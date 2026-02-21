"""GESTIMA - Materials API router (ADR-011: Material Hierarchy, ADR-014: Price Tiers)"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
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
    MaterialItemWithGroupResponse,
    MaterialItemListResponse
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


@router.get("/price-category-for-input", response_model=Optional[MaterialPriceCategoryWithGroupResponse])
async def get_price_category_for_input(
    shape: str,
    w_nr: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatické určení price category podle tvaru + W.Nr normy.

    Flow:
    1. W.Nr → MaterialNorm → material_group_id
    2. Najde PriceCategory kde shape == shape AND material_group_id == material_group_id
    3. Vrátí kategorii nebo None

    Args:
        shape: StockShape enum value (round_bar, flat_bar, atd.)
        w_nr: W.Nr norma (např. "1.7225", "1.4301")

    Returns:
        Automaticky vybraná PriceCategory nebo None pokud nenalezena
    """
    from app.models.material_norm import MaterialNorm

    # If no w_nr provided, return categories for shape only
    if not w_nr:
        result = await db.execute(
            select(MaterialPriceCategory)
            .options(selectinload(MaterialPriceCategory.material_group))
            .where(
                MaterialPriceCategory.deleted_at.is_(None),
                MaterialPriceCategory.shape == shape
            )
            .order_by(MaterialPriceCategory.code)
            .limit(1)
        )
        return result.scalar_one_or_none()

    # 1. Find MaterialNorm by W.Nr
    norm_result = await db.execute(
        select(MaterialNorm)
        .where(MaterialNorm.w_nr == w_nr)
    )
    norm = norm_result.scalar_one_or_none()

    if not norm:
        logger.warning(
            f"MaterialNorm not found for w_nr={w_nr}",
            extra={"user": current_user.username, "w_nr": w_nr}
        )
        return None

    # 2. Find PriceCategory by shape + material_group_id
    category_result = await db.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.material_group))
        .where(
            MaterialPriceCategory.deleted_at.is_(None),
            MaterialPriceCategory.shape == shape,
            MaterialPriceCategory.material_group_id == norm.material_group_id
        )
        .order_by(MaterialPriceCategory.code)
        .limit(1)
    )
    category = category_result.scalar_one_or_none()

    if not category:
        logger.warning(
            f"PriceCategory not found for shape={shape}, material_group_id={norm.material_group_id}",
            extra={
                "user": current_user.username,
                "w_nr": w_nr,
                "shape": shape,
                "material_group_id": norm.material_group_id
            }
        )
        return None

    logger.info(
        f"Auto-selected PriceCategory: {category.name}",
        extra={
            "user": current_user.username,
            "w_nr": w_nr,
            "shape": shape,
            "category_id": category.id,
            "category_name": category.name
        }
    )

    return category


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
    category_id: Optional[int] = None,
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
    return None  # 204 No Content


# ========== MATERIAL ITEMS ==========

