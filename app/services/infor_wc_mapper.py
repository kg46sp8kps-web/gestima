"""GESTIMA - Infor WorkCenter code → Gestima WorkCenter resolution

Maps Infor WorkCenter codes to Gestima WorkCenter IDs using configuration mapping.
Caches results to minimize DB queries.
"""

import json
import logging
from typing import Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_center import WorkCenter

logger = logging.getLogger(__name__)


class InforWcMapper:
    """
    Resolve Infor WorkCenter codes to Gestima work_center_id.

    Resolution order:
        1. Exact match: "KOO" → mapping["KOO"]
        2. Prefix fallback: "KOO1" → starts with "KOO" → mapping["KOO"]
        3. Not found → (None, warning)

    Configuration:
        INFOR_WC_MAPPING env variable (JSON dict):
        {"InforWcCode": "GestimaWcNumber"}

    Default mapping (config.py):
        PS/PSa/PSm/PSv → 80000011 (BOMAR STG240A)
        KOO → 80000016 (KOOPERACE) — prefix matches KOO1, KOOPB etc.
        See app/config.py for full list.

    Usage:
        mapper = InforWcMapper(settings.INFOR_WC_MAPPING)
        await mapper.warmup_cache(db)  # batch pre-resolve
        wc_id, warning = await mapper.resolve("KOO1", db)
    """

    def __init__(self, mapping_json: str):
        """
        Initialize mapper with JSON mapping.

        Args:
            mapping_json: JSON string dict {"InforCode": "GestimaNumber"}
        """
        try:
            self.mapping: Dict[str, str] = json.loads(mapping_json) if mapping_json else {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid INFOR_WC_MAPPING JSON: {e}")
            self.mapping = {}

        self._cache: Dict[str, Optional[int]] = {}

    async def resolve(
        self,
        infor_wc_code: str,
        db: AsyncSession
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Resolve Infor WC code to Gestima work_center_id.

        Returns (work_center_id, warning_or_none).
        Unknown codes return (None, warning_message).

        Args:
            infor_wc_code: Infor WorkCenter code (e.g., "100")
            db: Database session

        Returns:
            Tuple of (work_center_id, warning_message)
            - work_center_id is None if not found
            - warning_message is None if found successfully
        """
        if not infor_wc_code:
            return None, None

        code = str(infor_wc_code).strip()

        # Check cache first
        if code in self._cache:
            return self._cache[code], None

        # Check mapping configuration (exact match first, then prefix fallback)
        gestima_number = self.mapping.get(code)
        prefix_hit: Optional[str] = None
        if not gestima_number:
            # Prefix fallback: e.g., "KOO1" → match "KOO" entry
            for prefix_code, prefix_number in self.mapping.items():
                if code.startswith(prefix_code) and len(prefix_code) >= 2:
                    gestima_number = prefix_number
                    prefix_hit = prefix_code
                    logger.debug(f"Prefix match: '{code}' → '{prefix_code}' → {prefix_number}")
                    break
        if not gestima_number:
            warning = f"Neznámý Infor WC kód '{code}' — není v mapování"
            return None, warning

        # If prefix matched and the prefix key is already cached, reuse its wc_id
        if prefix_hit and prefix_hit in self._cache:
            wc_id = self._cache[prefix_hit]
            self._cache[code] = wc_id
            return wc_id, None

        # Resolve Gestima work_center_id from DB
        result = await db.execute(
            select(WorkCenter.id).where(
                WorkCenter.work_center_number == gestima_number,
                WorkCenter.deleted_at.is_(None)
            )
        )
        wc_id = result.scalar_one_or_none()

        if wc_id is None:
            warning = f"Gestima WC '{gestima_number}' neexistuje v DB"
            return None, warning

        # Cache successful resolution
        self._cache[code] = wc_id
        logger.debug(f"Resolved Infor WC '{code}' → Gestima WC {gestima_number} (id={wc_id})")
        return wc_id, None

    async def warmup_cache(self, db: AsyncSession) -> None:
        """
        Pre-resolve all mapping entries to avoid per-row DB queries.
        Call once before processing large batches.
        """
        if self._cache:
            return  # Already warmed up

        if not self.mapping:
            return

        gestima_numbers = list(self.mapping.values())
        result = await db.execute(
            select(WorkCenter.id, WorkCenter.work_center_number).where(
                WorkCenter.work_center_number.in_(gestima_numbers),
                WorkCenter.deleted_at.is_(None)
            )
        )
        wc_by_number = {row[1]: row[0] for row in result.all()}

        for infor_code, gestima_number in self.mapping.items():
            wc_id = wc_by_number.get(gestima_number)
            if wc_id:
                self._cache[infor_code] = wc_id

        logger.info(f"WC cache warmed: {len(self._cache)} entries from {len(self.mapping)} mappings")

    def get_mapping(self) -> Dict[str, str]:
        """
        Get current mapping configuration.

        Returns:
            Dict mapping Infor codes to Gestima numbers
        """
        return dict(self.mapping)

    def update_mapping(self, new_mapping: Dict[str, str]) -> None:
        """
        Update mapping configuration.
        Clears cache to force re-resolution.

        Args:
            new_mapping: New mapping dict {"InforCode": "GestimaNumber"}
        """
        self.mapping = dict(new_mapping)
        self._cache.clear()
        logger.info(f"Updated WC mapping: {len(self.mapping)} entries")
