"""GESTIMA - Infor Jobs Import Router

Import endpoints for Parts, Operations (routing), and ProductionRecords from Infor.
Uses generic InforImporterBase infrastructure.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.part import Part
from app.models.operation import Operation
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.services.infor_part_importer import PartImporter
from app.services.infor_job_routing_importer import JobRoutingImporter
from app.services.infor_production_importer import ProductionImporter
from app.services.infor_wc_mapper import InforWcMapper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/infor/import", tags=["Infor Import"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class ValidationResultSchema(BaseModel):
    """Validation result for single import row."""
    is_valid: bool
    is_duplicate: bool
    errors: List[str]
    warnings: List[str]


class PreviewRowSchema(BaseModel):
    """Preview row with validation."""
    row_index: int
    infor_data: Dict[str, Any]
    mapped_data: Dict[str, Any]
    validation: ValidationResultSchema


class ImportPreviewRequest(BaseModel):
    """Request for import preview."""
    rows: List[Dict[str, Any]] = Field(..., description="Infor IDO rows to import")


class ImportPreviewResponse(BaseModel):
    """Preview response with validation results."""
    valid_count: int
    error_count: int
    duplicate_count: int
    rows: List[PreviewRowSchema]


class ImportExecuteRequest(BaseModel):
    """Request for import execution."""
    rows: List[Dict[str, Any]] = Field(..., description="Validated rows with duplicate_action")


class ImportExecuteResponse(BaseModel):
    """Execution response with statistics."""
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


class WcMappingResponse(BaseModel):
    """WorkCenter mapping response."""
    mapping: Dict[str, str] = Field(..., description="Dict of InforCode → GestimaNumber")


class WcMappingUpdateRequest(BaseModel):
    """WorkCenter mapping update request."""
    mapping: Dict[str, str] = Field(..., description="New mapping dict")


# =============================================================================
# PARTS IMPORT ENDPOINTS
# =============================================================================


@router.post("/parts/preview", response_model=ImportPreviewResponse)
async def preview_part_import(
    data: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview Part import from Infor SLJobs.

    Validates rows, detects duplicates, maps fields.
    Returns validation results without creating any records.

    Request:
    {
      "rows": [{"Job": "ABC123", "Description": "Part name", ...}, ...]
    }

    Response:
    {
      "valid_count": 45,
      "error_count": 5,
      "duplicate_count": 3,
      "rows": [...]
    }
    """
    try:
        logger.info(f"Part preview: {len(data.rows)} rows")
        importer = PartImporter()
        preview_result = await importer.preview_import(data.rows, db)

        return ImportPreviewResponse(
            valid_count=preview_result["valid_count"],
            error_count=preview_result["error_count"],
            duplicate_count=preview_result["duplicate_count"],
            rows=preview_result["rows"]
        )

    except Exception as e:
        logger.error(f"Part preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/parts/execute", response_model=ImportExecuteResponse)
