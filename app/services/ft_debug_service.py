"""GESTIMA - FT Debug Service for fine-tuning data inspection.

Ports GT computation logic from scripts/generate_ft_v2_data.py to async SQLAlchemy.
Provides three main capabilities:
  1. list_eligible_parts — bulk GT computation + CV for all FT-eligible parts
  2. run_inference      — GPT-4.1 few-shot call + comparison with GT
  3. export_jsonl       — JSONL bytes ready for OpenAI fine-tuning upload
"""

import base64
import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file_record import FileRecord
from app.models.material import MaterialItem, MaterialPriceCategory
from app.models.material_input import MaterialInput
from app.models.material_norm import MaterialNorm
from app.models.part import Part
from app.models.production_record import ProductionRecord
from app.models.work_center import WorkCenter
from app.schemas.ft_debug import (
    FtInferenceComparison,
    FtInferenceResult,
    FtPartOperation,
    FtPartSummary,
    FtPartsResponse,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MAX_IMAGE_DIMENSION = 4096

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
# Must match scripts/generate_ft_v2_data.py — single source of truth for the
# system prompt used in both training-data generation and live inference.

SYSTEM_PROMPT = """Jsi CNC technolog. Analyzuj výrobní výkres a navrhni technologický postup.
Zakázková strojírenská výroba, malá firma. Časy jsou per kus v minutách.
Odpověz POUZE validním JSON.

MATERIÁL:
- Přečti materiál z rohového razítka výkresu přesně tak, jak je napsaný (W.Nr, ČSN, EN, AISI...).
- Urči materiálovou skupinu a ISO klasifikaci:
  * Ocel automatová (1.0715, 11SMnPb30) — ISO P, HB~180, nejlépe obrobitelná
  * Ocel konstrukční (1.0503, C45, 12050) — ISO P, HB~200
  * Nerez (1.4301, 1.4104, X5CrNi18-10) — ISO M, HB~220, hůře obrobitelná, delší časy
  * Ocel nástrojová (1.2842, 90MnCrV8) — ISO K, HB~300, tvrdá, pomalé řezné podmínky
  * Hliník (3.3547, AlMg4,5Mn) — ISO N, HB~80, rychlé obrábění
  * Plasty (POM-C, PA6) — ISO N, HB~30, velmi rychlé obrábění
- ISO M/K materiály = delší strojní časy než ISO P (pomalejší řezné podmínky).
- ISO N materiály = kratší strojní časy (rychlejší posuvy a otáčky).

POLOTOVAR:
- Urči tvar a rozměry polotovaru z výkresu.
- round_bar: ø + délka (přídavek na upnutí)
- flat_bar: šířka × výška × délka
- square_bar: strana × strana × délka
- hexagonal_bar: šířka (rozměr přes plochy) × délka
- plate: šířka × výška × délka (deska, přířez)
- tube: vnější ø × tloušťka stěny × délka

STROJE:
- BOMAR STG240A (pásová pila, vždy první operace)
- SMARTURN 160 (CNC soustruh, z tyče do ø40mm, menší série)
- NLX 2000 (CNC soustruh, z tyče do ø65mm, 2 vřetena — komplexní rotační díly, nebo poháněné nástroje)
- NZX 2000 (CNC soustruh, 2 vřetena + 3 revolverové hlavy — vysoce produkční, série)
- MASTURN 32 (CNC soustruh ≤ø320mm, větší a jednodušší díly, menší série)
- Soustruhy se překrývají — volba závisí na průměru, složitosti a sérii.
- MCV 750 (CNC frézka 3-osá)
- MILLTAP 700 5AX (CNC frézka 5-osá, složitější tvary)
- TAJMAC H40 (CNC frézka 4-osá horizontální)
- VS20 (sloupová vrtačka — upíchnutí z druhé strany / odjehlení)
- MECHANIK (ruční práce — srážení, začištění)
- KONTROLA (výstupní kontrola)

PRAVIDLA:
- Strojní čas = celkový čas na stroji per kus (řez, přejezdy, výměny nástrojů, upínání kusu). NE setup stroje.
- Jednoduché díly = málo operací. NEPŘIDÁVEJ zbytečné operace.
- Kooperace se NEPOČÍTÁ.
- Rotační díly ze soustruhu → většinou následuje VS20 (upíchnutí z druhé strany, odjehlení).
- Více upnutí na frézce = více operací na tom samém stroji.

JSON formát:
{
  "material_norm": "1.0503",
  "stock": {"shape": "round_bar|flat_bar|square_bar|hexagonal_bar|plate|tube", "diameter_mm": null, "width_mm": null, "height_mm": null, "length_mm": null},
  "operations": [
    {"category": "SAW|LATHE|MILL|DRILL|MANUAL|QC", "machine": "...", "operation_time_min": 0.0, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1}
  ]
}"""

# ─── WORK CENTER MAPPING ──────────────────────────────────────────────────────

WC_CATEGORY: dict[str, str] = {
    "BOMAR STG240A": "SAW",
    "SMARTURN 160": "LATHE",
    "NLX 2000": "LATHE",
    "NZX 2000": "LATHE",
    "MASTURN 32": "LATHE",
    "MCV 750": "MILL",
    "MILLTAP 700 5AX": "MILL",
    "MILLTAP 700 5AX + WH3": "MILL",
    "MILLTAP 700 + WH3": "MILL",
    "TAJMAC H40": "MILL",
    "FV20 (klasicka freza)": "MILL",
    "FV20 (klasická fréza)": "MILL",
    "VS20 (vrtacka)": "DRILL",
    "VS20 (vrtačka)": "DRILL",
    "MECHANIK": "MANUAL",
    "KONTROLA": "QC",
    "KOOPERACE": "COOP",
}

WC_NORMALIZE: dict[str, str] = {
    # MILLTAP 700 5AX + WH3 (5-axis + robot) — kept as-is in WC_CATEGORY
    # MILLTAP 700 + WH3 (3-axis + robot) — kept as-is in WC_CATEGORY
    # MILLTAP 700 5AX (5-axis manual) — kept as-is in WC_CATEGORY
    # All three are DISTINCT machines, NO merging
    "FV20 (klasicka freza)": "MCV 750",
    "FV20 (klasická fréza)": "MCV 750",
    "VS20 (vrtacka)": "VS20",
    "VS20 (vrtačka)": "VS20",
}

CAT_ORDER = ["SAW", "LATHE", "MILL", "DRILL", "MANUAL", "QC"]

# SAW/QC have legitimately tiny per-piece times (e.g. bar stock: 1 cut = 1000 pcs → 0.01 min/pc)
# Machine categories need > 0.05 to filter out noise/zero-like records
_LOW_THRESHOLD_CATS = {"SAW", "QC"}

# ─── FEW-SHOT EXAMPLES (same 6 as scripts/test_ft_v2_prompt.py) ──────────────

FEW_SHOT_EXAMPLES: dict[str, dict] = {
    "1068277": {
        "pdf": "uploads/parts/10278115/1068277_02.pdf",
        "answer": {
            "material_norm": "1.0715",
            "stock": {"shape": "round_bar", "diameter_mm": 16, "width_mm": None, "height_mm": None, "length_mm": 13},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 0.07, "setup_time_min": 0, "manning_pct": 98, "num_operations": 1},
                {"category": "LATHE", "machine": "SMARTURN 160", "operation_time_min": 0.29, "setup_time_min": 32, "manning_pct": 62, "num_operations": 1},
                {"category": "DRILL", "machine": "VS20", "operation_time_min": 0.39, "setup_time_min": 12, "manning_pct": 97, "num_operations": 1},
            ],
        },
    },
    "10109207": {
        "pdf": "uploads/parts/10171799/10109207_03.pdf",
        "answer": {
            "material_norm": "1.0715",
            "stock": {"shape": "round_bar", "diameter_mm": 18, "width_mm": None, "height_mm": None, "length_mm": 32},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 0.12, "setup_time_min": 0, "manning_pct": 70, "num_operations": 1},
                {"category": "LATHE", "machine": "SMARTURN 160", "operation_time_min": 0.97, "setup_time_min": 35, "manning_pct": 70, "num_operations": 1},
                {"category": "DRILL", "machine": "VS20", "operation_time_min": 0.34, "setup_time_min": 14, "manning_pct": 95, "num_operations": 1},
                {"category": "QC", "machine": "KONTROLA", "operation_time_min": 0.13, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1},
            ],
        },
    },
    "1007250": {
        "pdf": "uploads/parts/10990889/1007250_01.pdf",
        "answer": {
            "material_norm": "1.0715",
            "stock": {"shape": "round_bar", "diameter_mm": 25, "width_mm": None, "height_mm": None, "length_mm": 12},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 0.07, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1},
                {"category": "LATHE", "machine": "SMARTURN 160", "operation_time_min": 0.29, "setup_time_min": 50, "manning_pct": 64, "num_operations": 1},
                {"category": "DRILL", "machine": "VS20", "operation_time_min": 0.43, "setup_time_min": 13, "manning_pct": 96, "num_operations": 1},
            ],
        },
    },
    "0056204": {
        "pdf": "uploads/parts/10304600/0056204_40962_001.pdf",
        "answer": {
            "material_norm": "1.0503",
            "stock": {"shape": "flat_bar", "diameter_mm": None, "width_mm": 20, "height_mm": 12, "length_mm": 80},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 0.74, "setup_time_min": 0, "manning_pct": 82, "num_operations": 1},
                {"category": "MILL", "machine": "MILLTAP 700 5AX", "operation_time_min": 8.54, "setup_time_min": 124, "manning_pct": 81, "num_operations": 2},
            ],
        },
    },
    "0304933": {
        "pdf": "uploads/parts/10487910/0304930_D00043823_000_000.pdf",
        "answer": {
            "material_norm": "POM-C",
            "stock": {"shape": "plate", "diameter_mm": None, "width_mm": 42, "height_mm": 16, "length_mm": 159},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 1.78, "setup_time_min": 0, "manning_pct": 77, "num_operations": 1},
                {"category": "MILL", "machine": "MCV 750", "operation_time_min": 15.23, "setup_time_min": 151, "manning_pct": 85, "num_operations": 4},
                {"category": "QC", "machine": "KONTROLA", "operation_time_min": 0.31, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1},
            ],
        },
    },
    "0349384": {
        "pdf": "uploads/parts/10525255/0349384_000.pdf",
        "answer": {
            "material_norm": "3.3547",
            "stock": {"shape": "plate", "diameter_mm": None, "width_mm": 102, "height_mm": 65, "length_mm": 176},
            "operations": [
                {"category": "SAW", "machine": "BOMAR STG240A", "operation_time_min": 1.96, "setup_time_min": 0, "manning_pct": 78, "num_operations": 1},
                {"category": "MILL", "machine": "MILLTAP 700 5AX", "operation_time_min": 16.59, "setup_time_min": 121, "manning_pct": 69, "num_operations": 2},
                {"category": "QC", "machine": "KONTROLA", "operation_time_min": 0.27, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1},
            ],
        },
    },
}

