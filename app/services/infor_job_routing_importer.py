"""GESTIMA - Operation importer from Infor SLJobRoutes

Imports Operations (seq, times, work center) from Infor SLJobRoutes (planned routing).
Uses generic InforImporterBase infrastructure with WC mapping.

Field conversions:
    DerRunMchHrs = ks/hod strojní → operation_time_min = 60 / DerRunMchHrs
    DerRunLbrHrs = ks/hod obsluha → manning_coefficient = (DerRunMchHrs / DerRunLbrHrs) * 100
    JshSetupHrs = seřizovací hodiny → setup_time_min = JshSetupHrs * 60 (fallback JshSchedHrs)

Special WC handling:
    Wc starts with 'KOO' → kooperace (is_coop=True)
    Wc starts with 'CLO' → skip row (not imported)
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation import Operation
from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
)
from app.services.infor_wc_mapper import InforWcMapper

logger = logging.getLogger(__name__)


class JobRoutingImporter(InforImporterBase[Operation]):
    """
    Importer for Operation from Infor SLJobRoutes (planned routing).

    Field mappings (from IDO discovery):
    - OperNum → seq (operation sequence number)
    - Wc → infor_wc_code (resolved via InforWcMapper)
    - DerRunMchHrs → pcs_per_hour_machine (ks/hod strojní)
    - DerRunLbrHrs → pcs_per_hour_labor (ks/hod obsluha)

    Conversions:
    - operation_time_min = 60 / DerRunMchHrs (ks/hod → min/ks)
    - manning_coefficient = (DerRunMchHrs / DerRunLbrHrs) * 100
      (e.g., stroj 100 ks/hod, obsluha 303 ks/hod → 33%)

    Special WC:
    - KOO* → kooperace (is_coop=True, časy=0)
    - CLO* → skip (řádek se neimportuje)

    Requires:
        - part_id context (passed via constructor)
        - wc_mapper (InforWcMapper instance)
    """

    def __init__(self, part_id: int, wc_mapper: InforWcMapper):
        """
        Initialize importer with Part context.

        Args:
            part_id: Target Part.id for all Operations
            wc_mapper: InforWcMapper instance for WC resolution
        """
        super().__init__()
        self.part_id = part_id
        self.wc_mapper = wc_mapper

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for Operation import."""
        return InforImporterConfig(
            entity_name="Operation",
            ido_name="SLJobRoutes",
            field_mappings=[
                # Required fields
                FieldMapping("OperNum", "seq", required=True, transform=lambda x: int(float(x))),
                # Optional fields
                FieldMapping("Wc", "infor_wc_code", required=False),
                FieldMapping("DerRunMchHrs", "pcs_per_hour_machine", required=False, transform=float),
                FieldMapping("DerRunLbrHrs", "pcs_per_hour_labor", required=False, transform=float),
                FieldMapping("JshSetupHrs", "setup_time_hours", required=False, transform=float),
                FieldMapping("JshSchedHrs", "sched_time_hours", required=False, transform=float),
            ],
            duplicate_check_field="seq"
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Custom mapping for Operation.

        - Resolves work_center_id from Infor WC code
        - Converts hours to minutes

        Args:
            row: Raw Infor row
            basic_mapped: Basic field-mapped data
            db: Database session

        Returns:
            Dict with additional custom fields
        """
        custom = {}

        # === WC handling: CLO = skip, KOO = kooperace ===
        infor_wc_code = str(basic_mapped.get("infor_wc_code") or "").strip()

        if infor_wc_code.startswith("CLO") or infor_wc_code == "CADCAM":
            # CLO*, CADCAM = skip this row entirely
            custom["_skip"] = True
            return custom

        # Skip rows that contain ObsDate (obsolete operations)
        obs_date = row.get("ObsDate")
        if obs_date:
            custom["_skip"] = True
            return custom

        is_coop = infor_wc_code.startswith("KOO")
        custom["is_coop"] = is_coop

        # Resolve work_center_id via WC mapper (včetně kooperací — KOO má své WC)
        if infor_wc_code:
            wc_id, warning = await self.wc_mapper.resolve(infor_wc_code, db)
            custom["work_center_id"] = wc_id
            if warning:
                logger.warning(f"WC resolution failed for seq {basic_mapped.get('seq')}: {warning}")
        else:
            custom["work_center_id"] = None

        # DerRunMchHrs / DerRunLbrHrs = ks/hod
        pcs_per_hour_mch = basic_mapped.get("pcs_per_hour_machine")
        pcs_per_hour_lbr = basic_mapped.get("pcs_per_hour_labor")

        if is_coop:
            # Kooperace — časy nemají smysl, nulujeme
            custom["operation_time_min"] = 0.0
            custom["manning_coefficient"] = 100.0
        else:
            # operation_time_min = 60 / ks_hod (e.g., 60 ks/hod → 1 min/ks)
            if pcs_per_hour_mch and pcs_per_hour_mch > 0:
                custom["operation_time_min"] = round(60.0 / pcs_per_hour_mch, 4)
            else:
                custom["operation_time_min"] = 0.0

            # Manning = (machine / labor) * 100
            # Stroj 100 ks/hod, obsluha 303 ks/hod → 100/303*100 = 33%
            # Obsluha je rychlejší → obsluhuje stroj jen 33% času
            if pcs_per_hour_lbr and pcs_per_hour_lbr > 0 and pcs_per_hour_mch:
                custom["manning_coefficient"] = round((pcs_per_hour_mch / pcs_per_hour_lbr) * 100, 1)
            else:
                custom["manning_coefficient"] = 100.0

        # JshSetupHrs → setup_time_min, fallback na JshSchedHrs
        setup_hours = basic_mapped.get("setup_time_hours")
        sched_hours = basic_mapped.get("sched_time_hours")

        if setup_hours and setup_hours > 0:
            custom["setup_time_min"] = round(setup_hours * 60, 2)
        elif sched_hours and sched_hours > 0:
            custom["setup_time_min"] = round(sched_hours * 60, 2)
        else:
            custom["setup_time_min"] = 0.0

        # JshSchedHrs pro porovnání v staging tabulce
        custom["sched_time_min"] = round(sched_hours * 60, 2) if sched_hours and sched_hours > 0 else None

        # Remove temp fields from mapped data (keep infor_wc_code for staging display)
        custom["pcs_per_hour_machine"] = None
        custom["pcs_per_hour_labor"] = None
        custom["setup_time_hours"] = None
        custom["sched_time_hours"] = None

        return custom

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Operation:
        """
        Create Operation instance.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            Operation instance (not yet committed)
        """
        is_coop = mapped_data.get("is_coop", False)
        operation = Operation(
            part_id=self.part_id,
            seq=mapped_data.get("seq"),
            name=mapped_data.get("name", ""),
            type="coop" if is_coop else "turning",
            icon="truck" if is_coop else "settings",
            work_center_id=mapped_data.get("work_center_id"),
            cutting_mode="mid",
            setup_time_min=mapped_data.get("setup_time_min", 0.0),
            operation_time_min=mapped_data.get("operation_time_min", 0.0),
            setup_time_locked=False,
            operation_time_locked=False,
            manning_coefficient=mapped_data.get("manning_coefficient", 100.0),
            machine_utilization_coefficient=100.0,
            is_coop=is_coop,
            coop_price=0.0,
            coop_min_price=0.0,
            coop_days=0
        )

        logger.info(
            f"Created Operation: seq={operation.seq}, part_id={operation.part_id}, "
            f"wc_id={operation.work_center_id}"
        )
        return operation

    async def update_entity(
        self,
        existing: Operation,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Update existing Operation (only mutable fields).

        Args:
            existing: Existing Operation instance
            mapped_data: New mapped data
            db: Database session
        """
        # Update mutable fields
        existing.work_center_id = mapped_data.get("work_center_id")
        existing.setup_time_min = mapped_data.get("setup_time_min", 30.0)
        existing.operation_time_min = mapped_data.get("operation_time_min", 0.0)
        existing.manning_coefficient = mapped_data.get("manning_coefficient", 100.0)

        logger.info(
            f"Updated Operation: seq={existing.seq}, part_id={existing.part_id}"
        )

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Operation]:
        """
        Check if Operation with same part_id + seq exists.

        Args:
            mapped_data: Mapped data dict
            db: Database session

        Returns:
            Existing Operation or None
        """
        seq = mapped_data.get("seq")
        if not seq:
            return None

        result = await db.execute(
            select(Operation).where(
                Operation.part_id == self.part_id,
                Operation.seq == seq,
                Operation.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