async def execute_part_import(
    data: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute Part import - create Parts in database.

    Request:
    {
      "rows": [
        {
          "article_number": "ABC123",
          "name": "Part name",
          "drawing_number": "DWG001",
          "customer_revision": "A",
          "duplicate_action": "skip"  # or "update"
        }
      ]
    }

    Response:
    {
      "success": true,
      "created_count": 45,
      "updated_count": 3,
      "skipped_count": 5,
      "errors": []
    }
    """
    try:
        logger.info(f"Part execute: {len(data.rows)} rows")
        importer = PartImporter()
        import_result = await importer.execute_import(data.rows, db)

        return ImportExecuteResponse(
            success=import_result["success"],
            created_count=import_result["created_count"],
            updated_count=import_result["updated_count"],
            skipped_count=import_result["skipped_count"],
            errors=import_result["errors"]
        )

    except Exception as e:
        logger.error(f"Part import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# =============================================================================
# ROUTING (OPERATIONS) IMPORT ENDPOINTS
# =============================================================================


@router.post("/routing/preview", response_model=ImportPreviewResponse)
async def preview_routing_import(
    data: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview Operation import from Infor SLJobRoutes.

    Auto-groups rows by DerJobItem (article_number), resolves Part from DB.
    Rows without matching Part get validation error.
    """
    try:
        logger.info(f"Routing preview: {len(data.rows)} rows")

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        await wc_mapper.warmup_cache(db)

        # Group rows by DerJobItem (article_number)
        groups: Dict[str, List[Dict]] = {}
        for row in data.rows:
            article = row.get("DerJobItem", "")
            if not article:
                continue
            groups.setdefault(str(article), []).append(row)

        # === BATCH Part lookup (1 query instead of N) ===
        article_numbers = list(groups.keys())
        parts_result = await db.execute(
            select(Part).where(
                Part.article_number.in_(article_numbers),
                Part.deleted_at.is_(None)
            )
        )
        parts_by_article: Dict[str, Part] = {
            p.article_number: p for p in parts_result.scalars().all()
        }

        # === BATCH Operation preload for duplicate check (1 query) ===
        found_part_ids = [p.id for p in parts_by_article.values()]
        if found_part_ids:
            ops_result = await db.execute(
                select(Operation.part_id, Operation.seq).where(
                    Operation.part_id.in_(found_part_ids),
                    Operation.deleted_at.is_(None)
                )
            )
            existing_ops: set = {(r[0], r[1]) for r in ops_result.all()}
        else:
            existing_ops = set()

        logger.info(
            f"Batch lookup: {len(article_numbers)} articles, "
            f"{len(parts_by_article)} found, {len(existing_ops)} existing operations"
        )

        # Resolve Parts and preview per group (NO more DB queries per row)
        all_rows: List[Dict] = []
        total_valid = 0
        total_errors = 0
        total_duplicates = 0

        for article_number, group_rows in groups.items():
            part = parts_by_article.get(article_number)

            if not part:
                # Part not found → all rows in this group are errors
                for i, row in enumerate(group_rows):
                    all_rows.append({
                        "row_index": len(all_rows),
                        "infor_data": row,
                        "mapped_data": {"article_number": article_number, "seq": row.get("OperNum")},
                        "validation": {
                            "is_valid": False,
                            "is_duplicate": False,
                            "errors": [f"Part '{article_number}' nenalezen v Gestimě — nejdřív importujte položku"],
                            "warnings": []
                        }
                    })
                    total_errors += 1
                continue

            # Fast in-memory preview (no DB queries per row)
            importer = JobRoutingImporter(part_id=part.id, wc_mapper=wc_mapper)
            for row in group_rows:
                mapped = await importer.map_row(row, db)

                # Skip CLO / ObsDate rows entirely (not shown in staging)
                if mapped.get("_skip"):
                    continue

                mapped["article_number"] = article_number
                mapped["part_id"] = part.id

                # In-memory duplicate check (no DB query)
                seq = mapped.get("seq")
                is_dup = (part.id, seq) in existing_ops

                # In-memory validation (required fields only)
                errors = []
                if not seq:
                    errors.append("Missing required field: seq")

                validation = {
                    "is_valid": len(errors) == 0,
                    "is_duplicate": is_dup,
                    "errors": errors,
                    "warnings": [f"Operation seq={seq} already exists"] if is_dup else [],
                }

                if len(errors) == 0:
                    total_valid += 1
                else:
                    total_errors += 1
                if is_dup:
                    total_duplicates += 1

                all_rows.append({
                    "row_index": len(all_rows),
                    "infor_data": row,
                    "mapped_data": mapped,
                    "validation": validation,
                })

        return ImportPreviewResponse(
            valid_count=total_valid,
            error_count=total_errors,
            duplicate_count=total_duplicates,
            rows=all_rows
        )

    except Exception as e:
        logger.error(f"Routing preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/routing/execute", response_model=ImportExecuteResponse)
async def execute_routing_import(
    data: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute Operation import - create Operations in database.

    Rows must contain part_id (resolved in preview).
    Auto-groups by part_id and imports per Part.
    """
    try:
        logger.info(f"Routing execute: {len(data.rows)} rows")

        # Group rows by part_id
        rows_by_part: Dict[int, List[Dict]] = {}
        for row in data.rows:
            part_id = row.get("part_id")
            if not part_id:
                logger.error(f"Row missing part_id: {row}")
                continue
            rows_by_part.setdefault(part_id, []).append(row)

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)

        # Execute import for each Part separately
        total_created = 0
        total_updated = 0
        total_skipped = 0
        all_errors: List[str] = []

        for part_id, part_rows in rows_by_part.items():
            importer = JobRoutingImporter(part_id=part_id, wc_mapper=wc_mapper)
            result = await importer.execute_import(part_rows, db)

            total_created += result["created_count"]
            total_updated += result["updated_count"]
            total_skipped += result["skipped_count"]
            all_errors.extend(result["errors"])

        return ImportExecuteResponse(
            success=len(all_errors) == 0,
            created_count=total_created,
            updated_count=total_updated,
            skipped_count=total_skipped,
            errors=all_errors
        )

    except Exception as e:
        logger.error(f"Routing import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# =============================================================================
# PRODUCTION IMPORT ENDPOINTS
# =============================================================================


@router.post("/production/preview", response_model=ImportPreviewResponse)
async def preview_production_import(
    data: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview ProductionRecord import from Infor SLJobRoutes.

    Validates rows, detects duplicates, resolves Part from article_number.

    Request:
    {
      "rows": [
        {
          "Job": "ORDER123",
          "Item": "ABC123",  # article_number for Part lookup
          "OperNum": 10,
          "Wc": "100",
          "QtyComplete": 50,
          "RunHrsTPc": 2.0,
          "ActRunHrs": 2.5
        }
      ]
    }
    """
    try:
        logger.info(f"Production preview: {len(data.rows)} rows")

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        importer = ProductionImporter(wc_mapper=wc_mapper)
        preview_result = await importer.preview_import(data.rows, db)

        return ImportPreviewResponse(
            valid_count=preview_result["valid_count"],
            error_count=preview_result["error_count"],
            duplicate_count=preview_result["duplicate_count"],
            rows=preview_result["rows"]
        )

    except Exception as e:
        logger.error(f"Production preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/production/execute", response_model=ImportExecuteResponse)
async def execute_production_import(
    data: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute ProductionRecord import - create records in database.

    Request:
    {
      "rows": [
        {
          "part_id": 123,
          "infor_order_number": "ORDER123",
          "operation_seq": 10,
          "work_center_id": 5,
          "batch_quantity": 50,
          "planned_time_min": 120.0,
          "actual_time_min": 150.0,
          "duplicate_action": "skip"
        }
      ]
    }
    """
    try:
        logger.info(f"Production execute: {len(data.rows)} rows")

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        importer = ProductionImporter(wc_mapper=wc_mapper)
        import_result = await importer.execute_import(data.rows, db)

        return ImportExecuteResponse(
            success=import_result["success"],
            created_count=import_result["created_count"],
            updated_count=import_result["updated_count"],
            skipped_count=import_result["skipped_count"],
            errors=import_result["errors"]
        )

    except Exception as e:
        logger.error(f"Production import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# =============================================================================
# WORKCENTER MAPPING ENDPOINTS
# =============================================================================


@router.get("/wc-mapping", response_model=WcMappingResponse)
async def get_wc_mapping(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get current WorkCenter mapping configuration.

    Returns:
    {
      "mapping": {
        "100": "80000001",
        "200": "80000002"
      }
    }
    """
    try:
        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        return WcMappingResponse(mapping=wc_mapper.get_mapping())

    except Exception as e:
        logger.error(f"Failed to get WC mapping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get mapping: {str(e)}")


@router.put("/wc-mapping", response_model=WcMappingResponse)
async def update_wc_mapping(
    data: WcMappingUpdateRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Update WorkCenter mapping configuration.

    WARNING: This updates runtime mapping only.
    To persist, update INFOR_WC_MAPPING in .env file.

    Request:
    {
      "mapping": {
        "100": "80000001",
        "200": "80000002",
        "300": "80000003"
      }
    }

    Response:
    {
      "mapping": {...}  # Updated mapping
    }
    """
    try:
        # Update runtime mapping
        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        wc_mapper.update_mapping(data.mapping)

        # NOTE: This does NOT persist to .env
        # Admin must manually update INFOR_WC_MAPPING in .env for persistence

        logger.warning(
            f"WC mapping updated in runtime (not persisted to .env): "
            f"{len(data.mapping)} entries"
        )

        return WcMappingResponse(mapping=wc_mapper.get_mapping())

    except Exception as e:
        logger.error(f"Failed to update WC mapping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update mapping: {str(e)}")
