"""GESTIMA - MaterialInput importer from Infor SLJobmatls

Imports MaterialInputs (material assignments) from Infor SLJobmatls (planned materials).
Uses generic InforImporterBase infrastructure with MaterialItem resolution.

Simple lookup: Item code → existing MaterialItem in Gestima.
If MaterialItem not found → error (user must import material items first).

Field conversions:
    ItmItem       → article_number (temp, for Part lookup in router)
    Item          → material_item_code (for MaterialItem lookup)
    OperNum       → operation_seq (for Operation linking, stored in mapped_data)
    MatlQtyConv   → matl_qty (raw value, interpretation depends on UM)
    UM            → unit (mm → stock_length, kg → weight, ks/pcs → quantity)
"""

import logging
from typing import Dict, Any, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material_input import MaterialInput
from app.models.material import MaterialItem
from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
)

logger = logging.getLogger(__name__)


class JobMaterialsImporter(InforImporterBase[MaterialInput]):
    """
    Importer for MaterialInput from Infor SLJobmatls (planned materials).

    Simple lookup-based import:
    - Item code → MaterialItem.code match in Gestima DB
    - Found → use MaterialItem's shape, dims, price_category_id
    - Not found → ERROR (must import material items first)

    Field mappings:
    - ItmItem       → article_number (Part lookup key, not stored)
    - Item          → material_item_code (MaterialItem lookup key)
    - OperNum       → operation_seq (for M:N operation link)
    - MatlQtyConv   → matl_qty (raw value, interpretation depends on UM)
    - UM            → unit (mm/kg/ks)

    Requires:
        - part_id context (passed via constructor)
        - material_items_cache (pre-loaded by router, keyed by code)
        - operations_cache (pre-loaded by router, keyed by (part_id, seq))
    """

    def __init__(
        self,
        part_id: int,
        material_items_cache: Dict[str, MaterialItem],
        operations_cache: Dict[Tuple[int, int], int],
    ) -> None:
        """
        Initialize importer with Part context and pre-loaded caches.

        Args:
            part_id: Target Part.id for all MaterialInputs
            material_items_cache: Pre-loaded MaterialItems keyed by code
            operations_cache: Pre-loaded (part_id, seq) → operation_id mapping
        """
        super().__init__()
        self.part_id = part_id
        self.material_items_cache = material_items_cache
        self.operations_cache = operations_cache

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for MaterialInput import."""
        return InforImporterConfig(
            entity_name="MaterialInput",
            ido_name="SLJobmatls",
            field_mappings=[
                FieldMapping("ItmItem", "article_number", required=True),
                FieldMapping("Item", "material_item_code", required=True),
                FieldMapping(
                    "OperNum",
                    "operation_seq",
                    required=False,
                    transform=lambda x: int(float(x)),
                ),
                FieldMapping(
                    "MatlQtyConv",
                    "matl_qty",
                    required=False,
                    transform=float,
                ),
                FieldMapping("UM", "unit", required=False),
            ],
            duplicate_check_field="material_item_code",
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Custom mapping for MaterialInput.

        Simple lookup: match material_item_code → existing MaterialItem in Gestima.
        All material data (shape, dimensions, price_category) comes from MaterialItem.
        If MaterialItem not found → material_item_id=None (router marks as ERROR).

        Args:
            row: Raw Infor SLJobmatls row
            basic_mapped: Basic field-mapped data
            db: Database session

        Returns:
            Dict with resolved material fields and operation linkage data
        """
        custom: Dict[str, Any] = {}

        material_item_code = str(basic_mapped.get("material_item_code") or "").strip()
        matl_qty = basic_mapped.get("matl_qty")
        unit = str(basic_mapped.get("unit") or "").strip().lower()
        operation_seq = basic_mapped.get("operation_seq")

        # === MaterialItem lookup (simple match by code) ===
        item = self.material_items_cache.get(material_item_code)

        if item is not None:
            custom["material_item_id"] = item.id
            custom["price_category_id"] = item.price_category_id
            custom["stock_shape"] = item.shape
            custom["stock_diameter"] = item.diameter
            custom["stock_width"] = item.width
            custom["stock_height"] = item.thickness
            custom["stock_wall_thickness"] = item.wall_thickness
            custom["stock_length"] = item.standard_length
        else:
            # Not found — router will mark this as error
            logger.warning(
                f"MaterialItem not found for code '{material_item_code}'"
            )
            custom["material_item_id"] = None
            custom["price_category_id"] = None
            custom["stock_shape"] = None
            custom["stock_diameter"] = None
            custom["stock_width"] = None
            custom["stock_height"] = None
            custom["stock_wall_thickness"] = None
            custom["stock_length"] = None

        # === MatlQtyConv interpretation based on UM (unit of measure) ===
        custom["unit"] = unit
        custom["matl_qty"] = matl_qty
        custom["quantity"] = 1  # default

        if matl_qty and matl_qty > 0:
            if unit == "mm":
                # MatlQtyConv is cut length in mm → stock_length
                custom["stock_length"] = matl_qty
            elif unit in ("ks", "pcs", "ea"):
                # MatlQtyConv is piece count
                custom["quantity"] = max(1, round(matl_qty))
            # kg, m, etc. → store raw value, don't override stock_length

        # === Operation linkage ===
        custom["operation_seq"] = operation_seq
        if operation_seq is not None:
            custom["_operation_id"] = self.operations_cache.get(
                (self.part_id, operation_seq)
            )
        else:
            custom["_operation_id"] = None

        return custom

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession,
    ) -> Optional[MaterialInput]:
        """
        Check if MaterialInput for same part_id + material_item_id exists.

        Note: If material_item_id is None (unresolved item), duplicate check is skipped.
        Actual in-memory duplicate checking in the router uses a pre-loaded set.

        Args:
            mapped_data: Mapped data dict
            db: Database session

        Returns:
            Existing MaterialInput or None
        """
        material_item_id = mapped_data.get("material_item_id")
        if material_item_id is None:
            return None

        result = await db.execute(
            select(MaterialInput).where(
                MaterialInput.part_id == self.part_id,
                MaterialInput.material_item_id == material_item_id,
                MaterialInput.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession,
    ) -> MaterialInput:
        """
        Create MaterialInput instance from mapped data.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            MaterialInput instance (not yet committed)
        """
        material_input = MaterialInput(
            part_id=self.part_id,
            seq=mapped_data.get("seq", 0),
            price_category_id=mapped_data.get("price_category_id"),
            material_item_id=mapped_data.get("material_item_id"),
            stock_shape=mapped_data.get("stock_shape"),
            stock_diameter=mapped_data.get("stock_diameter"),
            stock_length=mapped_data.get("stock_length"),
            stock_width=mapped_data.get("stock_width"),
            stock_height=mapped_data.get("stock_height"),
            stock_wall_thickness=mapped_data.get("stock_wall_thickness"),
            quantity=mapped_data.get("quantity", 1),
            notes=f"Infor import: {mapped_data.get('material_item_code', '')}",
        )

        logger.info(
            f"Created MaterialInput: part_id={material_input.part_id}, "
            f"material_item_id={material_input.material_item_id}, "
            f"shape={material_input.stock_shape}"
        )
        return material_input

    async def update_entity(
        self,
        existing: MaterialInput,
        mapped_data: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """
        Update mutable fields of an existing MaterialInput.

        Args:
            existing: Existing MaterialInput instance
            mapped_data: New mapped data
            db: Database session
        """
        existing.quantity = mapped_data.get("quantity", existing.quantity)
        existing.stock_diameter = mapped_data.get("stock_diameter", existing.stock_diameter)
        existing.stock_length = mapped_data.get("stock_length", existing.stock_length)
        existing.stock_width = mapped_data.get("stock_width", existing.stock_width)
        existing.stock_height = mapped_data.get("stock_height", existing.stock_height)
        existing.stock_wall_thickness = mapped_data.get(
            "stock_wall_thickness", existing.stock_wall_thickness
        )

        logger.info(
            f"Updated MaterialInput: id={existing.id}, part_id={existing.part_id}"
        )
