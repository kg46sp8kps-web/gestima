"""GESTIMA - Material Importer (uses generic base)

Specific implementation for importing materials from Infor SLItems to Gestima MaterialItem.
"""

import re
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
    ValidationResult
)
from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialItem, StockShape
from app.models.material_norm import MaterialNorm
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


# === SHAPE DETECTION PATTERNS ===

SHAPE_PATTERNS = {
    StockShape.ROUND_BAR: [
        r"tyč\s+kruhov[áý]",
        r"kulatina",
        r"Ø\s*\d+",
        r"D\s*\d+",
        r"round\s+bar",
    ],
    StockShape.SQUARE_BAR: [
        r"tyč\s+čtverco?v[áý]",
        r"□\s*\d+",
        r"square\s+bar",
    ],
    StockShape.FLAT_BAR: [
        r"tyč\s+ploch[áý]",
        r"plochá",
        r"flat\s+bar",
    ],
    StockShape.HEXAGONAL_BAR: [
        r"šestihr[aá]n",  # šestihran, šestihranná, šestihranný
        r"⬡\s*\d+",
        r"hex",
    ],
    StockShape.PLATE: [
        r"plech",
        r"plate",
        r"t\s*\d+",
        r"tl\.?\s*\d+",
    ],
    StockShape.TUBE: [
        r"trubka",
        r"tube",
        r"roura?",
    ],
    StockShape.CASTING: [r"odlitek", r"casting"],
    StockShape.FORGING: [r"výkovek", r"forging"],
}

MATERIAL_CODE_PATTERNS = [
    r"1\.\d{4}",  # W.Nr
    r"S\d{3}",  # EN standards
    r"C\d{2,3}",  # Carbon steel
    r"\d{5}",  # ČSN
    r"[67]\d{3}",  # Aluminum
]

# Surface treatment codes (from Infor Item suffix)
# Format: {W.Nr}-{SHAPE}{dimensions}-{SURFACE}
# Example: 1.0503-HR016x016-T
SURFACE_TREATMENT_CODES = {
    'T': 'Tažená (cold drawn)',
    'V': 'Válená (hot rolled)',
    'P': 'Lisovaná (pressed)',
    'O': 'Loupaná (peeled)',
    'F': 'Frézovaná (milled)',
    'K': 'Kovaná (forged)',
    'L': 'Litá (cast)',
    'H': 'Kalená (hardened)',
    'N': 'Normalizovaná (normalized)',
    'Z': 'Pozinkovaná (galvanized)',
    'S': 'Svařovaná (welded)',
    'Sv': 'Svařovaná (welded)',
    'Vs': 'Válcovaná za studena (cold rolled)',
    'B': 'Broušená (ground)',
    'BLOK': 'Blok (block)',
    'EP': 'Elox Plus (anodized)',
}


