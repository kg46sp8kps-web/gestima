"""GESTIMA - Materials API router (ADR-011: Material Hierarchy, ADR-014: Price Tiers)"""

import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.services.reference_loader import clear_cache
from app.models import User, UserRole
from app.models.material import (
    MaterialGroup,
    MaterialGroupCreate,
    MaterialGroupUpdate,
    MaterialGroupResponse,
    MaterialPriceCategory,
    MaterialPriceCategoryCreate,
    MaterialPriceCategoryUpdate,
    MaterialPriceCategoryResponse,
    MaterialPriceCategoryWithTiersResponse,
    MaterialPriceCategoryWithGroupResponse,
    MaterialPriceTier,
    MaterialPriceTierCreate,
    MaterialPriceTierUpdate,
    MaterialPriceTierResponse,
    MaterialItem,
    MaterialItemCreate,
    MaterialItemUpdate,
    MaterialItemResponse,
    MaterialItemWithGroupResponse
)
from app.services.material_parser import MaterialParserService, ParseResult

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== MATERIAL GROUPS ==========

@router.get("/groups", response_model=List[MaterialGroupResponse])
async def get_material_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam kategorií materiálů (pro výpočty: hustota, řezné podmínky)"""
    result = await db.execute(
        select(MaterialGroup)
        .where(MaterialGroup.deleted_at.is_(None))
        .order_by(MaterialGroup.code)
    )
    return result.scalars().all()


@router.get("/groups/{group_id}", response_model=MaterialGroupResponse)
async def get_material_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail kategorie materiálu"""
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Skupina materiálu nenalezena")
    return group


