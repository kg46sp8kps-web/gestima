"""GESTIMA - Infor Sync Dispatchers

Dispatch functions for syncing operations, production, material_inputs, and documents.
Extracted from InforSyncService to keep each file under 300 LOC.

All dispatchers follow the preview → execute flow:
1. Group raw IDO rows by article_number
2. Batch Part lookup (single query)
3. Per-part: importer.map_row() → collect valid mapped data
4. Per-part: importer.execute_import() OR inline UPSERT
"""

import logging
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.material import MaterialItem
from app.models.material_input import MaterialInput, material_operation_link
from app.models.operation import Operation
from app.models.part import Part
from app.services.infor_api_client import InforAPIClient
from app.services.infor_document_importer import InforDocumentImporter
from app.services.infor_job_materials_importer import JobMaterialsImporter
from app.services.infor_job_routing_importer import JobRoutingImporter
from app.services.infor_production_importer import ProductionImporter
from app.services.infor_wc_mapper import InforWcMapper

logger = logging.getLogger(__name__)


async def dispatch_operations(rows: List[Dict[str, Any]], db: AsyncSession) -> Dict[str, Any]:
    """Sync operations from Infor SLJobRoutes (Type='S').

    Groups by DerJobItem, resolves Parts, maps via JobRoutingImporter,
    then executes import per-part with duplicate_action='update'.
    """
    if not rows:
        return _empty_result()

    wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
    await wc_mapper.warmup_cache(db)

    groups: Dict[str, List[Dict]] = {}
    for row in rows:
        article = row.get("DerJobItem", "")
        if article:
            groups.setdefault(str(article), []).append(row)

    parts_by_article = await _batch_part_lookup(list(groups.keys()), db)

    total_created = 0
    total_updated = 0
    total_skipped = 0
    all_errors: List[str] = []

    for article_number, group_rows in groups.items():
        part = parts_by_article.get(article_number)
        if not part:
            continue

        importer = JobRoutingImporter(part_id=part.id, wc_mapper=wc_mapper)
        mapped_rows: List[Dict] = []

        for row in group_rows:
            mapped = await importer.map_row(row, db)
            if mapped.get("_skip"):
                continue
            mapped["article_number"] = article_number
            mapped["part_id"] = part.id
            mapped["duplicate_action"] = "update"
            mapped_rows.append(mapped)

        if mapped_rows:
            try:
                result = await importer.execute_import(mapped_rows, db)
                total_created += result.get("created_count", 0)
                total_updated += result.get("updated_count", 0)
                total_skipped += result.get("skipped_count", 0)
                all_errors.extend(result.get("errors", []))
            except Exception as e:
                all_errors.append(f"Operations sync failed for {article_number}: {e}")
                logger.error(f"Operations sync error for {article_number}: {e}", exc_info=True)

    return _build_result(total_created, total_updated, total_skipped, all_errors)


async def dispatch_production(rows: List[Dict[str, Any]], db: AsyncSession) -> Dict[str, Any]:
    """Sync production records from Infor SLJobRoutes (Type='J').

    Groups by JobItem, resolves Parts, maps via ProductionImporter,
    then executes import per-part with duplicate_action='update'.
    """
    if not rows:
        return _empty_result()

    wc_mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
    await wc_mapper.warmup_cache(db)

    groups: Dict[str, List[Dict]] = {}
    for row in rows:
        article = row.get("JobItem", "")
        if article:
            groups.setdefault(str(article), []).append(row)

    parts_by_article = await _batch_part_lookup(list(groups.keys()), db)

    total_created = 0
    total_updated = 0
    total_skipped = 0
    all_errors: List[str] = []

    importer = ProductionImporter(wc_mapper=wc_mapper)

    for article_number, group_rows in groups.items():
        part = parts_by_article.get(article_number)
        if not part:
            continue

        mapped_rows: List[Dict] = []
        for row in group_rows:
            mapped = await importer.map_row(row, db)
            if mapped.get("_skip"):
                continue
            mapped["article_number"] = article_number
            mapped["part_id"] = part.id
            mapped["duplicate_action"] = "update"
            mapped_rows.append(mapped)

        if mapped_rows:
            try:
                result = await importer.execute_import(mapped_rows, db)
                total_created += result.get("created_count", 0)
                total_updated += result.get("updated_count", 0)
                total_skipped += result.get("skipped_count", 0)
                all_errors.extend(result.get("errors", []))
            except Exception as e:
                all_errors.append(f"Production sync failed for {article_number}: {e}")
                logger.error(f"Production sync error for {article_number}: {e}", exc_info=True)

    return _build_result(total_created, total_updated, total_skipped, all_errors)


