"""GESTIMA - Material Parser Service (Fáze 1: Regex-based parsing)

Parsuje materiálové popisy typu "D20 1.4301 100mm" a rozpozná:
- Tvar polotovaru (kulatina, čtyřhran, profil, plech, trubka)
- Rozměry (průměr, šířka, výška, tloušťka)
- Materiálovou normu (1.4301, C45, S235, EN AW-6060, atd.)
- Délku polotovaru

Výstup: ParseResult s confidence score + navržený MaterialGroup/PriceCategory/MaterialItem
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.enums import StockShape
from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialItem
from app.models.material_norm import MaterialNorm

logger = logging.getLogger(__name__)


class ParseResult(BaseModel):
    """Výsledek parsingu materiálového popisu"""

    # Raw input
    raw_input: str

    # Rozpoznané parametry
    shape: Optional[StockShape] = None
    diameter: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    thickness: Optional[float] = Field(None, ge=0)
    wall_thickness: Optional[float] = Field(None, ge=0)  # Pro trubky
    length: Optional[float] = Field(None, ge=0)

    # Materiál
    material_norm: Optional[str] = None  # "1.4301", "C45", "S235"
    material_category: Optional[str] = None  # "ocel", "nerez", "hlinik"

    # Navržené entity (pokud nalezeny v DB)
    suggested_material_group_id: Optional[int] = None
    suggested_material_group_code: Optional[str] = None
    suggested_material_group_name: Optional[str] = None
    suggested_material_group_density: Optional[float] = None

    suggested_price_category_id: Optional[int] = None
    suggested_price_category_code: Optional[str] = None
    suggested_price_category_name: Optional[str] = None

    suggested_material_item_id: Optional[int] = None
    suggested_material_item_code: Optional[str] = None
    suggested_material_item_name: Optional[str] = None

    # Meta
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_pattern: str  # Pro debugging
    warnings: List[str] = Field(default_factory=list)  # Chybové hlášky pro uživatele


class MaterialParserService:
    """
    Regex-based parser pro materiálové popisy.

    Podporované formáty:
    - D20 1.4301 100mm           (kulatina průměr 20, nerez, délka 100)
    - Ø20 1.4301 L=100           (alternativní zápis)
    - 20x20 C45 500              (čtyřhran 20x20, ocel C45, délka 500)
    - 20x30 S235 500             (profil 20x30, ocel, délka 500)
    - t2 1.4301 1000x2000        (plech tloušťka 2mm, nerez)
    - D20x2 1.4301 100           (trubka průměr 20, tloušťka stěny 2)
    - ⬡24 CuZn37 150             (šestihran 24mm, mosaz)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== REGEX PATTERNS ==========

    # Pattern definitions (pořadí důležité - specifické první!)
    PATTERNS = [
        # 1. TRUBKA: D20x2 nebo Ø20x2 (průměr x tloušťka stěny)
        {
            "name": "tube",
            "regex": r"[DdØø]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)",
            "shape": StockShape.TUBE,
            "extract": lambda m: {
                "diameter": float(m.group(1)),
                "wall_thickness": float(m.group(2))
            }
        },

        # 2. KULATINA: D20 nebo Ø20
        {
            "name": "round_bar",
            "regex": r"[DdØø]\s*(\d+(?:\.\d+)?)",
            "shape": StockShape.ROUND_BAR,
            "extract": lambda m: {"diameter": float(m.group(1))}
        },

        # 3. ČTYŘHRAN: □30 (speciální znak)
        {
            "name": "square_bar_symbol",
            "regex": r"[□▪■]\s*(\d+(?:\.\d+)?)",
            "shape": StockShape.SQUARE_BAR,
            "extract": lambda m: {
                "width": float(m.group(1)),
                "height": float(m.group(1))
            }
        },

        # 4. ŠESTIHRAN: ⬡24 (speciální znak)
        {
            "name": "hexagonal_bar",
            "regex": r"⬡\s*(\d+(?:\.\d+)?)",
            "shape": StockShape.HEXAGONAL_BAR,
            "extract": lambda m: {"width": float(m.group(1))}
        },

        # 5. ČTYŘHRAN nebo PROFIL: 20x20 (stejné číslo) nebo 20x30 (různé)
        # MUSÍ být AŽ za trubkou (jinak by D20x2 matchlo jako profil!)
        {
            "name": "square_or_flat_bar",
            "regex": r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)",
            "shape": None,  # Určí se podle hodnot
            "extract": lambda m: {
                "width": float(m.group(1)),
                "height": float(m.group(2))
            }
        },

        # 6. PLECH: t2 nebo tl.2 nebo thickness=2
        {
            "name": "plate",
            "regex": r"(?:t|tl\.?|thickness[=:]?)\s*(\d+(?:\.\d+)?)",
            "shape": StockShape.PLATE,
            "extract": lambda m: {"thickness": float(m.group(1))}
        },
    ]

    # Normy materiálů (pattern → kategorie)
    # DŮLEŽITÉ: Použít \b word boundaries aby se zabránilo partial match!
    # Např. bez \b by "[67]\d{3}" matchlo "7240" uvnitř "17240" (ČSN nerez)
    MATERIAL_CATEGORY_PATTERNS = {
        # Nerez (1.4xxx) - tečka funguje jako přirozený boundary
        r"1\.4\d{3}": "nerez",

        # Ocel (1.0xxx - 1.2xxx) - tečka funguje jako přirozený boundary
        r"1\.[0-2]\d{3}": "ocel",

        # Ocel (Sxxx - S235, S355) - \b pro standalone match
        r"\bS\d{3}\b": "ocel",

        # Ocel (Cxx - C45, C15, C60) - \b pro standalone match
        r"\bC\d{2,3}\b": "ocel",

        # Ocel (42CrMo4, 16MnCr5, 34CrNiMo6) - složený pattern, safe
        r"\d{2}[A-Z][a-z]+\d{1,2}": "ocel",

        # Hliník (EN AW-xxxx) - specifický formát, safe
        r"EN\s*AW[- ]?\d{4}": "hlinik",

        # Hliník (6xxx, 7xxx série) - KRITICKÉ: \b aby nematchlo uvnitř 17240!
        r"\b[67]\d{3}\b": "hlinik",

        # Mosaz (CuZnxx) - písmena na začátku, safe
        r"CuZn\d{2}": "mosaz",

        # Mosaz (CuZnxxxPbx)
        r"CuZn\d{2}Pb\d": "mosaz",

        # Bronz (CuSnxx)
        r"CuSn\d{1,2}": "bronz",

        # Plasty (PA6, POM, PEEK) - písmena na začátku, safe
        r"\bPA\d{1,2}\b": "plast",
        r"\bPOM(-[CH])?\b": "plast",
        r"\bPEEK\b": "plast",
    }

    # Délka: "100mm", "L=100", "length=100", "100"
    LENGTH_REGEX = r"(?:L[=:]?\s*|length[=:]?\s*)?(\d+(?:\.\d+)?)\s*(?:mm)?"

    # ========== MAIN PARSING METHOD ==========

    async def parse(self, description: str) -> ParseResult:
        """
        Hlavní parsing funkce.

        Args:
            description: User input (např. "D20 1.4301 100mm")

        Returns:
            ParseResult s rozpoznanými parametry a confidence score
        """
        result = ParseResult(
            raw_input=description,
            confidence=0.0,
            matched_pattern="none"
        )

        # Normalize input (trim whitespace)
        normalized = description.strip()

        # 1. Detect shape + dimensions
        shape_match = self._extract_shape(normalized)
        if shape_match:
            result.shape = shape_match["shape"]
            result.diameter = shape_match.get("diameter")
            result.width = shape_match.get("width")
            result.height = shape_match.get("height")
            result.thickness = shape_match.get("thickness")
            result.wall_thickness = shape_match.get("wall_thickness")
            result.matched_pattern = shape_match["pattern"]
            result.confidence += 0.4

        # 2. Detect material norm
        material_match = await self._extract_material(normalized)
        if material_match:
            result.material_norm = material_match["norm"]
            result.material_category = material_match["category"]
            result.confidence += 0.3

            # 2a. Find MaterialGroup v DB (via MaterialNorm)
            group = await self._find_material_group(material_match["norm"])
            if group:
                # Also fetch the MaterialNorm to get W.Nr.
                material_norm_result = await self.db.execute(
                    select(MaterialNorm)
                    .where(
                        MaterialNorm.material_group_id == group.id,
                        or_(
                            MaterialNorm.w_nr == material_match["norm"].upper(),
                            MaterialNorm.en_iso == material_match["norm"].upper(),
                            MaterialNorm.csn == material_match["norm"].upper(),
                            MaterialNorm.aisi == material_match["norm"].upper()
                        ),
                        MaterialNorm.deleted_at.is_(None)
                    )
                    .limit(1)
                )
                material_norm = material_norm_result.scalar_one_or_none()

                # Use W.Nr. from database if found, otherwise keep raw input
                if material_norm and material_norm.w_nr:
                    result.material_norm = material_norm.w_nr

                result.suggested_material_group_id = group.id
                result.suggested_material_group_code = group.code
                result.suggested_material_group_name = group.name
                result.suggested_material_group_density = group.density
                result.confidence += 0.1

        # 3. Detect length (po shape a material, aby jsme mohli odfiltrovat matchnuté části)
        length_match = self._extract_length(
            normalized,
            shape_pattern=shape_match.get("pattern") if shape_match else None,
            material_norm=result.material_norm
        )
        if length_match:
            result.length = length_match
            result.confidence += 0.1

        # 4. Find PriceCategory (pokud máme shape + material group)
        if result.shape and result.suggested_material_group_id:
            price_cat = await self._find_price_category(
                material_group_id=result.suggested_material_group_id,
                shape=result.shape
            )
            if price_cat:
                result.suggested_price_category_id = price_cat.id
                result.suggested_price_category_code = price_cat.code
                result.suggested_price_category_name = price_cat.name
                result.confidence += 0.05
            else:
                # WARNING: Nenalezena cenová kategorie pro tento materiál + tvar
                shape_label = {
                    StockShape.ROUND_BAR: "tyč kruhová",
                    StockShape.SQUARE_BAR: "tyč čtvercová",
                    StockShape.FLAT_BAR: "tyč plochá",
                    StockShape.HEXAGONAL_BAR: "tyč šestihranná",
                    StockShape.PLATE: "plech/deska",
                    StockShape.TUBE: "trubka",
                    StockShape.CASTING: "odlitek",
                    StockShape.FORGING: "výkovek"
                }.get(result.shape, str(result.shape))
                result.warnings.append(
                    f"Nenalezena cenová kategorie pro {result.suggested_material_group_name} + {shape_label}"
                )

        # 5. Find MaterialItem (pokud máme group + shape + rozměry)
        if result.suggested_material_group_id and result.shape:
            item = await self._find_material_item(
                material_group_id=result.suggested_material_group_id,
                shape=result.shape,
                diameter=result.diameter,
                width=result.width,
                height=result.height,
                thickness=result.thickness,
                wall_thickness=result.wall_thickness
            )
            if item:
                result.suggested_material_item_id = item.id
                result.suggested_material_item_code = item.code
                result.suggested_material_item_name = item.name
                result.confidence += 0.05

        return result

    # ========== HELPER METHODS ==========

    def _extract_shape(self, text: str) -> Optional[Dict[str, Any]]:
        """Rozpozná tvar a rozměry pomocí regex patterns"""
        for pattern_def in self.PATTERNS:
            match = re.search(pattern_def["regex"], text, re.IGNORECASE)
            if match:
                extracted = pattern_def["extract"](match)
                shape = pattern_def["shape"]

                # Speciální případ: 20x30 může být čtyřhran nebo profil
                if pattern_def["name"] == "square_or_flat_bar":
                    width = extracted["width"]
                    height = extracted["height"]
                    if width == height:
                        shape = StockShape.SQUARE_BAR
                    else:
                        shape = StockShape.FLAT_BAR

                return {
                    "shape": shape,
                    "pattern": pattern_def["name"],
                    **extracted
                }
        return None

    async def _extract_material(self, text: str) -> Optional[Dict[str, str]]:
        """
        Rozpozná materiálovou normu - VYLEPŠENÁ verze s DB lookup.

        Strategy:
        1. Zkus hardcoded regex patterns (nejběžnější normy)
        2. Pokud nic → Extrahuj všechny potenciální kódy a validuj přes DB
        3. Fallback na "unknown" kategorii
        """
        # 1. Try hardcoded patterns first (fastest for common cases)
        for norm_pattern, category in self.MATERIAL_CATEGORY_PATTERNS.items():
            match = re.search(norm_pattern, text, re.IGNORECASE)
            if match:
                return {
                    "norm": match.group(0).upper(),
                    "category": category
                }

        # 2. FALLBACK: Extract potential material codes and validate via DB
        # Patterns for material codes:
        # - W.Nr: 1.4301, 1.0503 (1.xxxx)
        # - EN/AISI: 6082, 304, C45, S235 (letters + numbers, 2-6 chars)
        # - ČSN: 11109, 12050 (5-digit numbers)

        potential_codes = []

        # Find all potential material codes:
        # - Pure digits: 4-6 chars (např. 6082, 1045, 11109) - filtruje 20, 100
        # - Mixed: letter(s) + digits 2-6 total (např. C45, S235, X5CrNi18-10)
        # - NOT: D20, Ø20 (shape dimensions), 100 (too short, délka)

        # Pattern 1: Pure digits 4-6 chars (6082, 11109)
        for match in re.finditer(r"\b(\d{4,6})\b", text):
            code = match.group(1)
            potential_codes.append(code)

        # Pattern 2: Mixed alphanumeric (C45, S235, X5CrNi18-10)
        for match in re.finditer(r"\b([A-Z]+\d+[A-Z\d]*)\b", text, re.IGNORECASE):
            code = match.group(1).upper()
            # Filter out shape dimensions (D20, Ø20)
            if not code.startswith('D') and not code.startswith('Ø') and not code.startswith('O'):
                potential_codes.append(code)

        logger.debug(f"_extract_material: potential codes found: {potential_codes}")

        # Try to find these codes in MaterialNorm DB
        for code in potential_codes:
            result = await self.db.execute(
                select(MaterialNorm)
                .where(
                    or_(
                        MaterialNorm.w_nr == code,
                        MaterialNorm.en_iso == code,
                        MaterialNorm.csn == code,
                        MaterialNorm.aisi == code
                    )
                )
                .limit(1)
            )
            norm = result.scalar_one_or_none()

            if norm:
                logger.debug(f"_extract_material: DB match found for '{code}' → MaterialNorm ID {norm.id}")
                # Return with category from MaterialGroup
                # (category is not needed anymore, _find_material_group will handle it)
                return {
                    "norm": code,
                    "category": "unknown"  # Will be resolved via _find_material_group
                }

        logger.debug(f"_extract_material: no material code found")
        return None

    def _extract_length(
        self,
        text: str,
        shape_pattern: Optional[str] = None,
        material_norm: Optional[str] = None
    ) -> Optional[float]:
        """
        Rozpozná délku (mm).

        Strategy:
        1. Odstranit matchnuté shape + material části z textu
        2. Pokud materiál NEBYL rozpoznán, odfiltrovat potenciální materiálové kódy (4-6 číslic)
        3. Vzít POSLEDNÍ číslo jako délku (délka je vždy na konci inputu)

        Args:
            text: Original input text
            shape_pattern: Matched shape pattern name (e.g. "round_bar", "square_or_flat_bar")
            material_norm: Matched material norm (e.g. "C45", "S235", "1.4301")

        Returns:
            Length in mm or None
        """
        # Create a cleaned version of text by removing matched patterns
        cleaned_text = text

        # Remove shape patterns
        if shape_pattern:
            # Remove based on pattern type
            for pattern_def in self.PATTERNS:
                if pattern_def["name"] == shape_pattern:
                    # Remove the matched shape part
                    cleaned_text = re.sub(pattern_def["regex"], " ", cleaned_text, flags=re.IGNORECASE)
                    break

        # Remove material norm
        if material_norm:
            # Remove the exact material norm string
            cleaned_text = re.sub(re.escape(material_norm), " ", cleaned_text, flags=re.IGNORECASE)

        # Debug log
        logger.debug(f"_extract_length: original='{text}', cleaned='{cleaned_text}'")

        # Find all numbers in cleaned text
        # Note: Don't use \b at end - "100mm" has no word boundary between "100" and "mm"
        all_numbers = list(re.finditer(r"(?<!\d)(\d+(?:\.\d+)?)", cleaned_text))
        logger.debug(f"_extract_length: found numbers: {[m.group(1) for m in all_numbers]}")

        if not all_numbers:
            return None

        # Filter out potential material codes if material was NOT recognized
        # Material codes are typically 4-6 digit pure numbers (ČSN codes like 11373, 12050, 17240)
        # Length is typically 2-4 digit number or < 10000 (max 10 meters)
        candidate_numbers = []

        for match in all_numbers:
            value = float(match.group(1))
            num_str = match.group(1).split('.')[0]  # Integer part
            num_digits = len(num_str)

            # Skip very small numbers (< 10mm is unlikely to be length)
            if value < 10.0:
                logger.debug(f"_extract_length: skipping {value} (too small for length)")
                continue

            # If material was NOT found, filter out potential material codes
            if material_norm is None:
                # 5-digit numbers are likely ČSN codes (11xxx, 12xxx, 17xxx)
                if num_digits == 5 and 10000 <= value < 100000:
                    logger.debug(f"_extract_length: skipping {value} (likely ČSN material code)")
                    continue

                # 4-digit numbers in 6xxx, 7xxx range are likely aluminum codes
                if num_digits == 4 and (6000 <= value < 8000):
                    logger.debug(f"_extract_length: skipping {value} (likely aluminum code)")
                    continue

            candidate_numbers.append(value)

        logger.debug(f"_extract_length: candidate lengths after filtering: {candidate_numbers}")

        # Take the LAST candidate (length is typically at the end of user input)
        if candidate_numbers:
            length = candidate_numbers[-1]
            logger.debug(f"_extract_length: returning length={length} (last candidate)")
            return length

        return None

    async def _find_material_group(self, norm: str) -> Optional[MaterialGroup]:
        """
        Najde MaterialGroup podle normy (hledá v MaterialNorm).

        Args:
            norm: Materiálová norma (např. "C45", "1.4301", "S235")

        Returns:
            MaterialGroup nebo None

        Strategy:
            1. Try exact match first (fastest, most specific)
            2. If not found, try prefix match (e.g. "S235" → "S235JR", "S235J2")
        """
        norm_upper = norm.upper()

        # 1. Try exact match first (hledá ve všech 4 sloupcích)
        result = await self.db.execute(
            select(MaterialNorm)
            .where(
                or_(
                    MaterialNorm.w_nr == norm_upper,
                    MaterialNorm.en_iso == norm_upper,
                    MaterialNorm.csn == norm_upper,
                    MaterialNorm.aisi == norm_upper
                ),
                MaterialNorm.deleted_at.is_(None)
            )
            .limit(1)
        )

        material_norm = result.scalar_one_or_none()

        # 2. If not found, try prefix match (for cases like S235 → S235JR)
        if not material_norm:
            result = await self.db.execute(
                select(MaterialNorm)
                .where(
                    or_(
                        MaterialNorm.w_nr.like(f'{norm_upper}%'),
                        MaterialNorm.en_iso.like(f'{norm_upper}%'),
                        MaterialNorm.csn.like(f'{norm_upper}%'),
                        MaterialNorm.aisi.like(f'{norm_upper}%')
                    ),
                    MaterialNorm.deleted_at.is_(None)
                )
                .limit(1)
            )

            material_norm = result.scalar_one_or_none()

        if not material_norm:
            return None

        # Načíst MaterialGroup
        result = await self.db.execute(
            select(MaterialGroup)
            .where(
                MaterialGroup.id == material_norm.material_group_id,
                MaterialGroup.deleted_at.is_(None)
            )
        )

        return result.scalar_one_or_none()

    async def _find_price_category(
        self,
        material_group_id: int,
        shape: StockShape
    ) -> Optional[MaterialPriceCategory]:
        """
        Najde MaterialPriceCategory podle MaterialGroup + Shape.

        Mapping keywords:
        - ROUND_BAR → "KRUHOVA" nebo "KULATINA"
        - SQUARE_BAR → "CTYRHRANNA", "ČTYŘHRAN", "CTVEREC", "ČTVEREC", "ČTVERCOVÁ"
        - FLAT_BAR → "PLOCHÁ" nebo "PLOCHA"
        - HEXAGONAL_BAR → "SESTIHRAN" nebo "ŠESTIHRAN"
        - PLATE → "PLECH"
        - TUBE → "TRUBKA"
        """
        shape_keywords = {
            StockShape.ROUND_BAR: ["KRUHOVA", "KULATINA"],
            StockShape.SQUARE_BAR: ["CTYRHRANNA", "ČTYŘHRAN", "CTVEREC", "ČTVEREC", "ČTVERCOVÁ"],
            StockShape.FLAT_BAR: ["PLOCHÁ", "PLOCHA"],
            StockShape.HEXAGONAL_BAR: ["SESTIHRAN", "ŠESTIHRAN"],
            StockShape.PLATE: ["PLECH"],
            StockShape.TUBE: ["TRUBKA"],
        }

        keywords = shape_keywords.get(shape, [])
        if not keywords:
            logger.debug(f"_find_price_category: No keywords for shape {shape}")
            return None

        # Query DB
        conditions = [
            MaterialPriceCategory.code.ilike(f"%{kw}%") for kw in keywords
        ]

        logger.debug(f"_find_price_category: Looking for material_group_id={material_group_id}, shape={shape}, keywords={keywords}")

        result = await self.db.execute(
            select(MaterialPriceCategory)
            .where(
                MaterialPriceCategory.material_group_id == material_group_id,
                or_(*conditions),
                MaterialPriceCategory.deleted_at.is_(None)
            )
            .limit(1)
        )

        category = result.scalar_one_or_none()
        if category:
            logger.debug(f"_find_price_category: Found category: {category.code} ({category.name})")
        else:
            logger.debug(f"_find_price_category: NO CATEGORY FOUND for material_group_id={material_group_id}, shape={shape}")

        return category

    async def _find_material_item(
        self,
        material_group_id: int,
        shape: StockShape,
        diameter: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        thickness: Optional[float] = None,
        wall_thickness: Optional[float] = None
    ) -> Optional[MaterialItem]:
        """
        Najde existující MaterialItem podle group + shape + rozměry.

        Exact match - všechny rozměry se musí shodovat.

        Note: MaterialItem model NEMÁ atribut 'height'.
        Pro flat_bar/square_bar:
          - Parser používá: width, height
          - MaterialItem má: width, thickness
          - Mapping: height → thickness (pro FLAT_BAR)
        """
        conditions = [
            MaterialItem.material_group_id == material_group_id,
            MaterialItem.shape == shape,
            MaterialItem.deleted_at.is_(None)
        ]

        # Přidat rozměrové podmínky (pouze nenulové hodnoty)
        if diameter is not None:
            conditions.append(MaterialItem.diameter == diameter)

        if width is not None:
            conditions.append(MaterialItem.width == width)

        # FLAT_BAR: height (z parseru) → thickness (v MaterialItem)
        # SQUARE_BAR: height se ignoruje (width == height)
        if shape == StockShape.FLAT_BAR and height is not None:
            conditions.append(MaterialItem.thickness == height)
        elif thickness is not None:
            # PLATE: thickness je tloušťka plechu
            conditions.append(MaterialItem.thickness == thickness)

        if wall_thickness is not None:
            conditions.append(MaterialItem.wall_thickness == wall_thickness)

        result = await self.db.execute(
            select(MaterialItem)
            .where(*conditions)
            .limit(1)
        )

        return result.scalar_one_or_none()
