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
        "step_name": "production",
        "ido_name": "SLJobRoutes",
        "filter_template": "Type = 'J'",
        "properties": "Job,JobItem,OperNum,Wc,JobQtyReleased,JshSetupHrs,DerRunMchHrs,DerRunLbrHrs,SetupHrsT,RunHrsTMch,RunHrsTLbr,ObsDate",
        "date_field": "RecordDate",
        "interval_seconds": 30,
    },
]


class InforSyncService:
    """Background sync service using asyncio task scheduler."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

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
            # Build date filter
            if step.last_sync_at:
                since = step.last_sync_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # First sync: lookback
                lookback_date = start_time - timedelta(days=settings.INFOR_SYNC_INITIAL_LOOKBACK_DAYS)
                since = lookback_date.strftime("%Y-%m-%d %H:%M:%S")

            date_filter = f"{step.date_field} >= '{since}'"
            full_filter = f"{step.filter_template} AND {date_filter}" if step.filter_template else date_filter

            # Fetch from Infor
            client = InforAPIClient(
                base_url=settings.INFOR_API_URL,
                config=settings.INFOR_CONFIG,
                username=settings.INFOR_USERNAME,
                password=settings.INFOR_PASSWORD,
            )

            props = [p.strip() for p in step.properties.split(",")]
            result = await client.load_collection(
                ido_name=step.ido_name, properties=props, filter=full_filter, record_cap=0
            )
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

        logger.warning(f"Unknown sync step: {step_name}")
        return {"created_count": 0, "updated_count": 0, "errors": [f"Unknown step: {step_name}"]}

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
        """Seed default step configs if DB is empty."""
        async with async_session() as db:
            result = await db.execute(select(SyncState))
            existing = result.scalars().first()

            if existing is None:
                for step_data in DEFAULT_STEPS:
                    db.add(SyncState(**step_data))

                try:
                    await db.commit()
                    logger.info("Seeded default sync steps")
                except Exception:
                    await db.rollback()
                    raise

    @property
    def running(self) -> bool:
        """Check if service is running."""
        return self._running


# Global singleton
infor_sync_service = InforSyncService()