async def dispatch_material_inputs(rows: List[Dict[str, Any]], db: AsyncSession) -> Dict[str, Any]:
    """Sync material inputs from Infor SLJobmatls (Type='S').

    Groups by ItmItem, resolves Parts + MaterialItems + Operations,
    then creates/updates MaterialInputs with operation links.
    Inline UPSERT (not via base execute_import) to handle material_operation_link.
    """
    if not rows:
        return _empty_result()

    groups: Dict[str, List[Dict]] = {}
    for row in rows:
        article = row.get("ItmItem", "")
        if article:
            groups.setdefault(str(article), []).append(row)

    parts_by_article = await _batch_part_lookup(list(groups.keys()), db)

    # Batch MaterialItem lookup
    all_item_codes: set = set()
    for group_rows in groups.values():
        for row in group_rows:
            code = row.get("Item", "")
            if code:
                all_item_codes.add(str(code))

    items_by_code: Dict[str, MaterialItem] = {}
    if all_item_codes:
        items_result = await db.execute(
            select(MaterialItem).where(MaterialItem.code.in_(list(all_item_codes)))
        )
        items_by_code = {item.code: item for item in items_result.scalars().all()}

    # Batch Operation lookup for linking
    found_part_ids = [p.id for p in parts_by_article.values()]
    ops_by_key: Dict[tuple, int] = {}
    if found_part_ids:
        ops_result = await db.execute(
            select(Operation.id, Operation.part_id, Operation.seq).where(
                Operation.part_id.in_(found_part_ids),
                Operation.deleted_at.is_(None),
            )
        )
        ops_by_key = {(r[1], r[2]): r[0] for r in ops_result.all()}

    total_created = 0
    total_updated = 0
    all_errors: List[str] = []

    for article_number, group_rows in groups.items():
        part = parts_by_article.get(article_number)
        if not part:
            continue

        importer = JobMaterialsImporter(
            part_id=part.id,
            material_items_cache=items_by_code,
            operations_cache=ops_by_key,
        )

        try:
            seq_counter = 0
            for row in group_rows:
                mapped = await importer.map_row(row, db)
                if mapped.get("_skip"):
                    continue

                material_item_id = mapped.get("material_item_id")
                if not material_item_id:
                    continue

                seq_counter += 10
                operation_seq = mapped.get("operation_seq")
                operation_id = ops_by_key.get((part.id, operation_seq)) if operation_seq else None

                # Duplicate check
                existing_result = await db.execute(
                    select(MaterialInput).where(
                        MaterialInput.part_id == part.id,
                        MaterialInput.material_item_id == material_item_id,
                        MaterialInput.deleted_at.is_(None),
                    )
                )
                existing = existing_result.scalar_one_or_none()

                if existing:
                    existing.quantity = mapped.get("quantity", 1)
                    existing.stock_diameter = mapped.get("stock_diameter")
                    existing.stock_length = mapped.get("stock_length")
                    existing.stock_width = mapped.get("stock_width")
                    existing.stock_height = mapped.get("stock_height")
                    existing.stock_wall_thickness = mapped.get("stock_wall_thickness")
                    total_updated += 1
                else:
                    new_material = MaterialInput(
                        part_id=part.id,
                        seq=seq_counter,
                        price_category_id=mapped.get("price_category_id"),
                        material_item_id=material_item_id,
                        stock_shape=mapped.get("stock_shape"),
                        stock_diameter=mapped.get("stock_diameter"),
                        stock_length=mapped.get("stock_length"),
                        stock_width=mapped.get("stock_width"),
                        stock_height=mapped.get("stock_height"),
                        stock_wall_thickness=mapped.get("stock_wall_thickness"),
                        quantity=mapped.get("quantity", 1),
                        notes=f"Infor sync: {mapped.get('material_item_code', '')}",
                    )
                    db.add(new_material)
                    await db.flush()

                    if operation_id:
                        await db.execute(
                            material_operation_link.insert().values(
                                material_input_id=new_material.id,
                                operation_id=int(operation_id),
                                consumed_quantity=None,
                            )
                        )
                    total_created += 1

            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        except Exception as e:
            all_errors.append(f"Material inputs sync failed for {article_number}: {e}")
            logger.error(f"Material inputs sync error for {article_number}: {e}", exc_info=True)

    return _build_result(total_created, total_updated, 0, all_errors)


async def dispatch_documents(
    rows: List[Dict[str, Any]], client: InforAPIClient, db: AsyncSession
) -> Dict[str, Any]:
    """Sync documents from Infor SLDocumentObjects_Exts.

    Uses InforDocumentImporter preview → execute flow.
    Downloads PDFs and links them to Parts via FileManager.
    """
    if not rows:
        return _empty_result()

    importer = InforDocumentImporter()

    # Preview: match documents to Parts + duplicate check
    staged_rows = await importer.preview_import(rows, db)

    # Set duplicate_action='update' for auto-sync (overwrite existing drawings)
    for row in staged_rows:
        if row.get("is_valid"):
            row["duplicate_action"] = "update"

    valid_count = sum(1 for r in staged_rows if r.get("is_valid"))
    if valid_count == 0:
        return _empty_result()

    result = await importer.execute_import(
        staged_rows=staged_rows,
        client=client,
        db=db,
        created_by="sync",
    )

    return {
        "created_count": result.get("created_count", 0),
        "updated_count": result.get("updated_count", 0),
        "errors": result.get("errors", []),
    }


# ==================== HELPERS ====================


async def _batch_part_lookup(
    article_numbers: List[str], db: AsyncSession
) -> Dict[str, Part]:
    """Batch lookup Parts by article_number (single query)."""
    if not article_numbers:
        return {}
    result = await db.execute(
        select(Part).where(
            Part.article_number.in_(article_numbers),
            Part.deleted_at.is_(None),
        )
    )
    return {p.article_number: p for p in result.scalars().all()}


def _empty_result() -> Dict[str, Any]:
    return {"created_count": 0, "updated_count": 0, "errors": []}


def _build_result(created: int, updated: int, skipped: int, errors: List[str]) -> Dict[str, Any]:
    return {
        "created_count": created,
        "updated_count": updated,
        "skipped_count": skipped,
        "errors": errors,
    }
