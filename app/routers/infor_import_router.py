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
from app.rate_limiter import limiter
from app.models.part import Part
from app.models.operation import Operation
from app.models.production_record import ProductionRecord
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.services.infor_part_importer import PartImporter
from app.services.infor_job_routing_importer import JobRoutingImporter
from app.services.infor_production_importer import ProductionImporter
from app.services.infor_job_materials_importer import JobMaterialsImporter
from app.services.infor_wc_mapper import InforWcMapper
from app.services.infor_document_importer import InforDocumentImporter
from app.routers.infor_router import get_infor_client
from app.models.material import MaterialItem
from app.models.material_input import MaterialInput, material_operation_link

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
@limiter.exempt
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
@limiter.exempt
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
@limiter.exempt
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
@limiter.exempt
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
@limiter.exempt
async def preview_production_import(
    data: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview ProductionRecord import from Infor SLJobRoutes (Type='J').

    Auto-groups rows by JobItem (article_number), resolves Part from DB in batch.
    Rows without matching Part get validation error.

    Request:
    {
      "rows": [
        {
          "Job": "ORDER123",
          "JobItem": "ABC123",
          "OperNum": 10,
          "Wc": "100",
          "JobQtyReleased": 50,
          "DerRunMchHrs": 30.0,
          "DerRunLbrHrs": 30.0,
          "JshSetupHrs": 0.5,
          "SetupHrsT": 0.6,
          "RunHrsTMch": 1.8,
          "RunHrsTLbr": 1.8
        }
      ]
    }
    """
    try:
        logger.info(f"Production preview: {len(data.rows)} rows")

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        await wc_mapper.warmup_cache(db)

        # Group rows by JobItem (article_number)
        groups: Dict[str, List[Dict]] = {}
        for row in data.rows:
            article = row.get("JobItem", "")
            if not article:
                continue
            groups.setdefault(str(article), []).append(row)

        # === BATCH Part lookup (1 query) ===
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

        # === BATCH duplicate check (1 query) ===
        found_part_ids = [p.id for p in parts_by_article.values()]
        if found_part_ids:
            dup_result = await db.execute(
                select(
                    ProductionRecord.part_id,
                    ProductionRecord.infor_order_number,
                    ProductionRecord.operation_seq,
                ).where(
                    ProductionRecord.part_id.in_(found_part_ids),
                    ProductionRecord.deleted_at.is_(None)
                )
            )
            existing_records: set = {(r[0], r[1], r[2]) for r in dup_result.all()}
        else:
            existing_records = set()

        logger.info(
            f"Batch lookup: {len(article_numbers)} articles, "
            f"{len(parts_by_article)} found, {len(existing_records)} existing records"
        )

        # Process each group — NO more DB queries per row
        importer = ProductionImporter(wc_mapper=wc_mapper)
        all_rows: List[Dict] = []
        total_valid = 0
        total_errors = 0
        total_duplicates = 0

        for article_number, group_rows in groups.items():
            part = parts_by_article.get(article_number)

            if not part:
                # Part not found → all rows in this group are errors
                for row in group_rows:
                    all_rows.append({
                        "row_index": len(all_rows),
                        "infor_data": row,
                        "mapped_data": {
                            "article_number": article_number,
                            "operation_seq": row.get("OperNum"),
                        },
                        "validation": {
                            "is_valid": False,
                            "is_duplicate": False,
                            "errors": [
                                f"Part '{article_number}' nenalezen v Gestimě — nejdřív importujte položku"
                            ],
                            "warnings": [],
                        },
                    })
                    total_errors += 1
                continue

            # Fast in-memory preview (no DB queries per row)
            for row in group_rows:
                mapped = await importer.map_row(row, db)

                # Skip CLO / CADCAM / ObsDate rows entirely
                if mapped.get("_skip"):
                    continue

                mapped["article_number"] = article_number
                mapped["part_id"] = part.id

                # In-memory duplicate check
                job = mapped.get("infor_order_number")
                seq = mapped.get("operation_seq")
                is_dup = (part.id, job, seq) in existing_records

                # In-memory validation
                errors = []
                if not job:
                    errors.append("Missing required field: Job")
                if not seq:
                    errors.append("Missing required field: OperNum")

                validation = {
                    "is_valid": len(errors) == 0,
                    "is_duplicate": is_dup,
                    "errors": errors,
                    "warnings": (
                        [f"Record order={job} seq={seq} already exists"] if is_dup else []
                    ),
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
            rows=all_rows,
        )

    except Exception as e:
        logger.error(f"Production preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/production/execute", response_model=ImportExecuteResponse)
@limiter.exempt
async def execute_production_import(
    data: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute ProductionRecord import — create records in database.

    Rows must contain part_id (resolved during preview).
    Auto-groups by part_id and imports per Part.

    Request:
    {
      "rows": [
        {
          "part_id": 123,
          "infor_order_number": "ORDER123",
          "operation_seq": 10,
          "work_center_id": 5,
          "batch_quantity": 50,
          "planned_time_min": 2.0,
          "planned_setup_min": 30.0,
          "actual_time_min": 2.4,
          "actual_setup_min": 35.0,
          "actual_run_machine_min": 120.0,
          "actual_run_labor_min": 120.0,
          "manning_coefficient": 100.0,
          "duplicate_action": "skip"
        }
      ]
    }
    """
    try:
        logger.info(f"Production execute: {len(data.rows)} rows")

        # Group rows by part_id
        rows_by_part: Dict[int, List[Dict]] = {}
        for row in data.rows:
            part_id = row.get("part_id")
            if not part_id:
                logger.error(f"Row missing part_id: {row}")
                continue
            rows_by_part.setdefault(int(part_id), []).append(row)

        wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)

        # Execute import for each Part separately
        total_created = 0
        total_updated = 0
        total_skipped = 0
        all_errors: List[str] = []

        for _part_id, part_rows in rows_by_part.items():
            importer = ProductionImporter(wc_mapper=wc_mapper)
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
            errors=all_errors,
        )

    except Exception as e:
        logger.error(f"Production import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# =============================================================================
# JOB MATERIALS IMPORT ENDPOINTS (SLJobmatls → MaterialInput)
# =============================================================================


@router.post("/job-materials/preview", response_model=ImportPreviewResponse)
@limiter.exempt
async def preview_job_materials_import(
    data: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview MaterialInput import from Infor SLJobmatls (planned materials).

    Auto-groups rows by ItmItem (article_number), resolves Part + MaterialItem from DB.
    Creates MaterialInput records and links them to Operations via material_operation_link.
    """
    try:
        logger.info(f"Job materials preview: {len(data.rows)} rows")

        # Group rows by ItmItem (article_number)
        groups: Dict[str, List[Dict]] = {}
        for row in data.rows:
            article = row.get("ItmItem", "")
            if not article:
                continue
            groups.setdefault(str(article), []).append(row)

        # === BATCH Part lookup (1 query) ===
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

        # === BATCH MaterialItem lookup (1 query) ===
        all_item_codes: set = set()
        for group_rows in groups.values():
            for row in group_rows:
                item_code = row.get("Item", "")
                if item_code:
                    all_item_codes.add(str(item_code))

        items_by_code: Dict[str, MaterialItem] = {}
        if all_item_codes:
            items_result = await db.execute(
                select(MaterialItem).where(
                    MaterialItem.code.in_(list(all_item_codes))
                )
            )
            items_by_code = {
                item.code: item for item in items_result.scalars().all()
            }

        # === BATCH Operation lookup for linking (1 query) ===
        found_part_ids = [p.id for p in parts_by_article.values()]
        ops_by_key: Dict[tuple, int] = {}
        if found_part_ids:
            ops_result = await db.execute(
                select(Operation.id, Operation.part_id, Operation.seq).where(
                    Operation.part_id.in_(found_part_ids),
                    Operation.deleted_at.is_(None)
                )
            )
            ops_by_key = {
                (r[1], r[2]): r[0] for r in ops_result.all()
            }

        # === BATCH existing MaterialInput lookup (duplicate check, 1 query) ===
        existing_materials: set = set()
        if found_part_ids:
            mat_result = await db.execute(
                select(
                    MaterialInput.part_id,
                    MaterialInput.material_item_id,
                ).where(
                    MaterialInput.part_id.in_(found_part_ids),
                    MaterialInput.deleted_at.is_(None)
                )
            )
            existing_materials = {
                (r[0], r[1]) for r in mat_result.all() if r[1] is not None
            }

        logger.info(
            f"Batch lookup: {len(article_numbers)} articles, "
            f"{len(parts_by_article)} parts found, {len(items_by_code)} material items, "
            f"{len(ops_by_key)} operations, {len(existing_materials)} existing materials"
        )

        # Process each group
        all_rows: List[Dict] = []
        total_valid = 0
        total_errors = 0
        total_duplicates = 0

        for article_number, group_rows in groups.items():
            part = parts_by_article.get(article_number)

            if not part:
                for row in group_rows:
                    all_rows.append({
                        "row_index": len(all_rows),
                        "infor_data": row,
                        "mapped_data": {
                            "article_number": article_number,
                            "material_item_code": row.get("Item", ""),
                        },
                        "validation": {
                            "is_valid": False,
                            "is_duplicate": False,
                            "errors": [f"Part '{article_number}' nenalezen v Gestimě — nejdřív importujte položku"],
                            "warnings": []
                        }
                    })
                    total_errors += 1
                continue

            importer = JobMaterialsImporter(
                part_id=part.id,
                material_items_cache=items_by_code,
                operations_cache=ops_by_key
            )

            seq_counter = 0
            for row in group_rows:
                mapped = await importer.map_row(row, db)

                if mapped.get("_skip"):
                    continue

                mapped["article_number"] = article_number
                mapped["part_id"] = part.id
                seq_counter += 10
                mapped["seq"] = seq_counter

                # Resolve operation link
                operation_seq = mapped.get("operation_seq")
                operation_id = None
                if operation_seq is not None:
                    operation_id = ops_by_key.get((part.id, operation_seq))
                mapped["operation_id"] = operation_id

                # In-memory duplicate check
                material_item_id = mapped.get("material_item_id")
                is_dup = False
                if material_item_id is not None:
                    is_dup = (part.id, material_item_id) in existing_materials

                # Validation
                errors = []
                warnings = []

                if material_item_id is None:
                    errors.append(f"Materiálová položka '{mapped.get('material_item_code', '?')}' nenalezena v Gestimě — nejdřív importujte materiály")
                if operation_seq and not operation_id:
                    warnings.append(f"Operace seq={operation_seq} nenalezena — materiál bez vazby na operaci")

                validation = {
                    "is_valid": len(errors) == 0,
                    "is_duplicate": is_dup,
                    "errors": errors,
                    "warnings": warnings,
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
            rows=all_rows,
        )

    except Exception as e:
        logger.error(f"Job materials preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/job-materials/execute", response_model=ImportExecuteResponse)
@limiter.exempt
async def execute_job_materials_import(
    data: ImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute MaterialInput import — create MaterialInputs and link to Operations.

    Rows must contain part_id (resolved in preview).
    Creates MaterialInput + inserts material_operation_link for Operation linking.
    """
    try:
        logger.info(f"Job materials execute: {len(data.rows)} rows")

        # Group rows by part_id
        rows_by_part: Dict[int, List[Dict]] = {}
        for row in data.rows:
            part_id = row.get("part_id")
            if not part_id:
                logger.error(f"Row missing part_id: {row}")
                continue
            rows_by_part.setdefault(int(part_id), []).append(row)

        total_created = 0
        total_updated = 0
        total_skipped = 0
        all_errors: List[str] = []

        for part_id, part_rows in rows_by_part.items():
            try:
                for row_data in part_rows:
                    duplicate_action = row_data.get("duplicate_action", "skip")
                    material_item_id = row_data.get("material_item_id")

                    if not material_item_id:
                        all_errors.append(
                            f"Part {part_id}: MaterialItem not found for '{row_data.get('material_item_code', '?')}'"
                        )
                        continue

                    # Check duplicate (same part + same material_item)
                    existing = None
                    if material_item_id:
                        dup_result = await db.execute(
                            select(MaterialInput).where(
                                MaterialInput.part_id == part_id,
                                MaterialInput.material_item_id == material_item_id,
                                MaterialInput.deleted_at.is_(None)
                            )
                        )
                        existing = dup_result.scalar_one_or_none()

                    if existing:
                        if duplicate_action == "skip":
                            total_skipped += 1
                            continue
                        elif duplicate_action == "update":
                            existing.quantity = row_data.get("quantity", 1)
                            existing.stock_diameter = row_data.get("stock_diameter")
                            existing.stock_length = row_data.get("stock_length")
                            existing.stock_width = row_data.get("stock_width")
                            existing.stock_height = row_data.get("stock_height")
                            existing.stock_wall_thickness = row_data.get("stock_wall_thickness")
                            total_updated += 1
                            continue

                    # Create new MaterialInput
                    new_material = MaterialInput(
                        part_id=part_id,
                        seq=row_data.get("seq", 0),
                        price_category_id=row_data.get("price_category_id"),
                        material_item_id=material_item_id,
                        stock_shape=row_data.get("stock_shape"),
                        stock_diameter=row_data.get("stock_diameter"),
                        stock_length=row_data.get("stock_length"),
                        stock_width=row_data.get("stock_width"),
                        stock_height=row_data.get("stock_height"),
                        stock_wall_thickness=row_data.get("stock_wall_thickness"),
                        quantity=row_data.get("quantity", 1),
                        notes=f"Infor import: {row_data.get('material_item_code', '')}",
                    )
                    db.add(new_material)
                    await db.flush()  # Get ID for linking

                    # Link to Operation via material_operation_link
                    operation_id = row_data.get("operation_id")
                    if operation_id:
                        await db.execute(
                            material_operation_link.insert().values(
                                material_input_id=new_material.id,
                                operation_id=int(operation_id),
                                consumed_quantity=None,
                            )
                        )

                    total_created += 1

                await db.commit()

            except Exception as part_error:
                await db.rollback()
                error_msg = f"Failed to import materials for part_id={part_id}: {str(part_error)}"
                all_errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        return ImportExecuteResponse(
            success=len(all_errors) == 0,
            created_count=total_created,
            updated_count=total_updated,
            skipped_count=total_skipped,
            errors=all_errors,
        )

    except Exception as e:
        logger.error(f"Job materials import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# =============================================================================
# WORKCENTER MAPPING ENDPOINTS
# =============================================================================


@router.get("/wc-mapping", response_model=WcMappingResponse)
@limiter.exempt
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
@limiter.exempt
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


# =============================================================================
# DOCUMENT IMPORT ENDPOINTS
# =============================================================================


class DocumentPreviewRequest(BaseModel):
    """Request for document import preview."""
    rows: List[Dict[str, Any]] = Field(..., description="Document metadata rows from IDO")


class DocumentPreviewResponse(BaseModel):
    """Document preview response with match info."""
    valid_count: int
    error_count: int
    duplicate_count: int
    rows: List[Dict[str, Any]]


class DocumentExecuteRequest(BaseModel):
    """Request for document import execution."""
    rows: List[Dict[str, Any]] = Field(..., description="Staged rows from preview")


class DocumentExecuteResponse(BaseModel):
    """Document execution response."""
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


class DocumentListRequest(BaseModel):
    """Request for listing documents from Infor (paginated)."""
    filter: Optional[str] = Field(None, description="IDO filter (e.g. DocumentType = 'Výkres-platný')")
    record_cap: int = Field(default=0, ge=0, description="Max records (0 = all)")


class DocumentListResponse(BaseModel):
    """Paginated document listing response."""
    count: int
    rows: List[Dict[str, Any]]


@router.post("/documents/list", response_model=DocumentListResponse)
@limiter.exempt
async def list_documents(
    data: DocumentListRequest,
    client=Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    List documents from Infor with automatic pagination.

    Uses InforDocumentImporter.list_documents() which handles bookmark-based
    pagination internally. Returns ALL documents matching the filter.
    """
    try:
        importer = InforDocumentImporter()
        rows = await importer.list_documents(
            client=client,
            filter_str=data.filter,
            record_cap=data.record_cap,
        )
        logger.info(f"Document list: {len(rows)} rows returned")
        return DocumentListResponse(count=len(rows), rows=rows)

    except Exception as e:
        logger.error(f"Document list failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@router.post("/documents/preview", response_model=DocumentPreviewResponse)
@limiter.exempt
async def preview_document_import(
    data: DocumentPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Preview document import — match documents to Parts.

    Input: metadata rows from IDO (DocumentName, RowPointer, etc.)
    Output: staged rows with Part match info and duplicate detection.
    No binary downloads, no DB writes.
    """
    try:
        logger.info(f"Document preview: {len(data.rows)} rows")
        importer = InforDocumentImporter()
        staged_rows = await importer.preview_import(data.rows, db)

        valid_count = sum(1 for r in staged_rows if r["is_valid"])
        error_count = sum(1 for r in staged_rows if not r["is_valid"])
        duplicate_count = sum(1 for r in staged_rows if r["is_duplicate"])

        return DocumentPreviewResponse(
            valid_count=valid_count,
            error_count=error_count,
            duplicate_count=duplicate_count,
            rows=staged_rows,
        )

    except Exception as e:
        logger.error(f"Document preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/documents/execute", response_model=DocumentExecuteResponse)
@limiter.exempt
async def execute_document_import(
    data: DocumentExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    client=Depends(get_infor_client),
):
    """
    Execute document import — download PDFs from Infor and store in File Manager.

    For each valid staged row:
    1. Downloads PDF binary from Infor IDO (base64 decode)
    2. Stores file via file_service.store_from_bytes()
    3. Creates FileLink (entity_type='part', link_type='drawing')
    4. Updates Part.file_id

    Single commit after all rows.
    """
    try:
        logger.info(f"Document execute: {len(data.rows)} rows")
        importer = InforDocumentImporter()
        result = await importer.execute_import(
            staged_rows=data.rows,
            client=client,
            db=db,
            created_by=current_user.username,
        )

        return DocumentExecuteResponse(
            success=len(result["errors"]) == 0,
            created_count=result["created_count"],
            updated_count=result["updated_count"],
            skipped_count=result["skipped_count"],
            errors=result["errors"],
        )

    except Exception as e:
        logger.error(f"Document execute failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execute failed: {str(e)}")
