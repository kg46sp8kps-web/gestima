"""GESTIMA - Admin router (Material Norms, System Config, ...)"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any

from app.database import get_db
from app.models import (
    User, MaterialNorm, MaterialNormCreate, MaterialNormUpdate, MaterialNormResponse,
    MaterialGroup, SystemConfig
)
from app.models.enums import UserRole
from app.dependencies import get_current_user, require_role
from app.db_helpers import set_audit
from app.services.material_mapping import search_norms

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ========== MATERIAL NORMS ==========

@router.get("/material-norms", response_class=HTMLResponse)
async def admin_material_norms_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Admin page: Material Norms + Material Groups + Price Categories + System Config.

    UI zobrazuje 4 taby:
    - Tab 1: Material Norms (W.Nr | EN ISO | ČSN | AISI → MaterialGroup)
    - Tab 2: Material Groups (code, name, density)
    - Tab 3: Price Categories (code, name, material_group, tiers)
    - Tab 4: System Config (koeficienty)
    """
    from app.models.material import MaterialPriceCategory, MaterialPriceTier

    # Tab 1: Material Norms
    result = await db.execute(
        select(MaterialNorm)
        .options(selectinload(MaterialNorm.material_group))
        .where(MaterialNorm.deleted_at.is_(None))
        .order_by(MaterialNorm.id)
    )
    norms_orm = result.scalars().all()

    norms_json = [
        {
            "id": norm.id,
            "w_nr": norm.w_nr,
            "en_iso": norm.en_iso,
            "csn": norm.csn,
            "aisi": norm.aisi,
            "material_group_id": norm.material_group_id,
            "material_group": {
                "id": norm.material_group.id,
                "code": norm.material_group.code,
                "name": norm.material_group.name,
                "density": float(norm.material_group.density)
            } if norm.material_group else None,
            "note": norm.note,
            "version": norm.version
        }
        for norm in norms_orm
    ]

    # Tab 2: Material Groups
    result_groups = await db.execute(
        select(MaterialGroup)
        .where(MaterialGroup.deleted_at.is_(None))
        .order_by(MaterialGroup.code)
    )
    groups_orm = result_groups.scalars().all()

    groups_json = [
        {
            "id": g.id,
            "code": g.code,
            "name": g.name,
            "density": float(g.density),
            "version": g.version
        }
        for g in groups_orm
    ]

    # Tab 3: Price Categories with Tiers
    result_categories = await db.execute(
        select(MaterialPriceCategory)
        .options(
            selectinload(MaterialPriceCategory.material_group),
            selectinload(MaterialPriceCategory.tiers)
        )
        .where(MaterialPriceCategory.deleted_at.is_(None))
        .order_by(MaterialPriceCategory.code)
    )
    categories_orm = result_categories.scalars().all()

    categories_json = [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "material_group_id": c.material_group_id,
            "material_group": {
                "id": c.material_group.id,
                "code": c.material_group.code,
                "name": c.material_group.name,
                "density": float(c.material_group.density)
            } if c.material_group else None,
            "tiers": [
                {
                    "id": t.id,
                    "min_weight": float(t.min_weight),
                    "max_weight": float(t.max_weight) if t.max_weight else None,
                    "price_per_kg": float(t.price_per_kg),
                    "version": t.version
                }
                for t in sorted(c.tiers, key=lambda x: x.min_weight)
            ],
            "version": c.version
        }
        for c in categories_orm
    ]

    # Tab 4: System Config
    result_config = await db.execute(
        select(SystemConfig).order_by(SystemConfig.key)
    )
    configs = result_config.scalars().all()

    return templates.TemplateResponse("admin/material_norms.html", {
        "request": request,
        "norms": norms_orm,
        "norms_json": norms_json,
        "groups_json": groups_json,
        "categories_json": categories_json,
        "configs": configs,
        "current_user": current_user
    })