@router.get("/items", response_model=MaterialItemListResponse)
async def get_material_items(
    group_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam polotovarů (filtrovatelné dle skupiny, stránkování) — vrací { items, total }"""
    base_query = select(MaterialItem).where(MaterialItem.deleted_at.is_(None))

    if group_id:
        base_query = base_query.where(MaterialItem.material_group_id == group_id)

    # Total count
    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0

    # Paginated items
    result = await db.execute(base_query.order_by(MaterialItem.code).offset(skip).limit(limit))
    items = result.scalars().all()

    return MaterialItemListResponse(items=items, total=total)


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
    return None  # 204 No Content


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


# ========== CATALOG IMPORT ==========

from pydantic import BaseModel

class ImportPreviewResponse(BaseModel):
    """Preview importu z katalogu"""
    total_items: int
    parseable_items: int
    skipped_items: int
    material_groups_needed: dict
    price_categories_needed: dict
    sample_items: List[dict]


class ImportExecuteResponse(BaseModel):
    """Výsledek importu"""
    success: bool
    groups_created: int
    categories_created: int
    items_created: int
    items_skipped: int
    message: str


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_catalog_import(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview importu materiálového katalogu z Excel.

    Načte parsed CSV data a vrátí statistiky bez zápisu do DB.
    """
    import pandas as pd
    from pathlib import Path

    PARSED_CSV = Path(__file__).parent.parent.parent / "temp" / "material_codes_preview.csv"
    EXCEL_PATH = Path(__file__).parent.parent.parent / "data" / "materialy_export_import.xlsx"

    if not PARSED_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="Parsovaná data nenalezena. Spusťte nejdřív: python scripts/analyze_material_codes.py"
        )

    try:
        # Load parsed data
        df_parsed = pd.read_csv(PARSED_CSV)

        # Load original Excel for skipped count
        df_excel = pd.read_excel(EXCEL_PATH)
        all_codes = set(df_excel['Pol.'].astype(str))
        parsed_codes = set(df_parsed['raw_code'].astype(str))
        skipped_codes = all_codes - parsed_codes

        # Analyze MaterialGroups needed (simplified - import full logic from script)
        from scripts.import_material_catalog import (
            identify_material_group,
            get_price_category_code,
            correct_shape
        )

        material_groups_needed = {}
        price_categories_needed = {}

        for _, row in df_parsed.head(20).iterrows():  # Sample first 20
            material_code = row['material']
            shape = row['shape']
            shape_code = row['shape_code']

            corrected_shape = correct_shape(shape, shape_code)
            group_info = identify_material_group(material_code)

            if group_info:
                code = group_info['code']
                if code not in material_groups_needed:
                    material_groups_needed[code] = group_info['name']

                cat_code, cat_name = get_price_category_code(code, corrected_shape)
                if cat_code not in price_categories_needed:
                    price_categories_needed[cat_code] = cat_name

        # Sample items
        sample_items = []
        for _, row in df_parsed.head(10).iterrows():
            sample_items.append({
                "code": row['raw_code'],
                "material": row['material'],
                "shape": row['shape'],
                "diameter": float(row['diameter']) if pd.notna(row['diameter']) else None,
                "width": float(row['width']) if pd.notna(row['width']) else None,
            })

        logger.info(
            f"Import preview generated",
            extra={
                "user": current_user.username,
                "parseable": len(df_parsed),
                "skipped": len(skipped_codes)
            }
        )

        return ImportPreviewResponse(
            total_items=len(all_codes),
            parseable_items=len(df_parsed),
            skipped_items=len(skipped_codes),
            material_groups_needed=material_groups_needed,
            price_categories_needed=price_categories_needed,
            sample_items=sample_items
        )

    except Exception as e:
        logger.error(f"Import preview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba při načítání preview: {str(e)}")