@router.post("/groups", response_model=MaterialGroupResponse)
async def create_material_group(
    data: MaterialGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nové kategorie materiálu (pouze admin)"""
    group = MaterialGroup(**data.model_dump())
    set_audit(group, current_user.username)
    db.add(group)

    group = await safe_commit(db, group, "vytváření skupiny materiálu", f"Skupina s kódem '{data.code}' již existuje")
    clear_cache()  # Invalidate reference data cache
    logger.info(f"Created material group: {group.code}", extra={"group_id": group.id, "user": current_user.username})
    return group


@router.put("/groups/{group_id}", response_model=MaterialGroupResponse)
async def update_material_group(
    group_id: int,
    data: MaterialGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Aktualizace kategorie materiálu (pouze admin)"""
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Skupina materiálu nenalezena")

    # Optimistic locking check (ADR-008)
    if group.version != data.version:
        logger.warning(f"Version conflict updating material group {group_id}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(group, key, value)

    set_audit(group, current_user.username, is_update=True)

    group = await safe_commit(db, group, "aktualizace skupiny materiálu", "Konflikt dat (duplicitní kód)")
    clear_cache()  # Invalidate reference data cache
    logger.info(f"Updated material group: {group.code}", extra={"group_id": group.id, "user": current_user.username})
    return group


# ========== MATERIAL PRICE CATEGORIES (ADR-014) ==========

@router.get("/price-categories", response_model=List[MaterialPriceCategoryWithGroupResponse])
async def get_price_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam cenových kategorií s MaterialGroup (pro dropdown v parts/edit.html)"""
    result = await db.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.material_group))
        .where(MaterialPriceCategory.deleted_at.is_(None))
        .order_by(MaterialPriceCategory.code)
    )
    return result.scalars().all()


@router.get("/price-categories/{category_id}", response_model=MaterialPriceCategoryWithTiersResponse)
async def get_price_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail cenové kategorie s tiers"""
    result = await db.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.tiers))
        .where(MaterialPriceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Cenová kategorie nenalezena")
    return category


@router.post("/price-categories", response_model=MaterialPriceCategoryResponse)
async def create_price_category(
    data: MaterialPriceCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nové cenové kategorie (pouze admin)"""
    category = MaterialPriceCategory(**data.model_dump())
    set_audit(category, current_user.username)
    db.add(category)

    category = await safe_commit(db, category, "vytváření cenové kategorie", f"Cenová kategorie s kódem '{data.code}' již existuje")
    clear_cache()
    logger.info(f"Created price category: {category.code}", extra={"category_id": category.id, "user": current_user.username})
    return category


@router.put("/price-categories/{category_id}", response_model=MaterialPriceCategoryResponse)
async def update_price_category(
    category_id: int,
    data: MaterialPriceCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Aktualizace cenové kategorie (pouze admin)"""
    result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Cenová kategorie nenalezena")

    # Optimistic locking check
    if category.version != data.version:
        logger.warning(f"Version conflict updating price category {category_id}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(category, key, value)

    set_audit(category, current_user.username, is_update=True)

    category = await safe_commit(db, category, "aktualizace cenové kategorie", "Konflikt dat (duplicitní kód)")
    clear_cache()
    logger.info(f"Updated price category: {category.code}", extra={"category_id": category.id, "user": current_user.username})
    return category


# ========== MATERIAL PRICE TIERS (ADR-014) ==========

@router.get("/price-tiers", response_model=List[MaterialPriceTierResponse])
async def get_price_tiers(
    category_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam price tiers (filtrovatelné dle kategorie)"""
    query = (
        select(MaterialPriceTier)
        .where(MaterialPriceTier.deleted_at.is_(None))
        .order_by(MaterialPriceTier.price_category_id, MaterialPriceTier.min_weight)
    )

    if category_id:
        query = query.where(MaterialPriceTier.price_category_id == category_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/price-tiers/{tier_id}", response_model=MaterialPriceTierResponse)
async def get_price_tier(
    tier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail price tier"""
    result = await db.execute(select(MaterialPriceTier).where(MaterialPriceTier.id == tier_id))
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail="Price tier nenalezen")
    return tier


@router.post("/price-tiers", response_model=MaterialPriceTierResponse)
async def create_price_tier(
    data: MaterialPriceTierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nového price tier (pouze admin)"""
    # Ověřit existenci price_category
    result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.id == data.price_category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=400, detail=f"Cenová kategorie s ID {data.price_category_id} neexistuje")

    tier = MaterialPriceTier(**data.model_dump())
    set_audit(tier, current_user.username)
    db.add(tier)

    tier = await safe_commit(db, tier, "vytváření price tier", "Konflikt dat (duplicitní tier)")
    clear_cache()
    logger.info(
        f"Created price tier: {tier.min_weight}-{tier.max_weight or '∞'} kg → {tier.price_per_kg} Kč/kg",
        extra={"tier_id": tier.id, "category_id": tier.price_category_id, "user": current_user.username}
    )
    return tier


@router.put("/price-tiers/{tier_id}", response_model=MaterialPriceTierResponse)
async def update_price_tier(
    tier_id: int,
    data: MaterialPriceTierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Aktualizace price tier (pouze admin)"""
    result = await db.execute(select(MaterialPriceTier).where(MaterialPriceTier.id == tier_id))
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail="Price tier nenalezen")

    # Optimistic locking check
    if tier.version != data.version:
        logger.warning(f"Version conflict updating price tier {tier_id}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Ověřit existenci price_category pokud se mění
    if data.price_category_id and data.price_category_id != tier.price_category_id:
        result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.id == data.price_category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=400, detail=f"Cenová kategorie s ID {data.price_category_id} neexistuje")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(tier, key, value)

    set_audit(tier, current_user.username, is_update=True)

    tier = await safe_commit(db, tier, "aktualizace price tier", "Konflikt dat")
    clear_cache()
    logger.info(
        f"Updated price tier: {tier.min_weight}-{tier.max_weight or '∞'} kg → {tier.price_per_kg} Kč/kg",
        extra={"tier_id": tier.id, "user": current_user.username}
    )
    return tier


@router.delete("/price-tiers/{tier_id}", status_code=204)
async def delete_price_tier(
    tier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Smazání price tier (pouze admin) - soft delete"""
    result = await db.execute(select(MaterialPriceTier).where(MaterialPriceTier.id == tier_id))
    tier = result.scalar_one_or_none()
    if not tier:
        raise HTTPException(status_code=404, detail="Price tier nenalezen")

    # Soft delete
    tier.deleted_at = datetime.utcnow()
    tier.deleted_by = current_user.username

    await safe_commit(db, action="mazání price tier")
    clear_cache()
    logger.info(f"Deleted price tier: {tier.min_weight}-{tier.max_weight or '∞'} kg", extra={"tier_id": tier.id, "user": current_user.username})
    return {"message": f"Price tier smazán"}


# ========== MATERIAL ITEMS ==========

@router.get("/items", response_model=List[MaterialItemWithGroupResponse])
async def get_material_items(
    group_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam polotovarů (filtrovatelné dle skupiny)"""
    query = (
        select(MaterialItem)
        .options(
            selectinload(MaterialItem.group),
            selectinload(MaterialItem.price_category)
        )
        .where(MaterialItem.deleted_at.is_(None))
        .order_by(MaterialItem.code)
    )

    if group_id:
        query = query.where(MaterialItem.material_group_id == group_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/items/{material_number}", response_model=MaterialItemWithGroupResponse)
async def get_material_item(
    material_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail polotovaru"""
    result = await db.execute(
        select(MaterialItem)
        .options(
            selectinload(MaterialItem.group),
            selectinload(MaterialItem.price_category)
        )
        .where(MaterialItem.material_number == material_number)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")
    return item


@router.post("/items", response_model=MaterialItemResponse)
async def create_material_item(
    data: MaterialItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nové skladové položky (pouze admin)"""
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    # Ověřit existenci material_group
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == data.material_group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=400, detail=f"Skupina materiálu s ID {data.material_group_id} neexistuje")

    # Ověřit existenci price_category (ADR-014)
    result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.id == data.price_category_id))
    price_category = result.scalar_one_or_none()
    if not price_category:
        raise HTTPException(status_code=400, detail=f"Cenová kategorie s ID {data.price_category_id} neexistuje")

    # Auto-generate material_number if not provided
    if not data.material_number:
        try:
            material_number = await NumberGenerator.generate_material_number(db)
        except NumberGenerationError as e:
            logger.error(f"Failed to generate material number: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo materiálu. Zkuste to znovu.")
    else:
        material_number = data.material_number
        # Kontrola duplicity (pokud zadáno ručně)
        result = await db.execute(select(MaterialItem).where(MaterialItem.material_number == material_number))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Materiál s číslem '{material_number}' již existuje")

    # Create item with generated/provided number
    item_data = data.model_dump(exclude={'material_number'})
    item = MaterialItem(material_number=material_number, **item_data)
    set_audit(item, current_user.username)
    db.add(item)

    item = await safe_commit(db, item, "vytváření polotovaru", f"Polotovar s kódem '{data.code}' již existuje")
    logger.info(f"Created material item: {item.code}", extra={"material_number": item.material_number, "user": current_user.username})
    return item


@router.put("/items/{material_number}", response_model=MaterialItemResponse)
async def update_material_item(
    material_number: str,
    data: MaterialItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Aktualizace polotovaru (admin nebo operator)"""
    result = await db.execute(select(MaterialItem).where(MaterialItem.material_number == material_number))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")

    # Optimistic locking check (ADR-008)
    if item.version != data.version:
        logger.warning(f"Version conflict updating material item {material_number}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Ověřit existenci material_group pokud se mění
    if data.material_group_id and data.material_group_id != item.material_group_id:
        result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == data.material_group_id))
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=400, detail=f"Skupina materiálu s ID {data.material_group_id} neexistuje")

    # Ověřit existenci price_category pokud se mění (ADR-014)
    if data.price_category_id and data.price_category_id != item.price_category_id:
        result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.id == data.price_category_id))
        price_category = result.scalar_one_or_none()
        if not price_category:
            raise HTTPException(status_code=400, detail=f"Cenová kategorie s ID {data.price_category_id} neexistuje")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(item, key, value)

    set_audit(item, current_user.username, is_update=True)

    item = await safe_commit(db, item, "aktualizace polotovaru", "Konflikt dat (duplicitní kód)")
    logger.info(f"Updated material item: {item.code}", extra={"material_number": item.material_number, "user": current_user.username})
    return item


@router.delete("/items/{material_number}", status_code=204)
async def delete_material_item(
    material_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Smazání polotovaru (pouze admin) - soft delete"""
    result = await db.execute(select(MaterialItem).where(MaterialItem.material_number == material_number))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")

    # Soft delete (ADR-001)
    item.deleted_at = datetime.utcnow()
    item.deleted_by = current_user.username

    await safe_commit(db, action="mazání polotovaru")
    logger.info(f"Deleted material item: {item.code}", extra={"material_number": item.material_number, "user": current_user.username})
    return {"message": f"Polotovar '{item.code}' byl smazán"}


# ========== MATERIAL PARSER (Fáze 1: Smart Input) ==========

@router.post("/parse", response_model=ParseResult)
async def parse_material_description(
    description: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parse material description string.

    Podporované formáty:
    - D20 1.4301 100mm → kulatina D20, nerez 1.4301, délka 100
    - 20x20 C45 500 → čtyřhran 20x20, ocel C45, délka 500
    - 20x30 S235 500 → profil 20x30, ocel S235, délka 500
    - t2 1.4301 1000x2000 → plech 2mm, nerez 1.4301
    - D20x2 1.4301 100 → trubka D20 tl.2mm, nerez, délka 100
    - ⬡24 CuZn37 150 → šestihran 24mm, mosaz, délka 150

    Args:
        description: User input string

    Returns:
        ParseResult s rozpoznanými parametry, confidence score,
        a navrhovanými entities (MaterialGroup, PriceCategory, MaterialItem)
    """
    try:
        parser = MaterialParserService(db)
        result = await parser.parse(description)

        logger.info(
            f"Material parsed: {description} → confidence={result.confidence:.2f}",
            extra={
                "user": current_user.username,
                "shape": result.shape,
                "material_norm": result.material_norm,
                "confidence": result.confidence
            }
        )

        return result

    except Exception as e:
        logger.error(f"Material parsing error: {e}", exc_info=True)
        # Return low-confidence result místo chyby (graceful degradation)
        return ParseResult(
            raw_input=description,
            confidence=0.0,
            matched_pattern="error"
        )