# GPT-4.1 model for inference
_INFERENCE_MODEL = "gpt-4.1-2025-04-14"

# Cost per token (USD) — gpt-4.1 pricing as of 2025
_COST_PER_INPUT_TOKEN = 2.0 / 1_000_000
_COST_PER_OUTPUT_TOKEN = 8.0 / 1_000_000


# ─── HELPERS ──────────────────────────────────────────────────────────────────


def _trimmed_mean_10(values: list[float]) -> float:
    """Trimmed mean 10% — remove 10% extremes from each side."""
    if not values:
        return 0.0
    if len(values) < 5:
        return median(values) if len(values) >= 3 else mean(values)
    n = len(values)
    trim = max(1, int(n * 0.10))
    sorted_vals = sorted(values)
    trimmed = sorted_vals[trim : n - trim]
    return mean(trimmed) if trimmed else mean(values)


def _compute_cv(values: list[float]) -> Optional[float]:
    """Coefficient of variation: stdev/mean. None if < 2 samples or mean == 0."""
    if len(values) < 2:
        return None
    m = mean(values)
    if m == 0:
        return None
    return stdev(values) / m


def _extract_wnr_from_code(code: str) -> Optional[str]:
    """Extract W.Nr from material_item code like '1.0503-HR012x008-T-Kl'."""
    if not code:
        return None
    m = re.match(r"^(\d\.\d{4})", code)
    if m:
        return m.group(1)
    # Plastic codes: POM-C, PA6, PE-HD — take first segment(s) before dash
    if not code[0].isdigit():
        parts = code.split("-")
        if len(parts) >= 2 and len(parts[0]) <= 5:
            candidate = (
                f"{parts[0]}-{parts[1]}" if len(parts[1]) <= 3 else parts[0]
            )
            return candidate
    return None


