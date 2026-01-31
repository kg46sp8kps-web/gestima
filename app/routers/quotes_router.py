"""GESTIMA - Quotes API router

Quote workflow:
- DRAFT: Editable
- SENT: Read-only (snapshot created)
- APPROVED/REJECTED: Final states

Edit lock: After SENT, must clone to edit
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
from app.models.quote import (
    Quote, QuoteCreate, QuoteUpdate, QuoteResponse,
    QuoteWithItemsResponse, QuoteListResponse
)
from app.models.partner import Partner
from app.models.enums import QuoteStatus
from app.services.number_generator import NumberGenerator
from app.services.quote_service import QuoteService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[QuoteListResponse])
async def get_quotes(
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    status: Optional[str] = Query(None, description="Filter podle statusu"),
    partner_id: Optional[int] = Query(None, description="Filter podle partnera"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List všech nabídek s pagination a filtry"""
    query = select(Quote).where(Quote.deleted_at.is_(None))

    # Filter by status
    if status:
        query = query.where(Quote.status == status)

    # Filter by partner
    if partner_id:
        query = query.where(Quote.partner_id == partner_id)

    result = await db.execute(
        query
        .order_by(Quote.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search")
async def search_quotes(
    search: str = Query("", description="Hledat v čísle nabídky, názvu"),
    status: Optional[str] = Query(None, description="Filter podle statusu"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování nabídek s multi-field search"""
    query = select(Quote).where(Quote.deleted_at.is_(None))

    # Status filter
    if status:
        query = query.where(Quote.status == status)

    # Search filter
    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            Quote.quote_number.ilike(search_term),
            Quote.title.ilike(search_term),
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(Quote.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Quote.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    quotes = result.scalars().all()

    # Convert to Pydantic models
    quotes_response = [QuoteListResponse.model_validate(quote) for quote in quotes]

    return {
        "quotes": quotes_response,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{quote_number}", response_model=QuoteWithItemsResponse)
async def get_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single quote by quote_number (with items)"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    return QuoteWithItemsResponse.model_validate(quote)


@router.post("/", response_model=QuoteResponse)
async def create_quote(
    data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new quote in DRAFT status.

    Auto-generates quote_number (85XXXXXX)
    """
    # Verify partner exists
    partner = await db.get(Partner, data.partner_id)
    if not partner or partner.deleted_at:
        raise HTTPException(status_code=404, detail="Partner not found")

    if not partner.is_customer:
        raise HTTPException(status_code=400, detail="Partner must be a customer")

    # Generate quote number
    quote_number = await NumberGenerator.generate_quote_number(db)

    # Create quote
    quote = Quote(
        quote_number=quote_number,
        partner_id=data.partner_id,
        title=data.title,
        description=data.description,
        valid_until=data.valid_until,
        status=QuoteStatus.DRAFT.value,
        discount_percent=data.discount_percent,
        tax_percent=data.tax_percent,
        notes=data.notes,
    )

    set_audit(quote, current_user.username)
    db.add(quote)
    await safe_commit(db, quote, "vytváření nabídky")

    logger.info(f"Created quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.put("/{quote_number}", response_model=QuoteResponse)
async def update_quote(
    quote_number: str,
    data: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quote - ONLY if status == DRAFT.

    Edit lock: Returns HTTP 409 if quote is not in DRAFT status
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check edit lock
    QuoteService.check_edit_lock(quote)

    # Optimistic locking
    if quote.version != data.version:
        raise HTTPException(status_code=409, detail="Version conflict")

    # Update fields
    if data.title is not None:
        quote.title = data.title
    if data.description is not None:
        quote.description = data.description
    if data.valid_until is not None:
        quote.valid_until = data.valid_until
    if data.discount_percent is not None:
        quote.discount_percent = data.discount_percent
    if data.tax_percent is not None:
        quote.tax_percent = data.tax_percent
    if data.notes is not None:
        quote.notes = data.notes

    # Recalculate totals
    await QuoteService.recalculate_quote_totals(quote, db)

    set_audit(quote, current_user.username, is_update=True)
    quote.version += 1

    await safe_commit(db, quote, "aktualizace nabídky")

    logger.info(f"Updated quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.delete("/{quote_number}")
async def delete_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete quote"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Soft delete
    from datetime import datetime
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = current_user.username

    await safe_commit(db, action="mazání nabídky")

    logger.info(f"Deleted quote {quote_number} by {current_user.username}")
    return {"message": "Quote deleted"}


@router.post("/{quote_number}/send", response_model=QuoteResponse)
async def send_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition DRAFT → SENT (creates snapshot).

    After this, quote is READ-ONLY.
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to SENT
    await QuoteService.transition_to_sent(quote, db, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "odeslání nabídky")

    logger.info(f"Sent quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/approve", response_model=QuoteResponse)
async def approve_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transition SENT → APPROVED"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to APPROVED
    await QuoteService.transition_to_approved(quote, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "schválení nabídky")

    logger.info(f"Approved quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/reject", response_model=QuoteResponse)
async def reject_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transition SENT → REJECTED"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to REJECTED
    await QuoteService.transition_to_rejected(quote, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "zamítnutí nabídky")

    logger.info(f"Rejected quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/clone", response_model=QuoteResponse)
async def clone_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clone quote (creates new DRAFT copy).

    Use this to edit after quote has been sent.
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Generate new quote number
    new_quote_number = await NumberGenerator.generate_quote_number(db)

    # Clone quote
    new_quote = await QuoteService.clone_quote(
        quote, db, current_user.username, new_quote_number
    )

    await safe_commit(db, new_quote, "klonování nabídky")

    logger.info(f"Cloned quote {quote_number} → {new_quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(new_quote)
