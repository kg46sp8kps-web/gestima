"""GESTIMA - Infor Smart Polling Sync Service

Background service that polls Infor API for changes and imports them automatically.
Uses asyncio task scheduler (no external dependencies).

Safety:
- READ-ONLY Infor access (GET only)
- Preview → Execute flow (W.Nr parsing, validation, mapping)
- Lock prevents concurrent sync + manual import conflicts
- Per-step enable/disable + interval config
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.sync_state import SyncState, SyncLog
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)


def _merge_dispatch_results(*results: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple dispatch results by summing counts and concatenating errors."""
    merged: Dict[str, Any] = {"created_count": 0, "updated_count": 0, "errors": []}
    for r in results:
        merged["created_count"] += r.get("created_count", 0)
        merged["updated_count"] += r.get("updated_count", 0)
        merged["errors"].extend(r.get("errors", []))
    return merged

# Default step configurations (seeded on first start)
DEFAULT_STEPS = [
    {
        "step_name": "parts",
        "ido_name": "SLItems",
        "filter_template": "FamilyCode LIKE 'Výrobek' AND (RybTridaNazev1 LIKE 'Nabídka' OR RybTridaNazev1 LIKE 'Aktivní')",
        "properties": "Item,FamilyCode,Description,DrawingNbr,Revision,RybTridaNazev1",
        "date_field": "RecordDate",
        "interval_seconds": 30,
    },
    {
        "step_name": "materials",
        "ido_name": "SLItems",
        "filter_template": "FamilyCode like 'materiál'",
        "properties": "Item,Description",
        "date_field": "RecordDate",
        "interval_seconds": 30,
    },
    {
        "step_name": "documents",
        "ido_name": "SLDocumentObjects_Exts",
        "filter_template": "DocumentType IN ('Výkres-platný','PDF','Výkres')",
        "properties": "DocumentName,DocumentExtension,DocumentType,RowPointer,Sequence,Description,StorageMethod",
        "date_field": "RecordDate",
        "interval_seconds": 300,
    },
    {
        "step_name": "operations",
        "ido_name": "SLJobRoutes",
        "filter_template": "Type = 'S'",
        "properties": "OperNum,DerJobItem,Wc,JshSchedHrs,JshSetupHrs,DerRunLbrHrs,DerRunMchHrs,ObsDate",
        "date_field": "RecordDate",
        "interval_seconds": 30,
    },
    {
        "step_name": "material_inputs",
        "ido_name": "SLJobmatls",
        "filter_template": "Type = 'S'",
        "properties": "ItmItem,Item,OperNum,MatlQtyConv,UM",
        "date_field": "RecordDate",
        "interval_seconds": 60,
    },
    {
        "step_name": "jobroutes_j",
        "ido_name": "SLJobRoutes",
        "filter_template": "Type = 'J'",
        "properties": (
            "Job,Suffix,OperNum,Wc,JobStat,DerJobItem,JobItem,JobDescription,"
            "JobQtyReleased,QtyComplete,QtyScrapped,JshSetupHrs,DerRunMchHrs,"
            "DerRunLbrHrs,SetupHrsT,RunHrsTMch,RunHrsTLbr,DerStartDate,DerEndDate,"
            "ObsDate,RecordDate"
        ),
        "date_field": "RecordDate",
        "interval_seconds": 30,
        "enabled": True,
    },
    {
        "step_name": "workshop_orders",
        "ido_name": "IteRybPrehledZakazekView",
        "filter_template": "Stat IN ('O','P','A')",
        "properties": (
            "CoNum,CoLine,CoRelease,"
            "CustNum,CustName,CustPo,CustShipName,"
            "Item,ItemDescription,Stat,"
            "DueDate,PromiseDate,ProjectedDate,ConfirmedDate,"
            "RybDeadLineDate,RybCoOrderDate,"
            "QtyOrderedConv,QtyShipped,QtyOnHand,QtyAvailable,QtyWIP,"
            "Job,Suffix,JobCount,"
            "Wc01,Wc02,Wc03,Wc04,Wc05,Wc06,Wc07,Wc08,Wc09,Wc10,"
            "Comp01,Comp02,Comp03,Comp04,Comp05,Comp06,Comp07,Comp08,Comp09,Comp10,"
            "Wip01,Wip02,Wip03,Wip04,Wip05,Wip06,Wip07,Wip08,Wip09,Wip10,"
            "Mat01,Mat02,Mat03,MatComp01,MatComp02,MatComp03,"
            "Ready,Picked,IsOverPromiseDate,"
            "TotalWeight,PriceConv,RybCena,"
            "Baleni,Regal,"
            "RecordDate"
        ),
        "date_field": "",
        "interval_seconds": 120,
        "enabled": True,
    },
    {
        "step_name": "workshop_jbr",
        "ido_name": "IteCzTsdJbrDetails",
        "filter_template": "",
        "properties": (
            "Job,Suffix,OperNum,Wc,"
            "State,StateAsd,LzeDokoncit,PlanFlag"
        ),
        "date_field": "",
        "interval_seconds": 60,
        "enabled": True,
    },
]

