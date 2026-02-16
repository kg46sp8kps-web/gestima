"""GESTIMA - Cutting Conditions Router

Provides API for viewing/editing cutting conditions in Master Admin pivot table.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.models.cutting_condition import (
    CuttingConditionDB,
    CuttingConditionUpdate,
    CuttingConditionResponse,
)
from app.models.enums import UserRole
from app.models import User
from app.dependencies import get_current_user, require_role
from app.db_helpers import set_audit, safe_commit
from app.services.cutting_conditions_catalog import (
    MATERIAL_GROUP_MAP,
    seed_cutting_conditions_to_db,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cutting-conditions", tags=["Cutting Conditions"])


# === OPERATION METADATA ===
# Frontend needs to know which operations exist and which fields they have

OPERATIONS_METADATA = [
    {"operation_type": "turning", "operation": "hrubovani", "label": "Soustru. hrub.", "fields": ["Vc", "f", "Ap"]},
    {"operation_type": "turning", "operation": "dokoncovani", "label": "Soustru. dok.", "fields": ["Vc", "f", "Ap"]},
    {"operation_type": "drilling", "operation": "navrtani", "label": "Navrtání", "fields": ["Vc", "f"]},
    {"operation_type": "drilling", "operation": "vrtani", "label": "Vrtání", "fields": ["Vc", "f"]},
    {"operation_type": "drilling", "operation": "vrtani_hluboke", "label": "Hluboké vrt.", "fields": ["Vc", "f"]},
    {"operation_type": "drilling", "operation": "vystruzovani", "label": "Vystružov.", "fields": ["Vc", "f"]},
    {"operation_type": "threading", "operation": "zavitovani", "label": "Závitování", "fields": ["Vc"]},
    {"operation_type": "grooving", "operation": "zapichovani", "label": "Zapichov.", "fields": ["Vc", "f"]},
    {"operation_type": "parting", "operation": "upichnuti", "label": "Upíchnutí", "fields": ["Vc", "f"]},
    {"operation_type": "milling", "operation": "frezovani", "label": "Frézování", "fields": ["Vc", "fz", "Ap"]},
    {"operation_type": "grinding", "operation": "brouseni", "label": "Broušení", "fields": ["Vc", "f", "Ap"]},
    {"operation_type": "sawing", "operation": "rezani", "label": "Řezání", "fields": ["f"]},
]


@router.get("/pivot", response_model=Dict[str, Any])
async def get_pivot_table(
    mode: str = "mid",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> Dict[str, Any]:
    """
    Get cutting conditions pivot table data.

    Args:
        mode: Cutting mode (low, mid, high)

    Returns:
        Pivot data structure for frontend table:
        {
            "mode": "mid",
            "materials": ["20910000", "20910001", ...],
            "material_names": {"20910000": "Hliník", ...},
            "operations": [{operation_type, operation, label, fields}, ...],
            "cells": {
                "20910000": {
                    "turning/hrubovani": {id, Vc, f, Ap, notes, version},
                    ...
                }
            }
        }
    """
    try:
        # Fetch all records for given mode
        result = await db.execute(
            select(CuttingConditionDB).where(CuttingConditionDB.mode == mode)
        )
        records = result.scalars().all()

        # Build cells dict
        cells: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            mat_code = rec.material_group
            op_key = f"{rec.operation_type}/{rec.operation}"

            if mat_code not in cells:
                cells[mat_code] = {}

            cells[mat_code][op_key] = {
                "id": rec.id,
                "Vc": rec.Vc,
                "f": rec.f,
                "Ap": rec.Ap,
                "notes": rec.notes,
                "version": rec.version,
            }

        return {
            "mode": mode,
            "materials": list(MATERIAL_GROUP_MAP.keys()),
            "material_names": {code: info["name"] for code, info in MATERIAL_GROUP_MAP.items()},
            "operations": OPERATIONS_METADATA,
            "cells": cells,
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching pivot table: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chyba databáze při načítání řezných podmínek",
        )


@router.put("/{record_id}", response_model=CuttingConditionResponse)
async def update_cutting_condition(
    record_id: int,
    data: CuttingConditionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Update single cutting condition with optimistic locking.

    Args:
        record_id: Record ID
        data: Update data (must include version field)

    Returns:
        Updated record

    Raises:
        404: Record not found
        409: Version conflict (optimistic locking)
    """
    try:
        # Fetch record
        result = await db.execute(
            select(CuttingConditionDB).where(CuttingConditionDB.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Řezná podmínka s ID {record_id} neexistuje",
            )

        # Optimistic locking check
        if record.version != data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Záznam byl mezitím změněn jiným uživatelem. Obnovte stránku.",
            )

        # Update fields (only non-None values)
        if data.Vc is not None:
            record.Vc = data.Vc
        if data.f is not None:
            record.f = data.f
        if data.Ap is not None:
            record.Ap = data.Ap
        if data.notes is not None:
            record.notes = data.notes

        # Audit fields
        set_audit(record, current_user.id)

        # Commit with transaction handling (L-008)
        try:
            await safe_commit(db)
            await db.refresh(record)
            return CuttingConditionResponse.model_validate(record)
        except Exception:
            await db.rollback()
            raise

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating cutting condition: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chyba databáze při ukládání řezné podmínky",
        )


@router.post("/seed", response_model=Dict[str, Any])
async def seed_from_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
) -> Dict[str, Any]:
    """
    Seed cutting conditions from catalog.

    Deletes all existing records and inserts fresh data from catalog.

    Returns:
        {"message": "Seeded X conditions", "count": X}
    """
    try:
        count = await seed_cutting_conditions_to_db(db)
        return {
            "message": f"Seeded {count} cutting conditions",
            "count": count,
        }
    except Exception as e:
        logger.error(f"Failed to seed cutting conditions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chyba při seedování řezných podmínek",
        )