@router.get("/api/material-groups")
async def api_get_material_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    API: Get all MaterialGroups (for dropdown in forms).
    """
    from app.models.material import MaterialGroupResponse
    result = await db.execute(
        select(MaterialGroup)
        .where(MaterialGroup.deleted_at.is_(None))
        .order_by(MaterialGroup.name)
    )
    groups = result.scalars().all()
    return [MaterialGroupResponse.model_validate(g) for g in groups]


@router.get("/api/material-norms/search")
async def api_search_material_norms(
    q: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[MaterialNormResponse]:
    """
    API: Search material norms (case-insensitive, partial match).

    Použití: Autocomplete v admin UI.

    Example:
        GET /api/material-norms/search?q=1.4301
        → [{"code": "1.4301", "standard": "EN", ...}, ...]
    """
    norms = await search_norms(db, q, limit)
    return [MaterialNormResponse.model_validate(n) for n in norms]


@router.post("/api/material-norms")
async def api_create_material_norm(
    data: MaterialNormCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> MaterialNormResponse:
    """
    API: Create new MaterialNorm (4-column conversion entry).

    Validations:
    - At least one norm column must be filled (w_nr, en_iso, csn, aisi)
    - material_group_id must exist
    """
    # At least one norm column must be filled
    if not any([data.w_nr, data.en_iso, data.csn, data.aisi]):
        raise HTTPException(
            status_code=400,
            detail="Musíš vyplnit aspoň jednu normu (W.Nr, EN ISO, ČSN, nebo AISI)"
        )

    # Check MaterialGroup exists
    result = await db.execute(
        select(MaterialGroup).where(MaterialGroup.id == data.material_group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail=f"MaterialGroup ID {data.material_group_id} neexistuje")

    # Create MaterialNorm
    norm = MaterialNorm(
        w_nr=data.w_nr.upper() if data.w_nr else None,
        en_iso=data.en_iso.upper() if data.en_iso else None,
        csn=data.csn.upper() if data.csn else None,
        aisi=data.aisi.upper() if data.aisi else None,
        material_group_id=data.material_group_id,
        note=data.note
    )
    set_audit(norm, current_user.username, is_update=False)

    try:
        db.add(norm)
        await db.commit()
        await db.refresh(norm)
        return MaterialNormResponse.model_validate(norm)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/api/material-norms/{norm_id}")
async def api_update_material_norm(
    norm_id: int,
    data: MaterialNormUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> MaterialNormResponse:
    """
    API: Update MaterialNorm (optimistic locking).

    Validations:
    - At least one norm column must be filled
    - material_group_id must exist
    """
    result = await db.execute(
        select(MaterialNorm).where(MaterialNorm.id == norm_id)
    )
    norm = result.scalar_one_or_none()

    if not norm:
        raise HTTPException(status_code=404, detail=f"MaterialNorm ID {norm_id} nenalezena")

    # Optimistic locking
    if norm.version != data.version:
        raise HTTPException(
            status_code=409,
            detail="Norma byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
        )

    # Update norm columns (at least one must be filled after update)
    if data.w_nr is not None:
        norm.w_nr = data.w_nr.upper() if data.w_nr else None
    if data.en_iso is not None:
        norm.en_iso = data.en_iso.upper() if data.en_iso else None
    if data.csn is not None:
        norm.csn = data.csn.upper() if data.csn else None
    if data.aisi is not None:
        norm.aisi = data.aisi.upper() if data.aisi else None

    # Check: At least one norm column must be filled
    if not any([norm.w_nr, norm.en_iso, norm.csn, norm.aisi]):
        raise HTTPException(
            status_code=400,
            detail="Musíš vyplnit aspoň jednu normu (W.Nr, EN ISO, ČSN, nebo AISI)"
        )

    # Update MaterialGroup
    if data.material_group_id is not None:
        # Check group exists
        result = await db.execute(
            select(MaterialGroup).where(MaterialGroup.id == data.material_group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail=f"MaterialGroup ID {data.material_group_id} neexistuje")
        norm.material_group_id = data.material_group_id

    # Update note
    if data.note is not None:
        norm.note = data.note

    set_audit(norm, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(norm)
        return MaterialNormResponse.model_validate(norm)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/api/material-norms/{norm_id}")
async def api_delete_material_norm(
    norm_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    API: Soft delete MaterialNorm.

    Note: Soft delete (set deleted_at, deleted_by) instead of hard delete.
    """
    result = await db.execute(
        select(MaterialNorm).where(MaterialNorm.id == norm_id)
    )
    norm = result.scalar_one_or_none()

    if not norm:
        raise HTTPException(status_code=404, detail=f"MaterialNorm ID {norm_id} nenalezena")

    # Soft delete
    from datetime import datetime
    norm.deleted_at = datetime.utcnow()
    norm.deleted_by = current_user.username

    try:
        await db.commit()
        return {"message": f"MaterialNorm '{norm.code}' smazána"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ========== MATERIAL CATALOG (Groups + Price Categories) ==========

@router.get("/material-catalog", response_class=HTMLResponse)
async def admin_material_catalog_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Admin page: Material Catalog (MaterialGroups + MaterialPriceCategories).

    UI zobrazuje: 2 taby pro správu kategorií před importem katalogu.
    """
    from app.models.material import MaterialPriceCategory

    # Load MaterialGroups
    result_groups = await db.execute(
        select(MaterialGroup)
        .where(MaterialGroup.deleted_at.is_(None))
        .order_by(MaterialGroup.code)
    )
    groups_orm = result_groups.scalars().all()

    # Convert to dict for JSON serialization
    groups_json = [
        {
            "id": g.id,
            "code": g.code,
            "name": g.name,
            "density": float(g.density),
            "version": g.version
        }
        for g in groups_orm
    ]

    # Load MaterialPriceCategories with MaterialGroup
    result_categories = await db.execute(
        select(MaterialPriceCategory)
        .options(selectinload(MaterialPriceCategory.material_group))
        .where(MaterialPriceCategory.deleted_at.is_(None))
        .order_by(MaterialPriceCategory.code)
    )
    categories_orm = result_categories.scalars().all()

    # Convert to dict for JSON serialization
    categories_json = [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "material_group_id": c.material_group_id,
            "material_group": {
                "id": c.material_group.id,
                "code": c.material_group.code,
                "name": c.material_group.name,
                "density": float(c.material_group.density)
            } if c.material_group else None,
            "version": c.version
        }
        for c in categories_orm
    ]

    return templates.TemplateResponse("admin/material_catalog.html", {
        "request": request,
        "groups_json": groups_json,
        "categories_json": categories_json,
        "current_user": current_user
    })


# ========== MaterialGroup CRUD ==========

@router.post("/api/material-groups")
async def api_create_material_group(
    data: "MaterialGroupCreate",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> "MaterialGroupResponse":
    """
    API: Create new MaterialGroup.
    """
    from app.models.material import MaterialGroupCreate, MaterialGroupResponse

    # Check code uniqueness
    result = await db.execute(
        select(MaterialGroup).where(MaterialGroup.code == data.code.upper())
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"MaterialGroup s kódem '{data.code}' již existuje")

    # Create MaterialGroup
    group = MaterialGroup(
        code=data.code.upper(),
        name=data.name,
        density=data.density
    )
    set_audit(group, current_user.username, is_update=False)

    try:
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return MaterialGroupResponse.model_validate(group)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/api/material-groups/{group_id}")
async def api_update_material_group(
    group_id: int,
    data: "MaterialGroupUpdate",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> "MaterialGroupResponse":
    """
    API: Update MaterialGroup (optimistic locking).
    """
    from app.models.material import MaterialGroupUpdate, MaterialGroupResponse

    result = await db.execute(
        select(MaterialGroup).where(MaterialGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail=f"MaterialGroup ID {group_id} nenalezena")

    # Optimistic locking
    if group.version != data.version:
        raise HTTPException(
            status_code=409,
            detail="Skupina byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
        )

    # Update fields
    if data.code is not None:
        # Check code uniqueness
        result = await db.execute(
            select(MaterialGroup).where(
                MaterialGroup.code == data.code.upper(),
                MaterialGroup.id != group_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Kód '{data.code}' je již použit")
        group.code = data.code.upper()

    if data.name is not None:
        group.name = data.name

    if data.density is not None:
        group.density = data.density

    set_audit(group, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(group)
        return MaterialGroupResponse.model_validate(group)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/api/material-groups/{group_id}")
async def api_delete_material_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    API: Soft delete MaterialGroup.

    Note: Soft delete (set deleted_at, deleted_by) instead of hard delete.
    """
    result = await db.execute(
        select(MaterialGroup).where(MaterialGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail=f"MaterialGroup ID {group_id} nenalezena")

    # Soft delete
    from datetime import datetime
    group.deleted_at = datetime.utcnow()
    group.deleted_by = current_user.username

    try:
        await db.commit()
        return {"message": f"MaterialGroup '{group.code}' smazána"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ========== MaterialPriceCategory CRUD ==========

@router.post("/api/material-price-categories")
async def api_create_material_price_category(
    data: "MaterialPriceCategoryCreate",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> "MaterialPriceCategoryResponse":
    """
    API: Create new MaterialPriceCategory.
    """
    from app.models.material import MaterialPriceCategoryCreate, MaterialPriceCategoryResponse, MaterialPriceCategory

    # Check code uniqueness
    result = await db.execute(
        select(MaterialPriceCategory).where(MaterialPriceCategory.code == data.code.upper())
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"MaterialPriceCategory s kódem '{data.code}' již existuje")

    # Create MaterialPriceCategory
    category = MaterialPriceCategory(
        code=data.code.upper(),
        name=data.name
    )
    set_audit(category, current_user.username, is_update=False)

    try:
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return MaterialPriceCategoryResponse.model_validate(category)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/api/material-price-categories/{category_id}")
async def api_update_material_price_category(
    category_id: int,
    data: "MaterialPriceCategoryUpdate",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> "MaterialPriceCategoryResponse":
    """
    API: Update MaterialPriceCategory (optimistic locking).
    """
    from app.models.material import MaterialPriceCategoryUpdate, MaterialPriceCategoryResponse, MaterialPriceCategory

    result = await db.execute(
        select(MaterialPriceCategory).where(MaterialPriceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail=f"MaterialPriceCategory ID {category_id} nenalezena")

    # Optimistic locking
    if category.version != data.version:
        raise HTTPException(
            status_code=409,
            detail="Kategorie byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
        )

    # Update fields
    if data.code is not None:
        # Check code uniqueness
        result = await db.execute(
            select(MaterialPriceCategory).where(
                MaterialPriceCategory.code == data.code.upper(),
                MaterialPriceCategory.id != category_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Kód '{data.code}' je již použit")
        category.code = data.code.upper()

    if data.name is not None:
        category.name = data.name

    set_audit(category, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(category)
        return MaterialPriceCategoryResponse.model_validate(category)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/api/material-price-categories/{category_id}")
async def api_delete_material_price_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    API: Soft delete MaterialPriceCategory.

    Note: Soft delete (set deleted_at, deleted_by) instead of hard delete.
    """
    from app.models.material import MaterialPriceCategory

    result = await db.execute(
        select(MaterialPriceCategory).where(MaterialPriceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail=f"MaterialPriceCategory ID {category_id} nenalezena")

    # Soft delete
    from datetime import datetime
    category.deleted_at = datetime.utcnow()
    category.deleted_by = current_user.username

    try:
        await db.commit()
        return {"message": f"MaterialPriceCategory '{category.code}' smazána"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