def _find_pdf_path(file_path: str) -> Optional[Path]:
    """Resolve DB-relative file_path to absolute filesystem path."""
    if not file_path:
        return None
    pdf_path = PROJECT_ROOT / "uploads" / file_path
    if pdf_path.exists():
        return pdf_path
    pdf_path2 = PROJECT_ROOT / file_path
    if pdf_path2.exists():
        return pdf_path2
    return None


def _pdf_to_base64(pdf_path: Path) -> Optional[str]:
    """Render first page of PDF to base64-encoded PNG. Returns None on failure."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        page = doc[0]
        rect = page.rect
        scale_w = MAX_IMAGE_DIMENSION / rect.width
        scale_h = MAX_IMAGE_DIMENSION / rect.height
        dpi = min(300, int(72 * min(scale_w, scale_h)))
        dpi = max(dpi, 150)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()
        return base64.b64encode(png_bytes).decode("utf-8")
    except Exception as exc:
        logger.warning("PDF render failed for %s: %s", pdf_path, exc)
        return None


def _compute_gt_from_records(
    records: list[dict],
) -> tuple[list[FtPartOperation], Optional[float]]:
    """Compute ground truth operations from production records for a single part.

    Args:
        records: List of dicts with keys: infor_order_number, wc_name,
                 actual_time_min, actual_setup_min, actual_manning_coefficient,
                 manning_coefficient

    Returns:
        Tuple of (operations, max_cv). Operations are sorted by CAT_ORDER.
        max_cv is the maximum CV across all machine categories.
    """
    # Group by VP → category
    vp_data: dict = defaultdict(
        lambda: defaultdict(
            lambda: {
                "times": [], "setups": [], "mannings": [], "machines": [],
                "planned_times": [], "count": 0,
            }
        )
    )

    for row in records:
        wc_name = row["wc_name"]
        category = WC_CATEGORY.get(wc_name)
        if not category or category == "COOP":
            continue

        actual_time = row["actual_time_min"] or 0.0
        # Per-category time threshold: SAW/QC accept any >0, machine ops need >0.05
        min_time = 0.0 if category in _LOW_THRESHOLD_CATS else 0.05
        if actual_time <= min_time:
            continue

        actual_setup = row["actual_setup_min"] or 0.0
        actual_manning = row["actual_manning_coefficient"]
        planned_manning = row["manning_coefficient"]
        planned_time = row.get("planned_time_min") or 0.0
        vp_num = row["infor_order_number"]
        machine = WC_NORMALIZE.get(wc_name, wc_name)

        # Manning: prefer actual, fallback to planned; convert coefficient → percentage
        manning = actual_manning or planned_manning or 1.0
        if manning <= 2.0:
            manning *= 100
        # Cap manning to realistic range (data quality: Infor sometimes stores 4165% etc.)
        manning = min(manning, 100.0)
        manning = max(manning, 1.0)

        vp_cat = vp_data[vp_num][category]
        vp_cat["times"].append(actual_time)
        vp_cat["setups"].append(actual_setup)
        vp_cat["mannings"].append(manning)
        vp_cat["machines"].append(machine)
        vp_cat["planned_times"].append(planned_time)
        vp_cat["count"] += 1

    if not vp_data:
        return [], None

    # Aggregate per VP per category: sum times/setups/planned, avg manning
    category_vp_totals: dict = defaultdict(
        lambda: {
            "total_times": [], "total_setups": [], "mannings": [],
            "num_ops": [], "machines": [], "total_planned": [],
        }
    )

    for _vp_num, cats in vp_data.items():
        for cat, data in cats.items():
            agg = category_vp_totals[cat]
            agg["total_times"].append(sum(data["times"]))
            agg["total_setups"].append(sum(data["setups"]))
            agg["mannings"].append(
                mean(data["mannings"]) if data["mannings"] else 100.0
            )
            agg["num_ops"].append(data["count"])
            agg["machines"].extend(data["machines"])
            agg["total_planned"].append(sum(data["planned_times"]))

    operations: list[FtPartOperation] = []
    category_cvs: list[float] = []

    for cat in CAT_ORDER:
        if cat not in category_vp_totals:
            continue
        agg = category_vp_totals[cat]
        n_vp = len(agg["total_times"])
        if n_vp < 1:
            continue

        machine_counts = Counter(agg["machines"])
        main_machine = machine_counts.most_common(1)[0][0]

        ops_counts = Counter(agg["num_ops"])
        num_ops = ops_counts.most_common(1)[0][0]

        # CV computation: stdev/mean of per-VP total times and mannings
        cv = _compute_cv(agg["total_times"])
        manning_cv = _compute_cv(agg["mannings"])
        if cv is not None:
            category_cvs.append(cv)

        actual_time = round(_trimmed_mean_10(agg["total_times"]), 2)

        # Planned time: median of per-VP totals (norma is same each VP, median is robust)
        planned_vals = [v for v in agg["total_planned"] if v > 0]
        planned_time: Optional[float] = (
            round(median(planned_vals), 2) if planned_vals else None
        )
        norm_ratio: Optional[float] = None
        if planned_time and planned_time > 0 and actual_time > 0:
            norm_ratio = round(actual_time / planned_time, 3)

        operations.append(
            FtPartOperation(
                category=cat,
                machine=main_machine,
                operation_time_min=actual_time,
                setup_time_min=round(_trimmed_mean_10(agg["total_setups"])),
                manning_pct=round(_trimmed_mean_10(agg["mannings"])),
                num_operations=num_ops,
                n_vp=n_vp,
                planned_time_min=planned_time,
                norm_ratio=norm_ratio,
                cv=round(cv, 3) if cv is not None else None,
                manning_cv=round(manning_cv, 3) if manning_cv is not None else None,
            )
        )

    max_cv = max(category_cvs) if category_cvs else None
    return operations, max_cv


# ─── SERVICE ──────────────────────────────────────────────────────────────────


class FtDebugService:
    """Service for FT debug panel: GT computation, inference, and JSONL export."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_eligible_parts(self, min_vp: int = 3) -> FtPartsResponse:
        """List all parts with GT computation and eligibility analysis.

        Loads all eligible parts and their production records in two bulk queries,
        then processes them in Python to avoid N+1 queries.

        Args:
            min_vp: Minimum number of distinct VPs (production orders) required.

        Returns:
            FtPartsResponse with all parts (eligible + skipped).
        """
        # Query 1: Find candidate parts (file_id + min_vp VPs with real production data)
        parts_stmt = (
            select(
                Part.id.label("part_id"),
                Part.article_number,
                Part.name,
                Part.file_id,
                FileRecord.file_path,
                func.count(func.distinct(ProductionRecord.infor_order_number)).label("vp_count"),
            )
            .join(ProductionRecord, ProductionRecord.part_id == Part.id)
            .outerjoin(FileRecord, Part.file_id == FileRecord.id)
            .where(
                Part.file_id.isnot(None),
                ~Part.article_number.like("DRE%"),
                Part.deleted_at.is_(None),
                ProductionRecord.source == "infor",
                ProductionRecord.actual_time_min > 0,
            )
            .group_by(Part.id, Part.article_number, Part.name, Part.file_id, FileRecord.file_path)
            .having(func.count(func.distinct(ProductionRecord.infor_order_number)) >= min_vp)
            .order_by(func.count(func.distinct(ProductionRecord.infor_order_number)).desc())
        )

        try:
            parts_result = await self.db.execute(parts_stmt)
        except Exception:
            await self.db.rollback()
            raise

        parts_rows = parts_result.mappings().all()
        if not parts_rows:
            return FtPartsResponse(total=0, eligible=0, skipped=0, parts=[])

        part_ids = [row["part_id"] for row in parts_rows]

        # Query 2: Load ALL production records for these parts in one shot
        records_stmt = (
            select(
                ProductionRecord.part_id,
                ProductionRecord.infor_order_number,
                WorkCenter.name.label("wc_name"),
                ProductionRecord.planned_time_min,
                ProductionRecord.actual_time_min,
                ProductionRecord.actual_setup_min,
                ProductionRecord.actual_manning_coefficient,
                ProductionRecord.manning_coefficient,
            )
            .join(WorkCenter, ProductionRecord.work_center_id == WorkCenter.id)
            .where(
                ProductionRecord.part_id.in_(part_ids),
                ProductionRecord.source == "infor",
                ProductionRecord.actual_time_min > 0,
            )
        )

        try:
            records_result = await self.db.execute(records_stmt)
        except Exception:
            await self.db.rollback()
            raise

        records_rows = records_result.mappings().all()

        # Query 3: Load material information for all parts (incl. stock dimensions)
        materials_stmt = (
            select(
                MaterialInput.part_id,
                MaterialInput.stock_shape,
                MaterialInput.stock_diameter,
                MaterialInput.stock_width,
                MaterialInput.stock_height,
                MaterialInput.stock_length,
                MaterialItem.code.label("item_code"),
                MaterialItem.norms.label("item_norms"),
            )
            .outerjoin(MaterialItem, MaterialInput.material_item_id == MaterialItem.id)
            .where(
                MaterialInput.part_id.in_(part_ids),
                MaterialInput.deleted_at.is_(None),
            )
            .order_by(MaterialInput.part_id, MaterialInput.seq)
        )

        try:
            materials_result = await self.db.execute(materials_stmt)
        except Exception:
            await self.db.rollback()
            raise

        materials_rows = materials_result.mappings().all()

        # Query 4: Fallback material via price_category → material_group → first norm
        fallback_stmt = (
            select(
                MaterialInput.part_id,
                MaterialNorm.w_nr,
            )
            .join(MaterialPriceCategory, MaterialInput.price_category_id == MaterialPriceCategory.id)
            .join(MaterialNorm, MaterialNorm.material_group_id == MaterialPriceCategory.material_group_id)
            .where(
                MaterialInput.part_id.in_(part_ids),
                MaterialInput.deleted_at.is_(None),
                MaterialNorm.deleted_at.is_(None),
            )
            .order_by(MaterialInput.part_id, MaterialNorm.id)
        )

        try:
            fallback_result = await self.db.execute(fallback_stmt)
        except Exception:
            await self.db.rollback()
            raise

        fallback_rows = fallback_result.mappings().all()

        # Build lookup: part_id → first material row
        materials_by_part: dict[int, dict] = {}
        for row in materials_rows:
            pid = row["part_id"]
            if pid not in materials_by_part:
                materials_by_part[pid] = dict(row)

        # Build fallback lookup: part_id → first w_nr from price_category chain
        fallback_by_part: dict[int, str] = {}
        for row in fallback_rows:
            pid = row["part_id"]
            if pid not in fallback_by_part:
                fallback_by_part[pid] = row["w_nr"]

        # Group production records by part_id
        records_by_part: dict[int, list[dict]] = defaultdict(list)
        for row in records_rows:
            records_by_part[row["part_id"]].append(dict(row))

        # Process each part
        result_parts: list[FtPartSummary] = []
        eligible_count = 0
        skipped_count = 0

        for part_row in parts_rows:
            part_id = part_row["part_id"]
            article_number = part_row["article_number"]
            file_path = part_row["file_path"]

            # Resolve material norm
            mat_row = materials_by_part.get(part_id)
            material_norm: Optional[str] = None
            stock_shape: Optional[str] = None

            if mat_row:
                stock_shape = (mat_row.get("stock_shape") or "flat_bar").lower()
                # Try norms field first
                item_norms = mat_row.get("item_norms")
                if item_norms:
                    first_norm = item_norms.strip().split(",")[0].strip()
                    if first_norm:
                        material_norm = first_norm
                # Try W.Nr from item code
                if not material_norm:
                    material_norm = _extract_wnr_from_code(mat_row.get("item_code") or "")
            # Fallback via price_category chain
            if not material_norm:
                material_norm = fallback_by_part.get(part_id)

            # Compute GT operations
            part_records = records_by_part.get(part_id, [])
            operations, max_cv = _compute_gt_from_records(part_records)

            # Eligibility checks (mirrors generate_ft_v2_data.py filters)
            skip_reason: Optional[str] = None
            total_prod_time = 0.0

            if not operations:
                skip_reason = "no_gt"
            else:
                total_prod_time = sum(
                    op.operation_time_min for op in operations if op.category != "QC"
                )
                if total_prod_time < 0.1:
                    skip_reason = "time_too_low"
                elif total_prod_time > 120:
                    skip_reason = "time_too_high"
                elif not any(op.category == "SAW" for op in operations):
                    skip_reason = "no_saw"
                elif all(op.category == "SAW" for op in operations):
                    skip_reason = "only_saw"
                elif not material_norm:
                    skip_reason = "no_material"
                elif not _find_pdf_path(file_path or ""):
                    skip_reason = "no_pdf"

            is_eligible = skip_reason is None

            if is_eligible:
                eligible_count += 1
            else:
                skipped_count += 1
                operations = []  # Don't include GT ops for skipped parts
                total_prod_time = 0.0
                max_cv = None

            # Compute part-level planned time & norm ratio
            total_planned: Optional[float] = None
            part_norm_ratio: Optional[float] = None
            if operations:
                planned_ops = [
                    op.planned_time_min for op in operations
                    if op.category != "QC" and op.planned_time_min is not None
                ]
                if planned_ops:
                    total_planned = round(sum(planned_ops), 2)
                    if total_planned > 0 and total_prod_time > 0:
                        part_norm_ratio = round(total_prod_time / total_planned, 3)

            result_parts.append(
                FtPartSummary(
                    part_id=part_id,
                    article_number=article_number,
                    name=part_row["name"],
                    file_id=part_row["file_id"],
                    vp_count=part_row["vp_count"],
                    material_norm=material_norm,
                    stock_shape=stock_shape,
                    operations=operations,
                    max_cv=round(max_cv, 3) if max_cv is not None else None,
                    total_production_time=total_prod_time if is_eligible else 0.0,
                    total_planned_time=total_planned,
                    norm_ratio=part_norm_ratio,
                    skip_reason=skip_reason,
                    is_eligible=is_eligible,
                )
            )

        return FtPartsResponse(
            total=len(parts_rows),
            eligible=eligible_count,
            skipped=skipped_count,
            parts=result_parts,
        )

    async def run_inference(self, part_id: int) -> FtInferenceResult:
        """Run GPT-4.1 few-shot inference on a part and compare with GT.

        Args:
            part_id: Database ID of the part to test.

        Returns:
            FtInferenceResult with GT operations, AI operations, and comparison.

        Raises:
            ValueError: If part not found, no PDF, or OPENAI_API_KEY not set.
        """
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")

        # Load part info
        part_stmt = (
            select(
                Part.id,
                Part.article_number,
                Part.name,
                Part.file_id,
                FileRecord.file_path,
            )
            .outerjoin(FileRecord, Part.file_id == FileRecord.id)
            .where(Part.id == part_id, Part.deleted_at.is_(None))
        )

        try:
            part_result = await self.db.execute(part_stmt)
        except Exception:
            await self.db.rollback()
            raise

        part_row = part_result.mappings().one_or_none()
        if not part_row:
            raise ValueError(f"Part {part_id} not found")

        article_number = part_row["article_number"]
        file_path = part_row["file_path"]

        # Load production records for GT computation
        records_stmt = (
            select(
                ProductionRecord.infor_order_number,
                WorkCenter.name.label("wc_name"),
                ProductionRecord.planned_time_min,
                ProductionRecord.actual_time_min,
                ProductionRecord.actual_setup_min,
                ProductionRecord.actual_manning_coefficient,
                ProductionRecord.manning_coefficient,
            )
            .join(WorkCenter, ProductionRecord.work_center_id == WorkCenter.id)
            .where(
                ProductionRecord.part_id == part_id,
                ProductionRecord.source == "infor",
                ProductionRecord.actual_time_min > 0,
            )
        )

        try:
            records_result = await self.db.execute(records_stmt)
        except Exception:
            await self.db.rollback()
            raise

        records_rows = records_result.mappings().all()
        gt_operations, _ = _compute_gt_from_records([dict(r) for r in records_rows])

        # Resolve material norm for GT
        material_gt = await self._resolve_material_norm(part_id)

        # Find and render PDF
        pdf_path = _find_pdf_path(file_path or "")
        if not pdf_path:
            raise ValueError(f"No PDF found for part {part_id} (file_path={file_path})")

        img_b64 = _pdf_to_base64(pdf_path)
        if not img_b64:
            raise ValueError(f"Failed to render PDF for part {part_id}")

        # Build few-shot messages
        few_shot_messages = self._build_few_shot_messages()

        # Call GPT-4.1
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(few_shot_messages)
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analyzuj výkres a navrhni technologický postup.",
                    },
                ],
            }
        )

        response = client.chat.completions.create(
            model=_INFERENCE_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )

        raw_content = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()

        try:
            ai_result = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"GPT returned invalid JSON: {exc}") from exc

        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost_estimate = (
            prompt_tokens * _COST_PER_INPUT_TOKEN
            + completion_tokens * _COST_PER_OUTPUT_TOKEN
        )

        # Extract AI operations and material
        ai_ops_raw = ai_result.get("operations", ai_result.get("machines", []))
        material_ai = ai_result.get("material_norm", ai_result.get("material", "?"))

        # Material match check (exact or via DB aliases)
        material_match = False
        if material_gt and material_ai and material_ai != "?":
            material_match = material_gt.strip().lower() == material_ai.strip().lower()
            if not material_match:
                # Try loading DB aliases for cross-designation matching
                material_match = await self._check_material_alias_match(
                    material_gt, material_ai
                )

        # Build per-category comparisons
        gt_by_cat = {op.category: op for op in gt_operations}
        ai_by_cat = {op["category"]: op for op in ai_ops_raw}
        all_cats = sorted(
            set(list(gt_by_cat.keys()) + list(ai_by_cat.keys())),
            key=lambda c: CAT_ORDER.index(c) if c in CAT_ORDER else 99,
        )

        comparisons: list[FtInferenceComparison] = []
        mape_values: list[float] = []

        for cat in all_cats:
            gt_op = gt_by_cat.get(cat)
            ai_op = ai_by_cat.get(cat)
            if not gt_op and not ai_op:
                continue

            ai_time = (
                ai_op.get("operation_time_min", ai_op.get("total_time_min", 0.0))
                if ai_op
                else 0.0
            )
            gt_time = gt_op.operation_time_min if gt_op else 0.0
            ai_setup = (
                ai_op.get("setup_time_min", ai_op.get("total_setup_min", 0.0))
                if ai_op
                else 0.0
            )
            gt_setup = gt_op.setup_time_min if gt_op else 0.0

            delta = ai_time - gt_time

            if gt_time > 0 and cat != "QC":
                mape_values.append(abs(delta) / gt_time * 100)

            comparisons.append(
                FtInferenceComparison(
                    category=cat,
                    ai_time=ai_time,
                    gt_time=gt_time,
                    delta=round(delta, 3),
                    ai_setup=ai_setup,
                    gt_setup=gt_setup,
                )
            )

        mape = mean(mape_values) if mape_values else None

        return FtInferenceResult(
            part_id=part_id,
            article_number=article_number,
            material_gt=material_gt,
            material_ai=material_ai,
            material_match=material_match,
            gt_operations=gt_operations,
            ai_operations=ai_ops_raw,
            comparisons=comparisons,
            mape=round(mape, 1) if mape is not None else None,
            tokens_used=tokens_used,
            cost_estimate=round(cost_estimate, 4),
        )

    async def export_jsonl(self, part_ids: list[int]) -> bytes:
        """Generate JSONL bytes for download — OpenAI FT format.

        For each part: renders PDF to base64 PNG, builds training message triplet
        (system + user_image + assistant_json).

        Args:
            part_ids: List of part IDs to include.

        Returns:
            JSONL-encoded bytes (one JSON object per line).
        """
        if not part_ids:
            return b""

        # Load part + file info
        parts_stmt = (
            select(
                Part.id.label("part_id"),
                Part.article_number,
                Part.name,
                FileRecord.file_path,
            )
            .join(FileRecord, Part.file_id == FileRecord.id)
            .where(Part.id.in_(part_ids), Part.deleted_at.is_(None))
        )

        try:
            parts_result = await self.db.execute(parts_stmt)
        except Exception:
            await self.db.rollback()
            raise

        parts_rows = {row["part_id"]: dict(row) for row in parts_result.mappings().all()}

        # Load production records for all parts
        records_stmt = (
            select(
                ProductionRecord.part_id,
                ProductionRecord.infor_order_number,
                WorkCenter.name.label("wc_name"),
                ProductionRecord.planned_time_min,
                ProductionRecord.actual_time_min,
                ProductionRecord.actual_setup_min,
                ProductionRecord.actual_manning_coefficient,
                ProductionRecord.manning_coefficient,
            )
            .join(WorkCenter, ProductionRecord.work_center_id == WorkCenter.id)
            .where(
                ProductionRecord.part_id.in_(part_ids),
                ProductionRecord.source == "infor",
                ProductionRecord.actual_time_min > 0,
            )
        )

        try:
            records_result = await self.db.execute(records_stmt)
        except Exception:
            await self.db.rollback()
            raise

        records_by_part: dict[int, list[dict]] = defaultdict(list)
        for row in records_result.mappings().all():
            records_by_part[row["part_id"]].append(dict(row))

        # Load material info for all parts (incl. stock dimensions for FT answer)
        materials_stmt = (
            select(
                MaterialInput.part_id,
                MaterialInput.stock_shape,
                MaterialInput.stock_diameter,
                MaterialInput.stock_width,
                MaterialInput.stock_height,
                MaterialInput.stock_length,
                MaterialItem.code.label("item_code"),
                MaterialItem.norms.label("item_norms"),
            )
            .outerjoin(MaterialItem, MaterialInput.material_item_id == MaterialItem.id)
            .where(
                MaterialInput.part_id.in_(part_ids),
                MaterialInput.deleted_at.is_(None),
            )
            .order_by(MaterialInput.part_id, MaterialInput.seq)
        )

        try:
            materials_result = await self.db.execute(materials_stmt)
        except Exception:
            await self.db.rollback()
            raise

        materials_by_part: dict[int, dict] = {}
        for row in materials_result.mappings().all():
            pid = row["part_id"]
            if pid not in materials_by_part:
                materials_by_part[pid] = dict(row)

        # Fallback materials
        fallback_stmt = (
            select(
                MaterialInput.part_id,
                MaterialNorm.w_nr,
            )
            .join(MaterialPriceCategory, MaterialInput.price_category_id == MaterialPriceCategory.id)
            .join(MaterialNorm, MaterialNorm.material_group_id == MaterialPriceCategory.material_group_id)
            .where(
                MaterialInput.part_id.in_(part_ids),
                MaterialInput.deleted_at.is_(None),
                MaterialNorm.deleted_at.is_(None),
            )
            .order_by(MaterialInput.part_id, MaterialNorm.id)
        )

        try:
            fallback_result = await self.db.execute(fallback_stmt)
        except Exception:
            await self.db.rollback()
            raise

        fallback_by_part: dict[int, str] = {}
        for row in fallback_result.mappings().all():
            pid = row["part_id"]
            if pid not in fallback_by_part:
                fallback_by_part[pid] = row["w_nr"]

        # Build JSONL
        lines: list[bytes] = []
        skipped = 0

        for part_id in part_ids:
            part_row = parts_rows.get(part_id)
            if not part_row:
                logger.warning("export_jsonl: part %d not found", part_id)
                skipped += 1
                continue

            # Resolve GT
            part_records = records_by_part.get(part_id, [])
            operations, _ = _compute_gt_from_records(part_records)
            if not operations:
                skipped += 1
                continue

            # Resolve material
            mat_row = materials_by_part.get(part_id)
            material_norm: Optional[str] = None
            stock_shape = "flat_bar"

            if mat_row:
                stock_shape = (mat_row.get("stock_shape") or "flat_bar").lower()
                item_norms = mat_row.get("item_norms")
                if item_norms:
                    first_norm = item_norms.strip().split(",")[0].strip()
                    if first_norm:
                        material_norm = first_norm
                if not material_norm:
                    material_norm = _extract_wnr_from_code(mat_row.get("item_code") or "")
            if not material_norm:
                material_norm = fallback_by_part.get(part_id)

            if not material_norm:
                skipped += 1
                continue

            # Find and render PDF
            pdf_path = _find_pdf_path(part_row.get("file_path") or "")
            if not pdf_path:
                skipped += 1
                continue

            img_b64 = _pdf_to_base64(pdf_path)
            if not img_b64:
                skipped += 1
                continue

            # Build answer (matches few-shot format: material_norm key + real dimensions)
            stock_dims = {}
            if mat_row:
                stock_dims = {
                    "diameter_mm": mat_row.get("stock_diameter") or None,
                    "width_mm": mat_row.get("stock_width") or None,
                    "height_mm": mat_row.get("stock_height") or None,
                    "length_mm": mat_row.get("stock_length") or None,
                }
            else:
                stock_dims = {
                    "diameter_mm": None, "width_mm": None,
                    "height_mm": None, "length_mm": None,
                }
            answer = {
                "material_norm": material_norm,
                "stock": {"shape": stock_shape, **stock_dims},
                "operations": [
                    {
                        "category": op.category,
                        "machine": op.machine,
                        "operation_time_min": op.operation_time_min,
                        "setup_time_min": int(op.setup_time_min),
                        "manning_pct": op.manning_pct,
                        "num_operations": op.num_operations,
                    }
                    for op in operations
                ],
            }

            ft_entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Analyzuj výkres a navrhni technologický postup.",
                            },
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(answer, ensure_ascii=False),
                    },
                ]
            }

            lines.append(json.dumps(ft_entry, ensure_ascii=False).encode("utf-8"))

        if skipped:
            logger.info("export_jsonl: skipped %d parts (no GT, PDF, or material)", skipped)

        return b"\n".join(lines) + (b"\n" if lines else b"")

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _resolve_material_norm(self, part_id: int) -> Optional[str]:
        """Resolve material W.Nr for a single part (three-step chain)."""
        stmt = (
            select(
                MaterialItem.code.label("item_code"),
                MaterialItem.norms.label("item_norms"),
            )
            .select_from(MaterialInput)
            .outerjoin(MaterialItem, MaterialInput.material_item_id == MaterialItem.id)
            .where(MaterialInput.part_id == part_id, MaterialInput.deleted_at.is_(None))
            .order_by(MaterialInput.seq)
            .limit(1)
        )

        try:
            result = await self.db.execute(stmt)
        except Exception:
            await self.db.rollback()
            raise

        row = result.mappings().one_or_none()

        if row:
            item_norms = row.get("item_norms")
            if item_norms:
                first_norm = item_norms.strip().split(",")[0].strip()
                if first_norm:
                    return first_norm
            w_nr = _extract_wnr_from_code(row.get("item_code") or "")
            if w_nr:
                return w_nr

        # Fallback via price_category chain
        fallback_stmt = (
            select(MaterialNorm.w_nr)
            .select_from(MaterialInput)
            .join(MaterialPriceCategory, MaterialInput.price_category_id == MaterialPriceCategory.id)
            .join(MaterialNorm, MaterialNorm.material_group_id == MaterialPriceCategory.material_group_id)
            .where(
                MaterialInput.part_id == part_id,
                MaterialInput.deleted_at.is_(None),
                MaterialNorm.deleted_at.is_(None),
            )
            .order_by(MaterialNorm.id)
            .limit(1)
        )

        try:
            fallback_result = await self.db.execute(fallback_stmt)
        except Exception:
            await self.db.rollback()
            raise

        fallback_row = fallback_result.mappings().one_or_none()
        return fallback_row["w_nr"] if fallback_row else None

    async def _check_material_alias_match(self, gt: str, ai: str) -> bool:
        """Check if two material designations resolve to the same W.Nr via DB aliases."""
        alias_stmt = (
            select(
                MaterialNorm.w_nr,
                MaterialNorm.en_iso,
                MaterialNorm.csn,
                MaterialNorm.aisi,
            )
            .where(MaterialNorm.deleted_at.is_(None))
        )

        try:
            result = await self.db.execute(alias_stmt)
        except Exception:
            await self.db.rollback()
            raise

        aliases: dict[str, str] = {}
        for row in result.mappings().all():
            w_nr = (row["w_nr"] or "").strip()
            if w_nr:
                aliases[w_nr.lower()] = w_nr
            for alias in (row["en_iso"], row["csn"], row["aisi"]):
                a = (alias or "").strip().lower()
                if a:
                    aliases[a] = w_nr

        def _resolve(raw: str) -> Optional[str]:
            raw_lower = raw.strip().lower()
            if raw_lower in aliases:
                return aliases[raw_lower]
            for alias_key, w_nr_val in aliases.items():
                if alias_key in raw_lower or raw_lower in alias_key:
                    return w_nr_val
            return None

        resolved_gt = _resolve(gt)
        resolved_ai = _resolve(ai)

        if resolved_gt and resolved_ai:
            return resolved_gt == resolved_ai
        return False

    def _build_few_shot_messages(self) -> list[dict]:
        """Build few-shot messages: image + answer pairs for each example part."""
        messages: list[dict] = []
        for article, example in FEW_SHOT_EXAMPLES.items():
            pdf_path = PROJECT_ROOT / example["pdf"]
            if not pdf_path.exists():
                logger.warning("Few-shot PDF not found: %s (article %s)", pdf_path, article)
                continue
            img_b64 = _pdf_to_base64(pdf_path)
            if not img_b64:
                logger.warning("Failed to render few-shot PDF: %s", pdf_path)
                continue
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyzuj výkres a navrhni technologický postup.",
                        },
                    ],
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(example["answer"], ensure_ascii=False),
                }
            )
        return messages
