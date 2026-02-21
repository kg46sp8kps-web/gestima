"""GESTIMA - Partners API router

Partners serve dual purpose:
- Customers (quotations, orders)
- Suppliers (material purchase)
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.partner import Partner, PartnerCreate, PartnerUpdate, PartnerResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[PartnerResponse])
async def get_partners(
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    partner_type: Optional[str] = Query(None, description="Filter: 'customer', 'supplier', or None (all)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List všech partnerů s pagination a filtrem podle typu"""
    query = select(Partner).where(Partner.deleted_at.is_(None))

    # Filter by type
    if partner_type == "customer":
        query = query.where(Partner.is_customer == True)
    elif partner_type == "supplier":
        query = query.where(Partner.is_supplier == True)

    result = await db.execute(
        query
        .order_by(Partner.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search", response_model=dict)
async def search_partners(
    search: str = Query("", description="Hledat v názvu, IČO, DIČ, email"),
    partner_type: Optional[str] = Query(None, description="Filter: 'customer', 'supplier', or None"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování partnerů s multi-field search"""
    query = select(Partner).where(Partner.deleted_at.is_(None))

    # Type filter
    if partner_type == "customer":
        query = query.where(Partner.is_customer == True)
    elif partner_type == "supplier":
        query = query.where(Partner.is_supplier == True)

    # Search filter
    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            Partner.partner_number.ilike(search_term),
            Partner.company_name.ilike(search_term),
            Partner.ico.ilike(search_term),
            Partner.dic.ilike(search_term),
            Partner.email.ilike(search_term),
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(Partner.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Partner.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    partners = result.scalars().all()

    # Convert to Pydantic models for proper JSON serialization
    partners_response = [PartnerResponse.model_validate(partner) for partner in partners]

    return {
        "partners": partners_response,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{partner_number}", response_model=PartnerResponse)
async def get_partner(
    partner_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Partner).where(Partner.partner_number == partner_number, Partner.deleted_at.is_(None))
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner nenalezen")
    return partner


@router.post("/", response_model=PartnerResponse)
async def create_partner(
    data: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    # Auto-generate partner_number if not provided
    if not data.partner_number:
        try:
            partner_number = await NumberGenerator.generate_partner_number(db)
        except NumberGenerationError as e:
            logger.error(f"Failed to generate partner number: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo partnera. Zkuste to znovu.")
    else:
        partner_number = data.partner_number
        # Kontrola duplicitního čísla partnera (pokud zadáno ručně)
        result = await db.execute(select(Partner).where(Partner.partner_number == partner_number))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Partner s číslem '{partner_number}' již existuje")

    # Create partner with generated/provided number
    partner_data = data.model_dump(exclude={'partner_number'})
    partner = Partner(partner_number=partner_number, **partner_data)
    set_audit(partner, current_user.username)  # Audit trail helper (db_helpers.py)
    db.add(partner)

    partner = await safe_commit(db, partner, "vytváření partnera")
    logger.info(f"Created partner: {partner.partner_number}", extra={"partner_id": partner.id, "user": current_user.username})
    return partner


@router.put("/{partner_number}", response_model=PartnerResponse)
async def update_partner(
    partner_number: str,
    data: PartnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Partner).where(Partner.partner_number == partner_number))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner nenalezen")

    # Optimistic locking check (ADR-008)
    if partner.version != data.version:
        logger.warning(f"Version conflict updating partner {partner_number}: expected {data.version}, got {partner.version}", extra={"partner_number": partner_number, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(partner, key, value)

    set_audit(partner, current_user.username, is_update=True)  # Audit trail helper

    partner = await safe_commit(db, partner, "aktualizace partnera")
    logger.info(f"Updated partner: {partner.partner_number}", extra={"partner_number": partner_number, "user": current_user.username})
    return partner


@router.delete("/{partner_number}", status_code=204)
async def delete_partner(
    partner_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Soft delete partnera.

    Quotes které referují tohoto partnera zůstanou (partner_id SET NULL),
    ale mají snapshot_data s historickými údaji.
    """
    from datetime import datetime

    result = await db.execute(
        select(Partner).where(
            Partner.partner_number == partner_number,
            Partner.deleted_at.is_(None)
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner nenalezen")

    # Soft delete
    partner.deleted_at = datetime.utcnow()
    partner.deleted_by = current_user.username

    await safe_commit(db, action="mazání partnera")
    logger.info(f"Soft deleted partner: {partner_number}", extra={"partner_number": partner_number, "user": current_user.username})
    return {"message": "Partner smazán"}