class MaterialImporter(InforImporterBase[MaterialItem]):
    """Importer for MaterialItem from Infor SLItems"""

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings for MaterialItem"""
        return InforImporterConfig(
            entity_name="MaterialItem",
            ido_name="SLItems",
            field_mappings=[
                # Required fields
                FieldMapping("Item", "code", required=True),
                FieldMapping("Description", "name", required=True),
                # Optional catalog fields
                FieldMapping("Diameter", "diameter"),
                FieldMapping("Width", "width"),
                FieldMapping("Thickness", "thickness"),
                FieldMapping("WallThickness", "wall_thickness", fallback_fields=["WallThick"]),
                FieldMapping("WeightPerMeter", "weight_per_meter", fallback_fields=["Weight"]),
                FieldMapping("StandardLength", "standard_length", fallback_fields=["Length"]),
                FieldMapping("Norms", "norms"),
                FieldMapping("SupplierCode", "supplier_code", fallback_fields=["SuppCode"]),
                FieldMapping("Supplier", "supplier"),
                FieldMapping("StockAvailable", "stock_available", fallback_fields=["Stock", "QtyOnHand"]),
            ],
            duplicate_check_field="code"
        )

    def parse_shape_from_item_code(self, item_code: str, dims: Dict[str, Optional[float]]) -> Optional[StockShape]:
        """Parse shape from Item code (MASTER source)

        Shape codes in Item:
        - KR = ROUND_BAR (kulatina)
        - HR = SQUARE_BAR or FLAT_BAR (based on dimensions)
        - OK = HEXAGONAL_BAR (šestihran)
        - DE = PLATE (deska/plech)
        - TR = TUBE (trubka)
        """
        if not item_code:
            return None

        item_upper = item_code.upper()

        # Extract shape code from Item
        match = re.search(r'-([A-Z]{2})\d', item_upper)
        if not match:
            return None

        shape_code = match.group(1)

        shape_map = {
            'KR': StockShape.ROUND_BAR,
            'OK': StockShape.HEXAGONAL_BAR,
            'DE': StockShape.PLATE,
            'TR': StockShape.TUBE,
        }

        if shape_code in shape_map:
            shape = shape_map[shape_code]
            logger.debug(f"Shape from Item code: {shape} (code={shape_code}) from '{item_code}'")
            return shape

        # HR: Square or Flat bar - determine by dimensions
        if shape_code == 'HR':
            width = dims.get("width")
            thickness = dims.get("thickness")
            if width and thickness and width == thickness:
                logger.debug(f"Shape from Item code: SQUARE_BAR (HR, {width}x{thickness}) from '{item_code}'")
                return StockShape.SQUARE_BAR
            else:
                logger.debug(f"Shape from Item code: FLAT_BAR (HR, {width}x{thickness}) from '{item_code}'")
                return StockShape.FLAT_BAR

        return None

    def parse_shape_from_text(self, text: str) -> Optional[StockShape]:
        """Parse shape from Description using regex patterns (FALLBACK)"""
        if not text:
            return None

        text_lower = text.lower()
        for shape, patterns in SHAPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    logger.debug(f"Shape detected from Description: {shape} from '{text}'")
                    return shape
        return None

    def extract_material_code(self, text: str) -> Optional[str]:
        """Extract material code from Description"""
        if not text:
            return None

        for pattern in MATERIAL_CODE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                code = match.group(0)
                logger.debug(f"Material code detected: {code} from '{text}'")
                return code
        return None

    def extract_w_nr_from_item_code(self, item_code: str) -> Optional[str]:
        """Extract W.Nr from Infor Item code (MASTER source for material code)

        Format: {W.Nr}-{SHAPE}{dimensions}-{SURFACE}
        Example: 1.0503-HR016x016-T → "1.0503"

        W.Nr patterns:
        - 1.xxxx = Steel (konstrukční, automatová, nástrojová, legovaná)
        - 2.xxxx = Copper, Brass
        - 3.xxxx = Aluminum

        Returns W.Nr code or None if not found.
        """
        if not item_code:
            return None

        # Pattern: W.Nr at the beginning before first dash
        # Match 1.xxxx, 2.xxxx, 3.xxxx, etc. (4 digits after dot)
        match = re.match(r'^([1-3]\.\d{4})', item_code)
        if match:
            w_nr = match.group(1)
            logger.debug(f"W.Nr detected from Item code: {w_nr} from '{item_code}'")
            return w_nr

        return None

    def extract_surface_treatment(self, item_code: str) -> Optional[str]:
        """Extract surface treatment from Infor Item code

        Formats:
        - 1.0503-HR016x016-T → "T" (at end)
        - 1.0503-KR020.000-B-h6 → "B" (in middle, before tolerance)
        - 1.0503-KR016.000-f7-B → "B" (at end, after tolerance)

        Returns surface treatment code (T, V, P, O, F, B, etc.)
        """
        if not item_code:
            return None

        item_upper = item_code.upper()

        # Strategy: Look for known surface treatment codes anywhere in the item code
        # They appear as standalone segments between dashes: -T-, -B-, -V- or -T$, -B$
        # Ignore shape codes (KR, HR, DE, TR, OK) and tolerance codes (h6, f7, etc.)

        # First try: exact match for known codes (longer codes first to avoid partial matches)
        sorted_codes = sorted(SURFACE_TREATMENT_CODES.keys(), key=len, reverse=True)
        for code in sorted_codes:
            # Match -CODE- (middle) or -CODE$ (end) or -CODE. (before dot)
            pattern = rf'-{re.escape(code)}(?:-|\.|$)'
            if re.search(pattern, item_upper):
                logger.debug(f"Surface treatment detected: {code} from '{item_code}'")
                return code

        # Fallback: try to find any 1-2 letter code at the end that's not a shape code
        shape_codes = {'KR', 'HR', 'DE', 'TR', 'OK'}
        match = re.search(r'-([A-Z]{1,2})$', item_upper)
        if match:
            surface_code = match.group(1)
            if surface_code not in shape_codes:
                logger.debug(f"Surface treatment detected (fallback): {surface_code} from '{item_code}'")
                return surface_code

        return None

    def parse_dimensions_from_item_code(self, item_code: str) -> Dict[str, Optional[float]]:
        """Parse dimensions from Infor Item code (MASTER source)

        Formats:
        - 1.0503-HR010x010-T → width=10, thickness=10 (square bar, 'x' separator)
        - 1.0503-HR010x003-T → width=10, thickness=3 (flat bar, 'x' separator)
        - 1.0503-KR016-V → diameter=16 (round bar)
        - 3.3547-DE010-042-F → thickness=10, width=42 (plate strip, dash separator)
        - 3.3547-DE010-038-066-L → thickness=10, width=38, length=66 (plate cut, dash separator)
        - 1.0503-TR025x002-V → diameter=25, wall_thickness=2 (tube)
        - 1.0503-OK017-T → width=17 (hexagonal bar, SW = across flats)
        """
        dims = {
            "diameter": None,
            "width": None,
            "thickness": None,
            "wall_thickness": None,
            "standard_length": None,
        }

        if not item_code:
            return dims

        item_upper = item_code.upper()

        # Pattern 1: DE with dash-separated dimensions
        # Format: {W.Nr}-DE{thickness}-{width}-{SURF} or {W.Nr}-DE{thickness}-{width}-{length}-{SURF}
        de_match = re.search(r'-DE(\d+)-(\d+)(?:-(\d+))?(?:-[A-Z]+)?$', item_upper)
        if de_match:
            dims["thickness"] = float(de_match.group(1))
            dims["width"] = float(de_match.group(2))
            if de_match.group(3):
                dims["standard_length"] = float(de_match.group(3))
            logger.debug(f"DE dimensions parsed: thickness={dims['thickness']}, width={dims['width']}, length={dims['standard_length']} from '{item_code}'")
            return dims

        # Pattern 2a: Rectangular tube with 3 dimensions (width x height x wall)
        # Format: {W.Nr}-TR{width}x{height}x{wall}-{SURF}
        # Example: 1.0039-TR080x040x02-Sv → width=80, thickness=40 (height), wall_thickness=2
        rect_tube_match = re.search(r'-TR(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?[xX]+(\d+)', item_upper)
        if rect_tube_match:
            dims["width"] = float(rect_tube_match.group(1))
            dims["thickness"] = float(rect_tube_match.group(2))  # height stored as thickness
            dims["wall_thickness"] = float(rect_tube_match.group(3))
            logger.debug(f"TR rectangular dimensions parsed: width={dims['width']}, height={dims['thickness']}, wall={dims['wall_thickness']} from '{item_code}'")
            return dims

        # Pattern 2b: HR/TR with 'x' separator (2 dimensions, with optional .000 suffix)
        # Format: {W.Nr}-HR{width}x{thickness}-{SURF} or {W.Nr}-TR{diameter}x{wall}-{SURF}
        x_match = re.search(r'-([A-Z]{2})(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?(?:-|$)', item_upper)
        if x_match:
            shape_code = x_match.group(1)
            dim1 = int(x_match.group(2))
            dim2 = int(x_match.group(3))

            if shape_code == 'HR':  # Square or flat bar
                dims["width"] = float(dim1)
                if dim1 == dim2:
                    # Square bar: 010x010 → width=10, thickness=10
                    dims["thickness"] = float(dim1)
                else:
                    # Flat bar: 010x003 → width=10, thickness=3
                    dims["thickness"] = float(dim2)
            elif shape_code == 'TR':  # Round tube
                dims["diameter"] = float(dim1)
                dims["wall_thickness"] = float(dim2)

            logger.debug(f"{shape_code} dimensions parsed: {dims} from '{item_code}'")
            return dims

        # Pattern 3: Single dimension (KR, OK, DE simple, HR simple)
        # Format: {W.Nr}-{SHAPE}{dimension}-{SURF}
        single_match = re.search(r'-([A-Z]{2})(\d+)-?', item_upper)
        if single_match:
            shape_code = single_match.group(1)
            dim = int(single_match.group(2))

            if shape_code == 'KR':  # Round bar
                dims["diameter"] = float(dim)
            elif shape_code == 'OK':  # Hexagonal bar - SW (across flats)
                dims["width"] = float(dim)  # SW = Schlüsselweite (across flats)
            elif shape_code == 'DE':  # Plate (thickness only)
                dims["thickness"] = float(dim)
            elif shape_code == 'HR':  # Square bar (single dimension)
                dims["width"] = float(dim)

            logger.debug(f"{shape_code} single dimension parsed: {dims} from '{item_code}'")

        return dims

    def parse_dimensions(self, description: str, shape: Optional[StockShape]) -> Dict[str, Optional[float]]:
        """Parse dimensions from Description field (FALLBACK)"""
        dims = {
            "diameter": None,
            "width": None,
            "thickness": None,
            "wall_thickness": None,
        }

        if not description:
            return dims

        # Diameter: D20, Ø20
        diameter_match = re.search(r"[DØ]\s*(\d+(?:\.\d+)?)", description, re.IGNORECASE)
        if diameter_match:
            dims["diameter"] = float(diameter_match.group(1))

        # Thickness: t5, tl.5
        thickness_match = re.search(r"t(?:l\.?)?\s*(\d+(?:\.\d+)?)", description, re.IGNORECASE)
        if thickness_match:
            dims["thickness"] = float(thickness_match.group(1))

        # Tube: D25x2
        tube_match = re.search(r"[DØ]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)", description)
        if tube_match:
            dims["diameter"] = float(tube_match.group(1))
            dims["wall_thickness"] = float(tube_match.group(2))

        # Width x Height: 20x30
        dimensions_match = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)", description)
        if dimensions_match and shape in [StockShape.SQUARE_BAR, StockShape.FLAT_BAR]:
            dims["width"] = float(dimensions_match.group(1))
            if shape == StockShape.FLAT_BAR:
                dims["thickness"] = float(dimensions_match.group(2))

        return dims

    async def detect_material_group(
        self, material_code: Optional[str], db: AsyncSession
    ) -> Optional[int]:
        """Detect MaterialGroup from material code with fallback pattern matching"""
        if not material_code:
            return None

        # 1. Try exact match first (fastest)
        result = await db.execute(
            select(MaterialNorm)
            .where(
                (MaterialNorm.w_nr == material_code)
                | (MaterialNorm.en_iso == material_code)
                | (MaterialNorm.csn == material_code)
                | (MaterialNorm.aisi == material_code)
            )
            .limit(1)
        )
        norm = result.scalar_one_or_none()

        if norm:
            logger.info(f"MaterialGroup found (exact): {norm.material_group_id} for code '{material_code}'")
            return norm.material_group_id

        # 2. Fallback: Pattern matching for W.Nr prefix
        # 1.0xxx → Ocel konstrukční, 1.4xxx → Nerez, 3.xxxx → Hliník, etc.
        if re.match(r'^\d\.\d{4}$', material_code):
            prefix = material_code[:3]  # "1.0", "1.4", "3.3", etc.

            # Try prefix match (e.g., "1.0036" → find any "1.0xxx")
            result = await db.execute(
                select(MaterialNorm)
                .where(MaterialNorm.w_nr.like(f'{prefix}%'))
                .limit(1)
            )
            norm = result.scalar_one_or_none()

            if norm:
                logger.info(f"MaterialGroup found (pattern): {norm.material_group_id} for code '{material_code}' (matched prefix {prefix})")
                return norm.material_group_id

        logger.warning(f"No MaterialGroup found for material code '{material_code}' (tried exact + pattern)")
        return None

    async def detect_price_category(
        self, material_group_id: Optional[int], shape: Optional[StockShape], db: AsyncSession
    ) -> Optional[int]:
        """Detect PriceCategory from MaterialGroup + shape"""
        if not material_group_id or not shape:
            return None

        result = await db.execute(
            select(MaterialPriceCategory).where(
                MaterialPriceCategory.material_group_id == material_group_id
            )
        )
        categories = result.scalars().all()

        if not categories:
            return None

        # Try to match shape from category name/code
        shape_keywords = {
            StockShape.ROUND_BAR: ["kruhov", "round", "kulatina"],
            StockShape.SQUARE_BAR: ["čtvercov", "square"],
            StockShape.FLAT_BAR: ["ploch", "flat"],
            StockShape.HEXAGONAL_BAR: ["šestihr", "hex"],
            StockShape.PLATE: ["plech", "plate"],
            StockShape.TUBE: ["trubka", "tube"],
        }

        keywords = shape_keywords.get(shape, [])
        for category in categories:
            name_lower = (category.name or "").lower()
            code_lower = (category.code or "").lower()
            for keyword in keywords:
                if keyword in name_lower or keyword in code_lower:
                    logger.info(f"PriceCategory found: {category.id} for group {material_group_id} + shape {shape}")
                    return category.id

        # Fallback: return first category
        return categories[0].id

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Custom mapping for MaterialItem (shape, dimensions, group, category, surface treatment)"""
        custom = {}

        item_code = row.get("Item", "")
        description = row.get("Description", "")

        # Parse dimensions (prioritize Item code as MASTER)
        # 1. Try from Item code (MASTER) - e.g., "1.0503-HR010x010-T" → width=10, thickness=10
        dims = self.parse_dimensions_from_item_code(item_code)

        # Parse shape (prioritize Item code as MASTER)
        # 1. Try from Item code (MASTER) - e.g., "1.0503-OK017-T" → HEXAGONAL_BAR
        shape = self.parse_shape_from_item_code(item_code, dims)

        # 2. Fallback: Try from Description if not found in Item code
        if not shape:
            shape = self.parse_shape_from_text(description)
            if shape:
                logger.info(f"Using fallback shape from Description: {shape}")

        custom["shape"] = shape

        # 3. Fallback dimensions from Description if not found in Item code
        if all(v is None for v in dims.values()):
            dims = self.parse_dimensions(description, shape)
            logger.info(f"Using fallback dimensions from Description: {dims}")

        custom.update(dims)

        # Extract material code (prioritize Item code as MASTER source)
        # 1. Try W.Nr from Item code (MASTER) - e.g., "1.0503-HR016x016-T" → "1.0503"
        material_code = self.extract_w_nr_from_item_code(item_code)

        # 2. Fallback: Try any material code from Description (ČSN, EN, etc.)
        if not material_code:
            material_code = self.extract_material_code(description)
            logger.info(f"Using fallback material code from Description: {material_code}")

        # Detect MaterialGroup from material code
        material_group_id = await self.detect_material_group(material_code, db)
        custom["material_group_id"] = material_group_id

        # Detect PriceCategory from MaterialGroup + shape
        price_category_id = await self.detect_price_category(material_group_id, shape, db)
        custom["price_category_id"] = price_category_id

        # Extract surface treatment from Item code (e.g., "1.0503-HR016x016-T" → "T")
        surface_treatment = self.extract_surface_treatment(item_code)
        custom["surface_treatment"] = surface_treatment

        # material_number will be generated in create_entity
        custom["material_number"] = None

        return custom

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> MaterialItem:
        """Create MaterialItem instance"""
        # Generate material_number
        material_numbers = await NumberGenerator.generate_material_numbers_batch(db, 1)
        material_number = material_numbers[0]

        return MaterialItem(
            material_number=material_number,
            code=mapped_data["code"],
            name=mapped_data["name"],
            shape=mapped_data.get("shape"),
            diameter=mapped_data.get("diameter"),
            width=mapped_data.get("width"),
            thickness=mapped_data.get("thickness"),
            wall_thickness=mapped_data.get("wall_thickness"),
            weight_per_meter=mapped_data.get("weight_per_meter"),
            standard_length=mapped_data.get("standard_length"),
            norms=mapped_data.get("norms"),
            supplier_code=mapped_data.get("supplier_code"),
            supplier=mapped_data.get("supplier"),
            stock_available=mapped_data.get("stock_available", 0.0),
            material_group_id=mapped_data.get("material_group_id"),
            price_category_id=mapped_data.get("price_category_id"),
            surface_treatment=mapped_data.get("surface_treatment")
        )

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[MaterialItem]:
        """Check if MaterialItem with same code exists"""
        code = mapped_data.get("code")
        if not code:
            return None

        result = await db.execute(
            select(MaterialItem).where(MaterialItem.code == code)
        )
        return result.scalar_one_or_none()

    async def update_entity(
        self,
        existing: MaterialItem,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """Update existing MaterialItem (only catalog fields)"""
        existing.supplier_code = mapped_data.get("supplier_code")
        existing.supplier = mapped_data.get("supplier")
        existing.stock_available = mapped_data.get("stock_available", 0.0)
        logger.info(f"Updated catalog fields for MaterialItem: {existing.code}")

    async def validate_mapped_row(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> ValidationResult:
        """Validate MaterialItem mapped data (with entity-specific rules)"""
        # Call base validation first
        result = await super().validate_mapped_row(mapped_data, db)

        # MaterialItem-specific validations

        # Shape validation
        if not mapped_data.get("shape"):
            result.errors.append("Shape not detected - manual selection required")
            result.is_valid = False
            result.needs_manual_input["shape"] = True

        # MaterialGroup validation
        if not mapped_data.get("material_group_id"):
            result.errors.append("MaterialGroup not detected - manual selection required")
            result.is_valid = False
            result.needs_manual_input["material_group_id"] = True

        # PriceCategory validation
        if not mapped_data.get("price_category_id"):
            result.warnings.append("PriceCategory not detected")
            result.needs_manual_input["price_category_id"] = True

        # Dimension validation
        for dim in ["diameter", "width", "thickness", "wall_thickness"]:
            value = mapped_data.get(dim)
            if value is not None:
                try:
                    if float(value) < 0:
                        result.errors.append(f"Invalid {dim}: must be >= 0")
                        result.is_valid = False
                except (ValueError, TypeError):
                    result.errors.append(f"Invalid {dim}: not a number")
                    result.is_valid = False

        return result
