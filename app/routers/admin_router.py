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
    Admin page: Material Norms (conversion table).

    UI zobrazuje: W.Nr | EN ISO | ČSN | AISI | MaterialGroup | Actions

    Format: 1 řádek = 1 conversion entry (4 sloupce norem → 1 kategorie)
    """
    # Načíst všechny normy + MaterialGroup
    result = await db.execute(
        select(MaterialNorm)
        .options(selectinload(MaterialNorm.material_group))
        .where(MaterialNorm.deleted_at.is_(None))
        .order_by(MaterialNorm.id)
    )
    norms_orm = result.scalars().all()

    # Convert to dict for JSON serialization in template
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
            },
            "note": norm.note,
            "version": norm.version
        }
        for norm in norms_orm
    ]

    # Načíst SystemConfig pro druhý tab (System Settings)
    result_config = await db.execute(
        select(SystemConfig).order_by(SystemConfig.key)
    )
    configs = result_config.scalars().all()

    return templates.TemplateResponse("admin/material_norms.html", {
        "request": request,
        "norms": norms_orm,
        "norms_json": norms_json,
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
