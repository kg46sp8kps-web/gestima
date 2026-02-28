"""GESTIMA — Workshop Cache Service

Background refresh cache pro workshop data (orders overview, wc queue, machine plan).
Eliminuje opakované HTTP volání do Infor REST API (3-8s → <50ms).

Architektura:
  - Singleton s asyncio background loop (vzor InforSyncService)
  - Cachuje fulltext datasety bez filtrů; filtry se aplikují in-memory
  - ETag (MD5 hash) pro 304 Not Modified support
  - Invalidace po zápisu (post_transaction, post_material_issue)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.infor_api_client import InforAPIClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    data: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: Optional[datetime] = None
    etag: str = ""
    refreshing: bool = False


def _compute_etag(data: List[Dict[str, Any]]) -> str:
    """Compute MD5 hash of JSON-serialized data for ETag."""
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.md5(raw).hexdigest()


# ---------------------------------------------------------------------------
# WorkshopCacheService
# ---------------------------------------------------------------------------

class WorkshopCacheService:
    """Background refresh cache pro workshop Infor data."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._entries: Dict[str, CacheEntry] = {
            "orders_overview": CacheEntry(),
            "wc_queue": CacheEntry(),
            "machine_plan": CacheEntry(),
        }
        self._intervals: Dict[str, int] = {}  # naplněno v start()
        self._client: Optional[InforAPIClient] = None

    # -- Public properties --------------------------------------------------

    @property
    def running(self) -> bool:
        return self._running

    def is_warm(self, name: str) -> bool:
        entry = self._entries.get(name)
        return entry is not None and entry.updated_at is not None

    def get_etag(self, name: str) -> str:
        entry = self._entries.get(name)
        return entry.etag if entry else ""

    def get_updated_at(self, name: str) -> Optional[datetime]:
        entry = self._entries.get(name)
        return entry.updated_at if entry else None

    def get_data(self, name: str) -> List[Dict[str, Any]]:
        entry = self._entries.get(name)
        return entry.data if entry else []

    def get_status(self) -> Dict[str, Any]:
        """Diagnostika — vrátí stav všech cache záznamů."""
        result: Dict[str, Any] = {"running": self._running, "entries": {}}
        for name, entry in self._entries.items():
            result["entries"][name] = {
                "warm": entry.updated_at is not None,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
                "etag": entry.etag,
                "count": len(entry.data),
                "refreshing": entry.refreshing,
                "interval_s": self._intervals.get(name, 0),
            }
        return result

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            logger.warning("WorkshopCacheService already running")
            return

        self._intervals = {
            "orders_overview": settings.WORKSHOP_CACHE_ORDERS_INTERVAL,
            "wc_queue": settings.WORKSHOP_CACHE_QUEUE_INTERVAL,
            "machine_plan": settings.WORKSHOP_CACHE_PLAN_INTERVAL,
        }

        self._client = InforAPIClient(
            base_url=settings.INFOR_API_URL,
            config=settings.INFOR_CONFIG,
            username=settings.INFOR_USERNAME,
            password=settings.INFOR_PASSWORD,
            verify_ssl=False,
        )

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "WorkshopCacheService started (intervals: orders=%ds, queue=%ds, plan=%ds)",
            self._intervals["orders_overview"],
            self._intervals["wc_queue"],
            self._intervals["machine_plan"],
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WorkshopCacheService stopped")

    # -- Invalidation -------------------------------------------------------

    def invalidate(self, name: str) -> None:
        """Invalidate a cache entry to force refresh on next loop cycle."""
        entry = self._entries.get(name)
        if entry:
            entry.updated_at = None
            logger.debug("Cache invalidated: %s", name)

    # -- Background loop ----------------------------------------------------

    async def _loop(self) -> None:
        """Background loop: initial refresh + periodic checks every 10s."""
        # Initial refresh — fill all caches before first request
        await self._refresh_all()

        while self._running:
            try:
                await asyncio.sleep(10)
                await self._check_and_refresh()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("WorkshopCacheService loop error")
                await asyncio.sleep(30)

    async def _refresh_all(self) -> None:
        """Refresh all caches concurrently."""
        tasks = [
            self._refresh_entry("orders_overview"),
            self._refresh_entry("wc_queue"),
            self._refresh_entry("machine_plan"),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_and_refresh(self) -> None:
        """Check which entries are stale and refresh them."""
        now = datetime.now(timezone.utc)
        tasks = []
        for name, entry in self._entries.items():
            if entry.refreshing:
                continue
            interval = self._intervals.get(name, 60)
            if entry.updated_at is None:
                tasks.append(self._refresh_entry(name))
            else:
                elapsed = (now - entry.updated_at).total_seconds()
                if elapsed >= interval:
                    tasks.append(self._refresh_entry(name))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _refresh_entry(self, name: str) -> None:
        """Refresh a single cache entry by fetching from Infor."""
        entry = self._entries[name]
        entry.refreshing = True
        t0 = time.monotonic()
        try:
            from app.services import workshop_service

            if name == "orders_overview":
                data = await workshop_service.fetch_orders_overview(
                    self._client,
                    limit=5000,
                )
            elif name == "wc_queue":
                data = await workshop_service.fetch_wc_queue(
                    self._client,
                    record_cap=2000,
                )
            elif name == "machine_plan":
                data = await workshop_service.fetch_machine_plan(
                    self._client,
                    record_cap=2000,
                )
            else:
                return

            etag = _compute_etag(data)
            entry.data = data
            entry.etag = etag
            entry.updated_at = datetime.now(timezone.utc)

            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "Cache refreshed: %s (%d items, %.0fms, etag=%s)",
                name, len(data), elapsed_ms, etag[:8],
            )
        except Exception:
            logger.exception("Cache refresh failed: %s", name)
        finally:
            entry.refreshing = False

    # -- Filtered access (in-memory) ----------------------------------------

    def get_orders_overview(
        self,
        *,
        customer: Optional[str] = None,
        due_from: Optional[str] = None,
        due_to: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        """Return cached orders overview with in-memory filtering."""
        data = self.get_data("orders_overview")
        if not data:
            return []

        result = data

        if customer:
            cust_upper = customer.strip().upper()
            result = [
                r for r in result
                if (r.get("customer_code") or "").upper() == cust_upper
            ]

        if due_from:
            result = [
                r for r in result
                if (r.get("due_date") or "") >= due_from
            ]

        if due_to:
            result = [
                r for r in result
                if (r.get("due_date") or "") <= due_to
            ]

        if search:
            s = search.strip().upper()
            result = [
                r for r in result
                if s in (r.get("co_num") or "").upper()
                or s in (r.get("item") or "").upper()
                or s in (r.get("description") or "").upper()
                or s in (r.get("selected_vp_job") or "").upper()
            ]

        return result[:limit]

    def get_wc_queue(
        self,
        *,
        wc: Optional[str] = None,
        job_filter: Optional[str] = None,
        sort_by: str = "OpDatumSt",
        sort_dir: str = "asc",
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Return cached queue with in-memory filtering and sorting."""
        from app.services.workshop_service import sort_queue

        data = self.get_data("wc_queue")
        if not data:
            return []

        result = data

        if wc:
            wc_upper = wc.strip().upper()
            result = [r for r in result if (r.get("Wc") or "").upper() == wc_upper]

        if job_filter:
            jf = job_filter.strip().upper()
            result = [r for r in result if jf in (r.get("Job") or "").upper()]

        result = sort_queue(result, sort_by=sort_by, sort_dir=sort_dir)
        return result[:limit]

    def get_machine_plan(
        self,
        *,
        wc: Optional[str] = None,
        job_filter: Optional[str] = None,
        sort_by: str = "OpDatumSt",
        sort_dir: str = "asc",
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return cached machine plan with in-memory filtering and sorting."""
        from app.services.workshop_service import sort_queue

        data = self.get_data("machine_plan")
        if not data:
            return []

        result = data

        if wc:
            wc_upper = wc.strip().upper()
            result = [r for r in result if (r.get("Wc") or "").upper() == wc_upper]

        if job_filter:
            jf = job_filter.strip().upper()
            result = [r for r in result if jf in (r.get("Job") or "").upper()]

        result = sort_queue(result, sort_by=sort_by, sort_dir=sort_dir)
        return result[:limit]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

workshop_cache = WorkshopCacheService()