@router.post("/import/execute", response_model=ImportExecuteResponse)
async def execute_catalog_import(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Provede import materiálového katalogu do databáze.

    DŮLEŽITÉ: Vytvoří MaterialGroups, PriceCategories a MaterialItems.
    Price Tiers NEBUDOU vytvořeny - musí se nastavit manuálně!
    """
    import pandas as pd
    from pathlib import Path
    from scripts.import_material_catalog import (
        identify_material_group,
        get_price_category_code,
        correct_shape,
        get_tier_template,
        MATERIAL_GROUPS
    )
    from app.models.enums import StockShape
    import random

    PARSED_CSV = Path(__file__).parent.parent.parent / "temp" / "material_codes_preview.csv"

    if not PARSED_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="Parsovaná data nenalezena"
        )

    try:
        df_parsed = pd.read_csv(PARSED_CSV)

        # Analyze what's needed
        material_groups_needed = {}
        price_categories_needed = {}

        for _, row in df_parsed.iterrows():
            material_code = row['material']
            shape = row['shape']
            shape_code = row['shape_code']

            corrected_shape = correct_shape(shape, shape_code)
            group_info = identify_material_group(material_code)

            if group_info:
                code = group_info['code']
                if code not in material_groups_needed:
                    material_groups_needed[code] = {
                        'name': group_info['name'],
                        'density': group_info['density']
                    }

                cat_code, cat_name = get_price_category_code(code, corrected_shape)
                if cat_code not in price_categories_needed:
                    price_categories_needed[cat_code] = {
                        'name': cat_name,
                        'material_group_code': code
                    }

        # Execute import
        group_id_map = {}
        category_id_map = {}
        created_count = 0
        skipped_count = 0

        # Create MaterialGroups
        for code, info in material_groups_needed.items():
            result = await db.execute(
                select(MaterialGroup).where(MaterialGroup.code == code)
            )
            existing = result.scalar_one_or_none()

            if existing:
                group_id_map[code] = existing.id
            else:
                new_group = MaterialGroup(
                    code=code,
                    name=info['name'],
                    density=info['density']
                )
                set_audit(new_group, current_user.username)
                db.add(new_group)
                await db.flush()
                group_id_map[code] = new_group.id

        await safe_commit(db, action="import skupin materiálů")

        # Create PriceCategories + Tiers
        tiers_created = 0
        for code, info in price_categories_needed.items():
            result = await db.execute(
                select(MaterialPriceCategory).where(MaterialPriceCategory.code == code)
            )
            existing = result.scalar_one_or_none()

            if existing:
                category_id_map[code] = existing.id
            else:
                material_group_code = info['material_group_code']
                material_group_id = group_id_map.get(material_group_code)

                new_category = MaterialPriceCategory(
                    code=code,
                    name=info['name'],
                    material_group_id=material_group_id
                )
                set_audit(new_category, current_user.username)
                db.add(new_category)
                await db.flush()
                category_id_map[code] = new_category.id

                # Auto-create tiers from template
                template_code = get_tier_template(code)
                if template_code:
                    template_result = await db.execute(
                        select(MaterialPriceCategory).where(MaterialPriceCategory.code == template_code)
                    )
                    template_category = template_result.scalar_one_or_none()

                    if template_category:
                        tiers_result = await db.execute(
                            select(MaterialPriceTier)
                            .where(MaterialPriceTier.price_category_id == template_category.id)
                            .order_by(MaterialPriceTier.min_weight)
                        )
                        template_tiers = tiers_result.scalars().all()

                        for tier in template_tiers:
                            new_tier = MaterialPriceTier(
                                price_category_id=new_category.id,
                                min_weight=tier.min_weight,
                                max_weight=tier.max_weight,
                                price_per_kg=round(tier.price_per_kg * 0.8, 1)
                            )
                            set_audit(new_tier, current_user.username)
                            db.add(new_tier)
                            tiers_created += 1

        await safe_commit(db, action="import cenových kategorií a tierů")

        # Create MaterialItems
        for idx, row in df_parsed.iterrows():
            material_code = row['material']
            shape = row['shape']
            shape_code = row['shape_code']
            code = row['raw_code']

            corrected_shape = correct_shape(shape, shape_code)
            group_info = identify_material_group(material_code)

            if not group_info:
                skipped_count += 1
                continue

            material_group_id = group_id_map.get(group_info['code'])
            cat_code, _ = get_price_category_code(group_info['code'], corrected_shape)
            price_category_id = category_id_map.get(cat_code)

            if not material_group_id or not price_category_id:
                skipped_count += 1
                continue

            # Check if exists
            result = await db.execute(
                select(MaterialItem).where(MaterialItem.code == code)
            )
            if result.scalar_one_or_none():
                skipped_count += 1
                continue

            # Generate unique material_number
            material_number = f"20{random.randint(100000, 999999)}"
            while True:
                result = await db.execute(
                    select(MaterialItem).where(MaterialItem.material_number == material_number)
                )
                if not result.scalar_one_or_none():
                    break
                material_number = f"20{random.randint(100000, 999999)}"

            # Parse dimensions
            diameter = float(row['diameter']) if pd.notna(row['diameter']) else None
            width = float(row['width']) if pd.notna(row['width']) else None
            thickness = float(row['thickness']) if pd.notna(row['thickness']) else None
            wall_thickness = float(row['wall_thickness']) if pd.notna(row['wall_thickness']) else None

            # Create item
            new_item = MaterialItem(
                material_number=material_number,
                code=code,
                name=f"{material_code} {code.split('-', 1)[1] if '-' in code else code}",
                shape=StockShape[corrected_shape],
                diameter=diameter,
                width=width,
                thickness=thickness,
                wall_thickness=wall_thickness,
                material_group_id=material_group_id,
                price_category_id=price_category_id,
                stock_available=0.0
            )
            set_audit(new_item, current_user.username)
            db.add(new_item)
            created_count += 1

            if created_count % 100 == 0:
                await db.flush()

        await safe_commit(db, action="import materiálových položek")
        clear_cache()

        logger.info(
            f"Catalog import completed",
            extra={
                "user": current_user.username,
                "groups": len(group_id_map),
                "categories": len(category_id_map),
                "items_created": created_count,
                "items_skipped": skipped_count
            }
        )

        tier_msg = f" Price Tiers: {tiers_created} vytvořeno (80% cena z template)." if tiers_created > 0 else " Price Tiers: nastavte manuálně!"
        return ImportExecuteResponse(
            success=True,
            groups_created=len(group_id_map),
            categories_created=len(category_id_map),
            items_created=created_count,
            items_skipped=skipped_count,
            message=f"Import dokončen. Vytvořeno {created_count} položek.{tier_msg}"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Import execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chyba při importu: {str(e)}")
