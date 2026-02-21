"""GESTIMA - ProductionRecord importer from Infor SLJobRoutes (Type='J')

Imports ProductionRecords (actual production times) from Infor Job Routes IDO.
Uses generic InforImporterBase infrastructure with Part + WC resolution.

Field conversions:
    JshSetupHrs         → planned_setup_min = JshSetupHrs * 60
    DerRunMchHrs        → planned_time_min = 60 / DerRunMchHrs (min/ks, same as routing)
    DerRunMchHrs/DerRunLbrHrs → manning_coefficient = (MchHrs / LbrHrs) * 100 (% obsluhy u stroje)
    SetupHrsT           → actual_setup_min = SetupHrsT * 60
    RunHrsTMch          → actual_run_machine_min = RunHrsTMch * 60 (whole batch)
    RunHrsTLbr          → actual_run_labor_min = RunHrsTLbr * 60 (whole batch)
    RunHrsTMch / batch_quantity → actual_time_min (per-piece)

Special WC handling (same as routing):
    Wc starts with 'CLO' → skip row
    Wc == 'CADCAM'       → skip row
    ObsDate present      → skip row
    Wc starts with 'KOO' → kooperace: times=0, manning=100%
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_record import ProductionRecord
from app.models.part import Part
from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
)
from app.services.infor_wc_mapper import InforWcMapper

logger = logging.getLogger(__name__)


class ProductionImporter(InforImporterBase[ProductionRecord]):
    """
    Importer for ProductionRecord from Infor SLJobRoutes (Type='J').

    Field mappings (from IDO discovery):
    - Job          → infor_order_number (required)
    - JobItem      → article_number (temp, for Part lookup)
    - OperNum      → operation_seq
    - Wc           → infor_wc_code (temp, resolved via InforWcMapper)
    - JobQtyReleased → batch_quantity
    - JshSetupHrs  → planned_setup_hours (temp)
    - DerRunMchHrs → pcs_per_hour_machine (temp)
    - DerRunLbrHrs → pcs_per_hour_labor (temp)
    - SetupHrsT    → actual_setup_hours (temp)
    - RunHrsTMch   → actual_run_machine_hours (temp)
    - RunHrsTLbr   → actual_run_labor_hours (temp)

    Requires:
        - wc_mapper (InforWcMapper instance)
        - part_id comes from mapped_data (resolved per row via JobItem)
    """

    def __init__(self, wc_mapper: InforWcMapper):
        """
        Initialize importer with WC mapper.

        Args:
            wc_mapper: InforWcMapper instance for WC resolution
        """
        super().__init__()
        self.wc_mapper = wc_mapper

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for ProductionRecord import."""
        return InforImporterConfig(
            entity_name="ProductionRecord",
            ido_name="SLJobRoutes",
            field_mappings=[
                # Required fields
                FieldMapping("Job", "infor_order_number", required=True),
                # Temp fields (removed after map_row_custom)
                FieldMapping("JobItem", "article_number", required=False),
                FieldMapping("Wc", "infor_wc_code", required=False),
                FieldMapping("JshSetupHrs", "planned_setup_hours", required=False, transform=float),
                FieldMapping("DerRunMchHrs", "pcs_per_hour_machine", required=False, transform=float),
                FieldMapping("DerRunLbrHrs", "pcs_per_hour_labor", required=False, transform=float),
                FieldMapping("SetupHrsT", "actual_setup_hours", required=False, transform=float),
                FieldMapping("RunHrsTMch", "actual_run_machine_hours", required=False, transform=float),
                FieldMapping("RunHrsTLbr", "actual_run_labor_hours", required=False, transform=float),
                # Direct fields (Infor returns "49.00" not "49" — must float→int)
                FieldMapping("OperNum", "operation_seq", required=False, transform=lambda x: int(float(x))),
                FieldMapping("JobQtyReleased", "batch_quantity", required=False, transform=lambda x: int(float(x))),
            ],
            duplicate_check_field="infor_order_number"
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Custom mapping for ProductionRecord.

        - Skip rules: CLO*, CADCAM, ObsDate
        - KOO* → kooperace: times=0, manning=100%
        - Resolves part_id from article_number
        - Resolves work_center_id from Infor WC code
        - Converts hours to minutes

        Args:
            row: Raw Infor row
            basic_mapped: Basic field-mapped data
            db: Database session

        Returns:
            Dict with additional custom fields
        """
        custom: Dict[str, Any] = {}

        # === Skip rules: CLO*, CADCAM, ObsDate ===
        infor_wc_code = str(basic_mapped.get("infor_wc_code") or "").strip()

        if infor_wc_code.startswith("CLO") or infor_wc_code == "CADCAM":
            custom["_skip"] = True
            return custom

        obs_date = row.get("ObsDate")
        if obs_date:
            custom["_skip"] = True
            return custom

        is_coop = infor_wc_code.startswith("KOO")

        # === Part lookup ===
        article_number = basic_mapped.get("article_number")
        if article_number:
            part_id = await self._resolve_part_id(str(article_number), db)
            custom["part_id"] = part_id
            if not part_id:
                logger.warning(f"Part not found for article_number '{article_number}'")
        else:
            custom["part_id"] = None

        # === WC resolution ===
        if infor_wc_code:
            wc_id, warning = await self.wc_mapper.resolve(infor_wc_code, db)
            custom["work_center_id"] = wc_id
            if warning:
                logger.warning(
                    f"WC resolution failed for seq {basic_mapped.get('operation_seq')}: {warning}"
                )
        else:
            custom["work_center_id"] = None

        # === Time conversions ===
        pcs_per_hour_mch = basic_mapped.get("pcs_per_hour_machine")
        pcs_per_hour_lbr = basic_mapped.get("pcs_per_hour_labor")
        batch_qty = basic_mapped.get("batch_quantity")

        if is_coop:
            # Kooperace — times have no meaning, zero them out
            custom["planned_time_min"] = 0.0
            custom["planned_labor_time_min"] = 0.0
            custom["planned_setup_min"] = 0.0
            custom["manning_coefficient"] = 100.0
            custom["actual_manning_coefficient"] = None
            custom["actual_time_min"] = None
            custom["actual_labor_time_min"] = None
            custom["actual_setup_min"] = None
            custom["actual_run_machine_min"] = None
            custom["actual_run_labor_min"] = None
        else:
            # === PLANNED per piece (from norms) ===
            # planned_time_min = 60 / DerRunMchHrs (stroj min/ks)
            if pcs_per_hour_mch and pcs_per_hour_mch > 0:
                custom["planned_time_min"] = round(60.0 / pcs_per_hour_mch, 4)
            else:
                custom["planned_time_min"] = 0.0

            # planned_labor_time_min = 60 / DerRunLbrHrs (obsluha min/ks)
            if pcs_per_hour_lbr and pcs_per_hour_lbr > 0:
                custom["planned_labor_time_min"] = round(60.0 / pcs_per_hour_lbr, 4)
            else:
                custom["planned_labor_time_min"] = 0.0

            # planned_setup_min = JshSetupHrs * 60
            setup_hours = basic_mapped.get("planned_setup_hours")
            custom["planned_setup_min"] = round(setup_hours * 60, 2) if setup_hours else 0.0

            # manning_coefficient = (DerRunMchHrs / DerRunLbrHrs) * 100
            # DerRun* = ks/hod. Obsluha 2 strojů → LbrHrs=2*MchHrs → Mch/Lbr=50%
            # = % času, kolik obsluha věnuje stroji
            if pcs_per_hour_lbr and pcs_per_hour_lbr > 0 and pcs_per_hour_mch:
                custom["manning_coefficient"] = round(
                    (pcs_per_hour_mch / pcs_per_hour_lbr) * 100, 1
                )
            else:
                custom["manning_coefficient"] = 100.0

            # === ACTUAL setup ===
            actual_setup_hours = basic_mapped.get("actual_setup_hours")
            custom["actual_setup_min"] = (
                round(actual_setup_hours * 60, 2) if actual_setup_hours else None
            )

            # === ACTUAL batch totals ===
            actual_run_mch = basic_mapped.get("actual_run_machine_hours")
            custom["actual_run_machine_min"] = (
                round(actual_run_mch * 60, 2) if actual_run_mch else None
            )

            actual_run_lbr = basic_mapped.get("actual_run_labor_hours")
            custom["actual_run_labor_min"] = (
                round(actual_run_lbr * 60, 2) if actual_run_lbr else None
            )

            # === ACTUAL per piece (computed from batch totals) ===
            # actual_time_min = (RunHrsTMch * 60) / qty (stroj min/ks)
            if actual_run_mch and batch_qty and batch_qty > 0:
                custom["actual_time_min"] = round((actual_run_mch * 60) / batch_qty, 4)
            else:
                custom["actual_time_min"] = None

            # actual_labor_time_min = (RunHrsTLbr * 60) / qty (obsluha min/ks)
            if actual_run_lbr and batch_qty and batch_qty > 0:
                custom["actual_labor_time_min"] = round((actual_run_lbr * 60) / batch_qty, 4)
            else:
                custom["actual_labor_time_min"] = None

            # actual_manning_coefficient = (RunHrsTLbr / RunHrsTMch) * 100
            # RunHrsT* = hodiny celé dávky. Obsluha 2 strojů → Lbr=Mch/2 → 50%
            # = % času, kolik obsluha věnuje stroji
            if actual_run_mch and actual_run_mch > 0 and actual_run_lbr:
                custom["actual_manning_coefficient"] = round(
                    (actual_run_lbr / actual_run_mch) * 100, 1
                )
            else:
                custom["actual_manning_coefficient"] = None

        # === Source ===
        custom["source"] = "infor"

        # === Clean up temp fields (keep infor_wc_code for UI display) ===
        custom["article_number"] = None
        custom["planned_setup_hours"] = None
        custom["pcs_per_hour_machine"] = None
        custom["pcs_per_hour_labor"] = None
        custom["actual_setup_hours"] = None
        custom["actual_run_machine_hours"] = None
        custom["actual_run_labor_hours"] = None

        return custom

    async def _resolve_part_id(
        self,
        article_number: str,
        db: AsyncSession
    ) -> Optional[int]:
        """
        Resolve Part.id from article_number.

        Args:
            article_number: Article number from Infor
            db: Database session

        Returns:
            Part.id or None if not found
        """
        result = await db.execute(
            select(Part.id).where(
                Part.article_number == article_number,
                Part.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> ProductionRecord:
        """
        Create ProductionRecord instance from fully mapped data.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            ProductionRecord instance (not yet committed)
        """
        record = ProductionRecord(
            part_id=mapped_data.get("part_id"),
            infor_order_number=mapped_data.get("infor_order_number"),
            batch_quantity=mapped_data.get("batch_quantity"),
            operation_seq=mapped_data.get("operation_seq"),
            work_center_id=mapped_data.get("work_center_id"),
            planned_time_min=mapped_data.get("planned_time_min"),
            planned_labor_time_min=mapped_data.get("planned_labor_time_min"),
            planned_setup_min=mapped_data.get("planned_setup_min"),
            actual_time_min=mapped_data.get("actual_time_min"),
            actual_labor_time_min=mapped_data.get("actual_labor_time_min"),
            actual_setup_min=mapped_data.get("actual_setup_min"),
            actual_run_machine_min=mapped_data.get("actual_run_machine_min"),
            actual_run_labor_min=mapped_data.get("actual_run_labor_min"),
            manning_coefficient=mapped_data.get("manning_coefficient"),
            actual_manning_coefficient=mapped_data.get("actual_manning_coefficient"),
            source="infor",
        )

        logger.info(
            f"Created ProductionRecord: order={record.infor_order_number}, "
            f"part_id={record.part_id}, seq={record.operation_seq}"
        )
        return record

    async def update_entity(
        self,
        existing: ProductionRecord,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Update existing ProductionRecord (only mutable fields).

        Args:
            existing: Existing ProductionRecord instance
            mapped_data: New mapped data
            db: Database session
        """
        existing.batch_quantity = mapped_data.get("batch_quantity")
        existing.work_center_id = mapped_data.get("work_center_id")
        existing.planned_time_min = mapped_data.get("planned_time_min")
        existing.planned_labor_time_min = mapped_data.get("planned_labor_time_min")
        existing.planned_setup_min = mapped_data.get("planned_setup_min")
        existing.actual_time_min = mapped_data.get("actual_time_min")
        existing.actual_labor_time_min = mapped_data.get("actual_labor_time_min")
        existing.actual_setup_min = mapped_data.get("actual_setup_min")
        existing.actual_run_machine_min = mapped_data.get("actual_run_machine_min")
        existing.actual_run_labor_min = mapped_data.get("actual_run_labor_min")
        existing.manning_coefficient = mapped_data.get("manning_coefficient")
        existing.actual_manning_coefficient = mapped_data.get("actual_manning_coefficient")

        logger.info(
            f"Updated ProductionRecord: order={existing.infor_order_number}, "
            f"part_id={existing.part_id}, seq={existing.operation_seq}"
        )

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[ProductionRecord]:
        """
        Check if ProductionRecord with same part_id + order + seq exists.

        Args:
            mapped_data: Mapped data dict
            db: Database session

        Returns:
            Existing ProductionRecord or None
        """
        part_id = mapped_data.get("part_id")
        infor_order_number = mapped_data.get("infor_order_number")
        operation_seq = mapped_data.get("operation_seq")

        if not part_id or not infor_order_number or not operation_seq:
            return None

        result = await db.execute(
            select(ProductionRecord).where(
                ProductionRecord.part_id == part_id,
                ProductionRecord.infor_order_number == infor_order_number,
                ProductionRecord.operation_seq == operation_seq,
                ProductionRecord.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
