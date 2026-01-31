"""GESTIMA - Admin router (Material Norms, System Config, ...)

UPDATED: 2026-01-31
Jinja2 templates archived in: archive/legacy-alpinejs-v1.6.1/
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
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
from app.db_helpers import set_audit, safe_commit
from app.services.material_mapping import search_norms

router = APIRouter()


# ========== MATERIAL NORMS ==========

# LEGACY: Commented out - replaced by Vue SPA
# @router.get("/master-data", response_class=HTMLResponse)
# async def admin_master_data_page(...):
#     """Vue SPA now handles /admin/master-data route"""
#     pass


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


@router.get("/api/material-norms", response_model=List[Dict[str, Any]])
async def api_list_material_norms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    API: List all material norms with material_group eagerly loaded.
    """
    result = await db.execute(
        select(MaterialNorm)
        .options(selectinload(MaterialNorm.material_group))
        .where(MaterialNorm.deleted_at.is_(None))
        .order_by(MaterialNorm.id)
    )
    norms = result.scalars().all()

    return [
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
            "version": norm.version,
            "created_at": norm.created_at.isoformat(),
            "updated_at": norm.updated_at.isoformat()
        }
        for norm in norms
    ]


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
    db.add(norm)

    norm = await safe_commit(db, norm, "vytváření normy")
    return MaterialNormResponse.model_validate(norm)


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

    norm = await safe_commit(db, norm, "aktualizace MaterialNorm")
    return MaterialNormResponse.model_validate(norm)


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

    await safe_commit(db, action="mazání MaterialNorm")
    return {"message": f"MaterialNorm '{norm.code}' smazána"}


# ========== MATERIAL CATALOG (Groups + Price Categories) ==========
# ARCHIVED: 2026-01-31 - Jinja2 template moved to archive/legacy-alpinejs-v1.6.1/

@router.get("/material-catalog")
async def admin_material_catalog_redirect():
    """Redirect to Vue SPA Master Data (Material Catalog tab)"""
    return RedirectResponse(url="/admin/master-data?tab=materials", status_code=302)


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
    db.add(group)

    group = await safe_commit(db, group, "vytváření skupiny materiálu")
    return MaterialGroupResponse.model_validate(group)


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

    group = await safe_commit(db, group, "aktualizace MaterialGroup")
    return MaterialGroupResponse.model_validate(group)


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

    await safe_commit(db, action="mazání MaterialGroup")
    return {"message": f"MaterialGroup '{group.code}' smazána"}


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
    db.add(category)

    category = await safe_commit(db, category, "vytváření cenové kategorie")
    return MaterialPriceCategoryResponse.model_validate(category)


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

    category = await safe_commit(db, category, "aktualizace MaterialPriceCategory")
    return MaterialPriceCategoryResponse.model_validate(category)


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

    await safe_commit(db, action="mazání MaterialPriceCategory")
    return {"message": f"MaterialPriceCategory '{category.code}' smazána"}