# JBR property set variants for fallback fetch (mirrors _QUEUE_PROP_SETS in workshop_service)
_JBR_PROP_SETS: List[List[str]] = [
    # Set with col* prefix (most common)
    ["colJob", "colSuffix", "colOper", "colWc", "colState", "colStateAsd", "colLzeDokoncit", "colPlanFlag"],
    # Set with standard names
    ["Job", "Suffix", "OperNum", "Wc", "State", "StateAsd", "LzeDokoncit", "PlanFlag"],
    # Empty = load default columns (last resort, like live fetch_wc_queue fallback)
    [],
]


class InforSyncService:
    """Background sync service using asyncio task scheduler."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._jbr_working_propset: Optional[List[str]] = None

    async def start(self):
        """Start sync scheduler."""
        if self._running:
            logger.warning("Sync service already running")
            return

        # Seed default steps
        await self._ensure_default_steps()

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("Infor Sync Service started")

    async def stop(self):
        """Stop sync scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Infor Sync Service stopped")

    async def _sync_loop(self):
        """Main sync loop - runs every 5s, checks intervals per step."""
        while self._running:
            try:
                async with async_session() as db:
                    result = await db.execute(
                        select(SyncState).where(SyncState.enabled == True)  # noqa: E712
                    )
                    steps = result.scalars().all()

                    now = datetime.now(timezone.utc)
                    for step in steps:
                        if step.last_sync_at:
                            elapsed = (now - step.last_sync_at.replace(tzinfo=timezone.utc)).total_seconds()
                            if elapsed < step.interval_seconds:
                                continue

                        # Execute step (with lock to prevent conflicts)
                        async with self._lock:
                            await self._execute_step(step, db)

            except Exception as e:
                logger.error(f"Sync loop error: {e}", exc_info=True)

            await asyncio.sleep(5)  # Check every 5s

    async def _execute_step(self, step: SyncState, db: AsyncSession):
        """Execute one sync step."""
        start_time = datetime.now(timezone.utc)
        start_ms = int(start_time.timestamp() * 1000)

        try:
            # Build filter
            # date_field="" → full load (no incremental date filter, e.g. for views)
            if step.date_field:
                if step.last_sync_at:
                    since = step.last_sync_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # First sync: fixed date nebo lookback
                    if settings.INFOR_SYNC_INITIAL_DATE:
                        since = f"{settings.INFOR_SYNC_INITIAL_DATE} 00:00:00"
                    else:
                        lookback_date = start_time - timedelta(days=settings.INFOR_SYNC_INITIAL_LOOKBACK_DAYS)
                        since = lookback_date.strftime("%Y-%m-%d %H:%M:%S")

                date_filter = f"{step.date_field} >= '{since}'"
                full_filter = f"{step.filter_template} AND {date_filter}" if step.filter_template else date_filter
            else:
                # No date field → use filter_template as-is (full load every cycle)
                full_filter = step.filter_template or ""

            # Fetch from Infor
            client = InforAPIClient(
                base_url=settings.INFOR_API_URL,
                config=settings.INFOR_CONFIG,
                username=settings.INFOR_USERNAME,
                password=settings.INFOR_PASSWORD,
            )

            if step.step_name == "workshop_jbr":
                rows = await self._fetch_jbr_with_fallback(step, client, full_filter)
            else:
                props = [p.strip() for p in step.properties.split(",")]
                result = await client.load_collection(
                    ido_name=step.ido_name, properties=props, filter=full_filter, record_cap=0
                )

                # Validate Infor MessageCode
                message_code = result.get("message_code", 0)
                if message_code and message_code not in (0, 200, 210):
                    message = result.get("message", "")
                    logger.warning("Sync %s: Infor MessageCode=%s: %s", step.step_name, message_code, message)
                    raise RuntimeError(f"Infor MessageCode {message_code}: {message}")

                rows = result.get("data", [])

            logger.info(f"Sync {step.step_name}: fetched {len(rows)} rows")

            # Dispatch to importer
            import_result = await self._dispatch_step(step.step_name, rows, db, client=client)

            # Update state
            step.last_sync_at = start_time
            step.created_count = import_result.get("created_count", 0)
            step.updated_count = import_result.get("updated_count", 0)
            step.error_count = len(import_result.get("errors", []))
            step.last_error = None

            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            duration_ms = end_ms - start_ms

            # Log success
            db.add(
                SyncLog(
                    step_name=step.step_name,
                    status="success",
                    fetched_count=len(rows),
                    created_count=import_result.get("created_count", 0),
                    updated_count=import_result.get("updated_count", 0),
                    error_count=len(import_result.get("errors", [])),
                    duration_ms=duration_ms,
                )
            )

            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise

            logger.info(
                f"Sync {step.step_name}: success ({duration_ms}ms, "
                f"+{import_result.get('created_count', 0)}, "
                f"~{import_result.get('updated_count', 0)})"
            )

        except Exception as e:
            logger.error(f"Sync {step.step_name} failed: {e}", exc_info=True)

            step.last_error = str(e)[:500]

            db.add(SyncLog(step_name=step.step_name, status="error", error_message=str(e)[:500]))

            try:
                await db.commit()
            except Exception:
                await db.rollback()

    async def _dispatch_step(
        self, step_name: str, rows: List[Dict[str, Any]], db: AsyncSession, client=None
    ) -> Dict[str, Any]:
        """Dispatch rows to appropriate importer (preview → execute flow)."""
        if not rows:
            return {"created_count": 0, "updated_count": 0, "errors": []}

        if step_name == "parts":
            from app.services.infor_part_importer import PartImporter

            importer = PartImporter()
            preview = await importer.preview_import(rows, db)
            mapped = self._extract_valid_rows(preview)
            if mapped:
                return await importer.execute_import(mapped, db)
            return {"created_count": 0, "updated_count": 0, "errors": []}

        elif step_name == "materials":
            from app.services.infor_material_importer import MaterialImporter

            importer = MaterialImporter()
            preview = await importer.preview_import(rows, db)
            mapped = self._extract_valid_rows(preview)
            if mapped:
                return await importer.execute_import(mapped, db)
            return {"created_count": 0, "updated_count": 0, "errors": []}

        elif step_name == "operations":
            from app.services.infor_sync_dispatchers import dispatch_operations

            return await dispatch_operations(rows, db)

        elif step_name == "production":
            from app.services.infor_sync_dispatchers import dispatch_production

            return await dispatch_production(rows, db)

        elif step_name == "material_inputs":
            from app.services.infor_sync_dispatchers import dispatch_material_inputs

            return await dispatch_material_inputs(rows, db)

        elif step_name == "documents":
            from app.services.infor_sync_dispatchers import dispatch_documents

            if client is None:
                return {"created_count": 0, "updated_count": 0, "errors": ["No client for document sync"]}
            return await dispatch_documents(rows, client, db)

        elif step_name == "jobroutes_j":
            from app.services.infor_sync_dispatchers import dispatch_production
            from app.services.workshop_sync_dispatchers import dispatch_workshop_routes, dispatch_workshop_materials

            r1 = await dispatch_workshop_routes(rows, db)
            r2 = await dispatch_production(rows, db)
            # Prefetch materials pro aktivní operace (background-safe, nezdržuje sync)
            try:
                await dispatch_workshop_materials(db, client)
            except Exception as e:
                logger.warning("Materials prefetch failed: %s", e)
            return _merge_dispatch_results(r1, r2)

        elif step_name == "workshop_routes":
            from app.services.workshop_sync_dispatchers import dispatch_workshop_routes, dispatch_workshop_materials

            result = await dispatch_workshop_routes(rows, db)
            # Prefetch materials pro aktivní operace
            try:
                await dispatch_workshop_materials(db, client)
            except Exception as e:
                logger.warning("Materials prefetch failed: %s", e)
            return result

        elif step_name == "workshop_jbr":
            from app.services.workshop_sync_dispatchers import dispatch_workshop_jbr

            return await dispatch_workshop_jbr(rows, db)

        elif step_name == "workshop_orders":
            from app.services.workshop_sync_dispatchers import dispatch_workshop_orders

            return await dispatch_workshop_orders(rows, db)

        logger.warning(f"Unknown sync step: {step_name}")
        return {"created_count": 0, "updated_count": 0, "errors": [f"Unknown step: {step_name}"]}

    async def _fetch_jbr_with_fallback(
        self, step: SyncState, client: "InforAPIClient", full_filter: str
    ) -> List[Dict[str, Any]]:
        """Fetch JBR data with property-set fallback (unstable schema)."""
        # Use cached working propset if available
        if self._jbr_working_propset is not None:
            kwargs: Dict[str, Any] = {
                "ido_name": step.ido_name, "filter": full_filter, "record_cap": 0,
            }
            if self._jbr_working_propset:
                kwargs["properties"] = self._jbr_working_propset
            result = await client.load_collection(**kwargs)
            message_code = result.get("message_code", 0)
            if message_code and message_code not in (0, 200, 210):
                message = result.get("message", "")
                logger.warning("Sync %s: Infor MessageCode=%s: %s", step.step_name, message_code, message)
                raise RuntimeError(f"Infor MessageCode {message_code}: {message}")
            return result.get("data", [])

        # Try each property set (last one is [] = default columns)
        last_error = None
        for i, prop_set in enumerate(_JBR_PROP_SETS):
            try:
                kwargs = {
                    "ido_name": step.ido_name, "filter": full_filter, "record_cap": 0,
                }
                if prop_set:
                    kwargs["properties"] = prop_set
                result = await client.load_collection(**kwargs)
                message_code = result.get("message_code", 0)
                if message_code and message_code not in (0, 200, 210):
                    raise RuntimeError(f"Infor MessageCode {message_code}: {result.get('message', '')}")
                self._jbr_working_propset = prop_set
                logger.info("JBR: using property set %d: %s", i, prop_set or "(default columns)")
                return result.get("data", [])
            except Exception as e:
                last_error = e
                logger.warning("JBR property set %d failed: %s", i, e)
                continue

        raise RuntimeError(f"All JBR property sets failed. Last error: {last_error}")

    def _extract_valid_rows(self, preview_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract valid mapped rows from preview, add duplicate_action='update'."""
        valid = []
        for row in preview_result.get("rows", []):
            validation = row.get("validation", {})
            if validation.get("is_valid", False) or validation.get("is_duplicate", False):
                mapped = row.get("mapped_data", {})
                mapped["duplicate_action"] = "update"
                valid.append(mapped)
        return valid

    async def _ensure_default_steps(self):
        """Seed default step configs if DB is empty; add missing steps to existing DB."""
        async with async_session() as db:
            result = await db.execute(select(SyncState))
            existing_steps = result.scalars().all()
            existing_names = {s.step_name for s in existing_steps}

            if not existing_steps:
                # Fresh DB — seed all
                for step_data in DEFAULT_STEPS:
                    db.add(SyncState(**step_data))
                try:
                    await db.commit()
                    logger.info("Seeded default sync steps")
                except Exception:
                    await db.rollback()
                    raise
            else:
                # Existing DB — add missing steps, update workshop step configs
                added = 0
                updated = 0
                existing_by_name = {s.step_name: s for s in existing_steps}
                for step_data in DEFAULT_STEPS:
                    name = step_data["step_name"]
                    if name not in existing_names:
                        new_step = SyncState(**step_data)
                        # Watermark migration: jobroutes_j inherits from old production/workshop_routes
                        if name == "jobroutes_j":
                            old_watermarks = []
                            for old_name in ("production", "workshop_routes"):
                                old_step = existing_by_name.get(old_name)
                                if old_step and old_step.last_sync_at:
                                    old_watermarks.append(old_step.last_sync_at)
                            if old_watermarks:
                                new_step.last_sync_at = max(old_watermarks)
                                logger.info(
                                    "jobroutes_j: inherited watermark %s from old steps",
                                    new_step.last_sync_at,
                                )
                        db.add(new_step)
                        added += 1
                    elif name.startswith("workshop_"):
                        # Auto-update workshop steps to match DEFAULT config
                        # (e.g. date_field, enabled, interval changes)
                        existing_step = existing_by_name[name]
                        changed = False
                        for key in ("date_field", "enabled", "filter_template", "properties", "interval_seconds"):
                            default_val = step_data.get(key)
                            if default_val is not None and getattr(existing_step, key) != default_val:
                                setattr(existing_step, key, default_val)
                                changed = True
                        if changed:
                            updated += 1

                # Always disable old steps replaced by jobroutes_j
                if "jobroutes_j" in existing_names or added:
                    for old_name in ("production", "workshop_routes"):
                        old_step = existing_by_name.get(old_name)
                        if old_step and old_step.enabled:
                            old_step.enabled = False
                            updated += 1
                            logger.info("Disabled old step '%s' (replaced by jobroutes_j)", old_name)
                if added or updated:
                    try:
                        await db.commit()
                        if added:
                            logger.info("Added %d new sync steps to existing DB", added)
                        if updated:
                            logger.info("Updated %d workshop sync steps to match defaults", updated)
                    except Exception:
                        await db.rollback()
                        raise

    @property
    def running(self) -> bool:
        """Check if service is running."""
        return self._running


# Global singleton
infor_sync_service = InforSyncService()
