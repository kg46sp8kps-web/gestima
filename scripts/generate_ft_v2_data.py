"""Generate FT v2 training data — JSONL for OpenAI fine-tuning.

Pipeline:
1. Find all parts with drawing (file_id) + ≥3 VPs (production_records)
2. For each part: compute GT per machine category (trimmed mean from VP data)
3. Resolve material_norm from material_inputs → PriceCategory → MaterialGroup
4. Resolve stock from material_inputs
5. Generate JSONL: system prompt + user image + assistant JSON answer

Usage:
    python scripts/generate_ft_v2_data.py                    # Generate JSONL
    python scripts/generate_ft_v2_data.py --dry-run           # Analyze only, no JSONL
    python scripts/generate_ft_v2_data.py --min-vp 5          # Require ≥5 VPs
    python scripts/generate_ft_v2_data.py --validate           # Validate existing JSONL
"""

import argparse
import base64
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF required. Install: pip install PyMuPDF")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "gestima.db"
MAX_IMAGE_DIMENSION = 4096
OUTPUT_DIR = PROJECT_ROOT / "data"

# ─── SYSTEM PROMPT (must match test_ft_v2_prompt.py) ──────────────────

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
  "material": "1.0503",
  "stock": {"shape": "round_bar|flat_bar|square_bar|hexagonal_bar|plate|tube", "diameter_mm": null, "width_mm": null, "height_mm": null, "length_mm": null},
  "operations": [
    {"category": "SAW|LATHE|MILL|DRILL|MANUAL|QC", "machine": "...", "operation_time_min": 0.0, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1}
  ]
}"""

# ─── WORK CENTER MAPPING ─────────────────────────────────────────────

WC_CATEGORY = {
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

# Normalize machine names for output (merge variants)
WC_NORMALIZE = {
    "MILLTAP 700 5AX + WH3": "MILLTAP 700 5AX",
    "MILLTAP 700 + WH3": "MILLTAP 700 5AX",
    "FV20 (klasicka freza)": "MCV 750",  # legacy mill → map to MCV
    "FV20 (klasická fréza)": "MCV 750",
    "NZX 2000": "NZX 2000",  # standalone — production lathe, 3 turrets
    "VS20 (vrtacka)": "VS20",
    "VS20 (vrtačka)": "VS20",
    "MASTURN 32": "MASTURN 32",
}

# Shape mapping from price_category names
SHAPE_KEYWORDS = {
    "kruhova": "round_bar",
    "ctvercova": "square_bar",
    "plocha": "flat_bar",
    "plech": "plate",
    "deska": "plate",
    "profil": "flat_bar",
    "trubka": "tube",
}


# ─── CLAMP CONSTANTS ─────────────────────────────────────────────────

MANNING_MIN = 30
MANNING_MAX = 120
SETUP_MAX = 360  # 6 hours max


# ─── HELPERS ──────────────────────────────────────────────────────────

def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, value))


def trimmed_mean_10(values: list) -> float:
    """Trimmed mean 10% — remove 10% extremes from each side."""
    if not values:
        return 0.0
    if len(values) < 5:
        return median(values) if len(values) >= 3 else mean(values)
    n = len(values)
    trim = max(1, int(n * 0.10))
    sorted_vals = sorted(values)
    trimmed = sorted_vals[trim:n - trim]
    return mean(trimmed) if trimmed else mean(values)


def pdf_to_base64(pdf_path: str) -> str | None:
    """Render PDF first page to base64 PNG."""
    try:
        doc = fitz.open(pdf_path)
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
    except Exception as e:
        print(f"    ⚠️  PDF render failed: {e}")
        return None


def resolve_shape(price_cat_name: str | None) -> str:
    """Resolve stock shape from price category name."""
    if not price_cat_name:
        return "flat_bar"  # safe default
    name_lower = price_cat_name.lower()
    for keyword, shape in SHAPE_KEYWORDS.items():
        if keyword in name_lower:
            return shape
    return "flat_bar"


# ─── GT COMPUTATION ──────────────────────────────────────────────────

def compute_gt_for_part(conn: sqlite3.Connection, part_id: int) -> list[dict] | None:
    """Compute ground truth per machine category from VP production records.

    Returns list of operations dicts or None if insufficient data.
    Algorithm:
    1. For each VP: group operations by category, sum times
    2. Trimmed mean across VPs per category
    """
    rows = conn.execute("""
        SELECT pr.infor_order_number, wc.name as wc_name,
               pr.actual_time_min, pr.actual_setup_min,
               pr.actual_manning_coefficient,
               pr.planned_time_min, pr.planned_setup_min,
               pr.manning_coefficient
        FROM production_records pr
        JOIN work_centers wc ON pr.work_center_id = wc.id
        WHERE pr.part_id = ?
        AND pr.source = 'infor'
        AND pr.actual_time_min > 0.05
    """, (part_id,)).fetchall()

    if not rows:
        return None

    # Group by VP → category
    vp_data = defaultdict(lambda: defaultdict(lambda: {
        "times": [], "setups": [], "mannings": [], "machines": [], "count": 0
    }))

    for row in rows:
        vp_num = row[0]
        wc_name = row[1]
        actual_time = row[2] or 0
        actual_setup = row[3] or 0
        actual_manning = row[4]
        planned_manning = row[7]

        category = WC_CATEGORY.get(wc_name)
        if not category or category == "COOP":
            continue

        machine = WC_NORMALIZE.get(wc_name, wc_name)

        # Manning: prefer actual, fallback to planned, convert if needed
        manning = actual_manning or planned_manning or 1.0
        if manning <= 2.0:
            manning *= 100  # coefficient → percentage

        vp_cat = vp_data[vp_num][category]
        vp_cat["times"].append(actual_time)
        vp_cat["setups"].append(actual_setup)
        vp_cat["mannings"].append(manning)
        vp_cat["machines"].append(machine)
        vp_cat["count"] += 1

    if not vp_data:
        return None

    # Aggregate per VP: sum times/setups per category, avg manning
    category_vp_totals = defaultdict(lambda: {
        "total_times": [], "total_setups": [], "mannings": [],
        "num_ops": [], "machines": []
    })

    for vp_num, cats in vp_data.items():
        for cat, data in cats.items():
            cat_agg = category_vp_totals[cat]
            cat_agg["total_times"].append(sum(data["times"]))
            cat_agg["total_setups"].append(sum(data["setups"]))
            cat_agg["mannings"].append(mean(data["mannings"]) if data["mannings"] else 100)
            cat_agg["num_ops"].append(data["count"])
            cat_agg["machines"].extend(data["machines"])

    # Compute final GT per category
    operations = []
    cat_order = ["SAW", "LATHE", "MILL", "DRILL", "MANUAL", "QC"]

    for cat in cat_order:
        if cat not in category_vp_totals:
            continue
        agg = category_vp_totals[cat]
        n_vp = len(agg["total_times"])

        if n_vp < 1:
            continue

        # Most common machine
        machine_counts = Counter(agg["machines"])
        main_machine = machine_counts.most_common(1)[0][0]

        # Num operations: mode (most common count per VP)
        ops_counts = Counter(agg["num_ops"])
        num_ops = ops_counts.most_common(1)[0][0]

        operations.append({
            "category": cat,
            "machine": main_machine,
            "operation_time_min": round(trimmed_mean_10(agg["total_times"]), 2),
            "setup_time_min": round(trimmed_mean_10(agg["total_setups"])),
            "manning_pct": round(trimmed_mean_10(agg["mannings"])),
            "num_operations": num_ops,
            "n_vp": n_vp,
        })

    return operations if operations else None


def get_material_and_stock(conn: sqlite3.Connection, part_id: int) -> tuple[str | None, dict]:
    """Get material_norm and stock dimensions from material_inputs."""
    row = conn.execute("""
        SELECT mi.stock_shape, mi.stock_diameter, mi.stock_length,
               mi.stock_width, mi.stock_height,
               mi.material_item_id, mi.price_category_id
        FROM material_inputs mi
        WHERE mi.part_id = ?
        AND mi.deleted_at IS NULL
        ORDER BY mi.seq
        LIMIT 1
    """, (part_id,)).fetchone()

    if not row:
        return None, {"shape": "flat_bar", "diameter_mm": None, "width_mm": None,
                       "height_mm": None, "length_mm": None}

    shape = (row[0] or "flat_bar").lower()
    diameter = row[1]
    length = row[2]
    width = row[3]
    height = row[4]

    stock = {
        "shape": shape,
        "diameter_mm": round(diameter) if diameter else None,
        "width_mm": round(width) if width else None,
        "height_mm": round(height) if height else None,
        "length_mm": round(length) if length else None,
    }

    # Get material_norm via material_item or price_category
    material_norm = get_material_norm_direct(conn, part_id)

    return material_norm, stock


def _extract_wnr_from_code(code: str) -> str | None:
    """Extract W.Nr from material_item code like '1.0503-HR012x008-T-Kl' → '1.0503'."""
    import re
    if not code:
        return None
    # W.Nr pattern: digit.digit(s) at start of code (e.g. 1.0503, 3.3547, POM-C)
    m = re.match(r'^(\d\.\d{4})', code)
    if m:
        return m.group(1)
    # Plastic codes: POM-C, PA6, PE-HD etc. — take first segment before dash if no W.Nr
    if not code[0].isdigit():
        # e.g. "POM-C-..." → "POM-C"
        parts = code.split("-")
        if len(parts) >= 2 and len(parts[0]) <= 5:
            candidate = f"{parts[0]}-{parts[1]}" if len(parts[1]) <= 3 else parts[0]
            return candidate
    return None


def get_material_norm_direct(conn: sqlite3.Connection, part_id: int) -> str | None:
    """Get the most specific material_norm W.Nr from material_inputs chain."""
    # 1. Try via material_item.code — W.Nr is encoded at start (e.g. "1.0503-HR012x008")
    row = conn.execute("""
        SELECT mitem.code, mitem.norms
        FROM material_inputs mi
        JOIN material_items mitem ON mi.material_item_id = mitem.id
        WHERE mi.part_id = ?
        AND mi.deleted_at IS NULL
        LIMIT 1
    """, (part_id,)).fetchone()

    if row:
        # Try norms field first (most explicit)
        if row[1]:
            norms_str = row[1].strip()
            # "1.0503, C45, 12050" → "1.0503"
            first_norm = norms_str.split(",")[0].strip()
            if first_norm:
                return first_norm

        # Parse W.Nr from code
        w_nr = _extract_wnr_from_code(row[0])
        if w_nr:
            return w_nr

    # 2. Fallback: via price_category → material_group → first norm
    row = conn.execute("""
        SELECT mn.w_nr
        FROM material_inputs mi
        JOIN material_price_categories pc ON mi.price_category_id = pc.id
        JOIN material_norms mn ON mn.material_group_id = pc.material_group_id
        WHERE mi.part_id = ?
        AND mi.deleted_at IS NULL
        AND mn.deleted_at IS NULL
        ORDER BY mn.id
        LIMIT 1
    """, (part_id,)).fetchone()

    return row[0] if row else None


def find_pdf_path(conn: sqlite3.Connection, part_id: int) -> Path | None:
    """Find PDF file path for a part via file_id → file_records."""
    row = conn.execute("""
        SELECT fr.file_path
        FROM parts p
        JOIN file_records fr ON p.file_id = fr.id
        WHERE p.id = ?
    """, (part_id,)).fetchone()

    if not row or not row[0]:
        return None

    # file_path in DB is relative: "parts/xxx/yyy.pdf"
    # Actual files are in "uploads/parts/xxx/yyy.pdf"
    pdf_path = PROJECT_ROOT / "uploads" / row[0]
    if pdf_path.exists():
        return pdf_path
    # Fallback: try without uploads/ prefix
    pdf_path2 = PROJECT_ROOT / row[0]
    if pdf_path2.exists():
        return pdf_path2
    return None


# ─── MAIN PIPELINE ───────────────────────────────────────────────────

SMALL_BATCH_THRESHOLD = 5  # ks — serie ≤5 ks get relaxed VP requirement
SMALL_BATCH_MIN_VP = 1     # minimum VP for small-batch parts


def generate_ft_data(min_vp: int = 3, dry_run: bool = False, validate: bool = False,
                     small_batch: bool = False):
    """Main pipeline: generate FT training JSONL."""
    if validate:
        return validate_jsonl()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Find eligible parts
    if small_batch:
        # Include small-batch exception: ≥1 VP with avg batch ≤5 ks
        parts = conn.execute("""
            SELECT p.id, p.article_number, p.name,
                   COUNT(DISTINCT pr.infor_order_number) as vp_count,
                   AVG(pr.batch_quantity) as avg_batch
            FROM parts p
            JOIN production_records pr ON pr.part_id = p.id
                AND pr.source = 'infor' AND pr.actual_time_min > 0.05
            WHERE p.file_id IS NOT NULL
            AND p.article_number NOT LIKE 'DRE%'
            AND p.deleted_at IS NULL
            GROUP BY p.id
            HAVING vp_count >= ?
               OR (vp_count >= ? AND avg_batch <= ?)
            ORDER BY vp_count DESC
        """, (min_vp, SMALL_BATCH_MIN_VP, SMALL_BATCH_THRESHOLD)).fetchall()
    else:
        # Standard: only ≥min_vp
        parts = conn.execute("""
            SELECT p.id, p.article_number, p.name,
                   COUNT(DISTINCT pr.infor_order_number) as vp_count,
                   AVG(pr.batch_quantity) as avg_batch
            FROM parts p
            JOIN production_records pr ON pr.part_id = p.id
                AND pr.source = 'infor' AND pr.actual_time_min > 0.05
            WHERE p.file_id IS NOT NULL
            AND p.article_number NOT LIKE 'DRE%'
            AND p.deleted_at IS NULL
            GROUP BY p.id
            HAVING vp_count >= ?
            ORDER BY vp_count DESC
        """, (min_vp,)).fetchall()

    n_standard = sum(1 for p in parts if p["vp_count"] >= min_vp)
    n_small_batch = len(parts) - n_standard
    print(f"Found {len(parts)} eligible parts:")
    print(f"  Standard (≥{min_vp} VP):        {n_standard}")
    if small_batch:
        print(f"  Small-batch (≤{SMALL_BATCH_THRESHOLD} ks, ≥{SMALL_BATCH_MIN_VP} VP): {n_small_batch}")

    # Stats counters
    stats = {
        "total": len(parts),
        "n_standard": n_standard,
        "n_small_batch": n_small_batch,
        "gt_ok": 0,
        "gt_fail": 0,
        "pdf_ok": 0,
        "pdf_fail": 0,
        "material_ok": 0,
        "material_fail": 0,
        "jsonl_written": 0,
        "included_standard": 0,
        "included_small_batch": 0,
        "categories": Counter(),
        "machines": Counter(),
        "time_distribution": [],
        "skipped_reasons": Counter(),
    }

    training_samples = []

    for i, part in enumerate(parts):
        part_id = part["id"]
        article = part["article_number"]
        name = part["name"]
        vp_count = part["vp_count"]

        if (i + 1) % 50 == 0:
            print(f"  Processing {i + 1}/{len(parts)}...")

        # 1. Compute GT
        operations = compute_gt_for_part(conn, part_id)
        if not operations:
            stats["gt_fail"] += 1
            stats["skipped_reasons"]["no_gt"] += 1
            continue
        stats["gt_ok"] += 1

        # Quality filter: skip if total production time is suspicious
        total_prod_time = sum(
            op["operation_time_min"] for op in operations
            if op["category"] != "QC"
        )
        if total_prod_time < 0.1:
            stats["skipped_reasons"]["time_too_low"] += 1
            continue
        if total_prod_time > 120:
            stats["skipped_reasons"]["time_too_high"] += 1
            continue

        # Extra filter for small-batch (1-2 VP): reject extreme per-operation values
        # These parts have no trimmed mean → single VP outlier would poison FT
        is_low_vp = vp_count < min_vp
        if is_low_vp:
            has_extreme = False
            for op in operations:
                t = op["operation_time_min"]
                s = op["setup_time_min"]
                cat = op["category"]
                # Per-category sanity bounds (from P99 of standard dataset)
                if cat == "SAW" and (t > 40 or s > 30):
                    has_extreme = True
                elif cat == "LATHE" and (t > 90 or s > 450):
                    has_extreme = True
                elif cat == "MILL" and (t > 80 or s > 350):
                    has_extreme = True
                elif cat == "DRILL" and (t > 15 or s > 120):
                    has_extreme = True
                elif cat == "MANUAL" and (t > 10 or s > 50):
                    has_extreme = True
                elif cat == "QC" and (t > 10 or s > 10):
                    has_extreme = True
            if has_extreme:
                stats["skipped_reasons"]["small_batch_extreme"] += 1
                continue

        # 2. Quality filter: must have SAW (prompt says "vždy první operace")
        op_categories = [op["category"] for op in operations]
        if "SAW" not in op_categories:
            stats["skipped_reasons"]["no_saw"] += 1
            continue

        # 3. Get material and stock
        material_norm, stock = get_material_and_stock(conn, part_id)

        if material_norm:
            stats["material_ok"] += 1
        else:
            stats["material_fail"] += 1
            stats["skipped_reasons"]["no_material"] += 1
            continue  # SKIP — model must not learn to say "?"

        # Quality filter: must have stock dimensions
        has_stock_dims = any(
            v for k, v in stock.items() if k != "shape" and v
        )
        if not has_stock_dims:
            stats["skipped_reasons"]["no_stock_dims"] += 1
            continue

        # 4. Find PDF
        pdf_path = find_pdf_path(conn, part_id)
        if not pdf_path:
            stats["pdf_fail"] += 1
            stats["skipped_reasons"]["no_pdf"] += 1
            continue
        stats["pdf_ok"] += 1

        # 5. Build answer JSON — clamp outliers
        clean_ops = []
        for op in operations:
            clean_op = {
                "category": op["category"],
                "machine": op["machine"],
                "operation_time_min": op["operation_time_min"],
                "setup_time_min": min(op["setup_time_min"], SETUP_MAX),
                "manning_pct": round(clamp(op["manning_pct"], MANNING_MIN, MANNING_MAX)),
                "num_operations": op["num_operations"],
            }
            clean_ops.append(clean_op)
            stats["categories"][op["category"]] += 1
            stats["machines"][op["machine"]] += 1

        answer = {
            "material": material_norm,
            "stock": stock,
            "operations": clean_ops,
        }

        stats["time_distribution"].append(total_prod_time)

        # Track standard vs small-batch
        is_small_batch = vp_count < min_vp
        if is_small_batch:
            stats["included_small_batch"] += 1
        else:
            stats["included_standard"] += 1

        training_samples.append({
            "article": article,
            "name": name,
            "vp_count": vp_count,
            "pdf_path": str(pdf_path),
            "answer": answer,
            "is_small_batch": is_small_batch,
        })

    conn.close()

    # ── Print stats ──
    print(f"\n{'=' * 60}")
    print(f"  FT v2 DATA GENERATION — STATISTICS")
    print(f"{'=' * 60}")
    print(f"\n  Total eligible parts:    {stats['total']}")
    print(f"    Standard (≥{min_vp} VP):     {stats['n_standard']}")
    print(f"    Small-batch (≤{SMALL_BATCH_THRESHOLD} ks):   {stats['n_small_batch']}")
    print(f"  GT computed OK:          {stats['gt_ok']}")
    print(f"  GT failed:               {stats['gt_fail']}")
    print(f"  PDF found:               {stats['pdf_ok']}")
    print(f"  PDF missing:             {stats['pdf_fail']}")
    print(f"  Material found:          {stats['material_ok']}")
    print(f"  Material missing:        {stats['material_fail']}")
    print(f"  ────────────────────────")
    print(f"  Training samples ready:  {len(training_samples)}")
    print(f"    Standard:              {stats['included_standard']}")
    print(f"    Small-batch:           {stats['included_small_batch']}")

    if stats["skipped_reasons"]:
        print(f"\n  Skipped reasons:")
        for reason, count in stats["skipped_reasons"].most_common():
            print(f"    {reason}: {count}")

    if stats["categories"]:
        print(f"\n  Operations by category:")
        for cat, count in stats["categories"].most_common():
            print(f"    {cat}: {count}")

    if stats["machines"]:
        print(f"\n  Operations by machine:")
        for machine, count in stats["machines"].most_common(10):
            print(f"    {machine}: {count}")

    if stats["time_distribution"]:
        times = sorted(stats["time_distribution"])
        print(f"\n  Production time distribution:")
        print(f"    Min:    {times[0]:.2f} min")
        print(f"    P25:    {times[len(times)//4]:.2f} min")
        print(f"    Median: {times[len(times)//2]:.2f} min")
        print(f"    P75:    {times[3*len(times)//4]:.2f} min")
        print(f"    Max:    {times[-1]:.2f} min")

    if dry_run:
        print(f"\n  DRY RUN — no JSONL generated")
        # Save GT JSON for review
        gt_review = {}
        for sample in training_samples[:20]:  # First 20 for review
            gt_review[sample["article"]] = {
                "name": sample["name"],
                "vp_count": sample["vp_count"],
                **sample["answer"],
            }
        review_path = OUTPUT_DIR / "ft_v2_training_preview.json"
        with open(review_path, "w") as f:
            json.dump(gt_review, f, indent=2, ensure_ascii=False)
        print(f"  Preview saved: {review_path} ({len(gt_review)} samples)")
        return

    # ── Generate JSONL ──
    print(f"\n📦 Generating JSONL ({len(training_samples)} samples)...")
    jsonl_path = OUTPUT_DIR / "ft_v2_training.jsonl"

    written = 0
    failed_pdf = 0

    with open(jsonl_path, "w") as f:
        for i, sample in enumerate(training_samples):
            if (i + 1) % 50 == 0:
                print(f"  Rendering PDF {i + 1}/{len(training_samples)}...")

            img_b64 = pdf_to_base64(sample["pdf_path"])
            if not img_b64:
                failed_pdf += 1
                continue

            # OpenAI FT format for vision
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
                        "content": json.dumps(sample["answer"], ensure_ascii=False),
                    },
                ],
            }

            f.write(json.dumps(ft_entry, ensure_ascii=False) + "\n")
            written += 1

    print(f"\n  ✅ JSONL written: {jsonl_path}")
    print(f"     Samples: {written}")
    print(f"     Failed PDFs: {failed_pdf}")
    print(f"     File size: {jsonl_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Save metadata
    meta = {
        "samples": written,
        "min_vp": min_vp,
        "system_prompt_len": len(SYSTEM_PROMPT),
        "categories": dict(stats["categories"]),
        "machines": dict(stats["machines"]),
    }
    meta_path = OUTPUT_DIR / "ft_v2_training_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"     Metadata: {meta_path}")


def validate_jsonl():
    """Validate existing JSONL file."""
    jsonl_path = OUTPUT_DIR / "ft_v2_training.jsonl"
    if not jsonl_path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return

    print(f"Validating: {jsonl_path}")
    errors = []
    warnings = []
    total = 0

    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            total += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: Invalid JSON — {e}")
                continue

            msgs = entry.get("messages", [])
            if len(msgs) != 3:
                errors.append(f"Line {line_num}: Expected 3 messages, got {len(msgs)}")
                continue

            # Check system
            if msgs[0]["role"] != "system":
                errors.append(f"Line {line_num}: First message must be system")

            # Check user (image)
            if msgs[1]["role"] != "user":
                errors.append(f"Line {line_num}: Second message must be user")
            else:
                content = msgs[1]["content"]
                if not isinstance(content, list):
                    errors.append(f"Line {line_num}: User content must be list")
                else:
                    has_image = any(c.get("type") == "image_url" for c in content)
                    if not has_image:
                        errors.append(f"Line {line_num}: Missing image in user message")

            # Check assistant (JSON answer)
            if msgs[2]["role"] != "assistant":
                errors.append(f"Line {line_num}: Third message must be assistant")
            else:
                try:
                    answer = json.loads(msgs[2]["content"])
                    # Validate answer structure
                    if "material" not in answer:
                        warnings.append(f"Line {line_num}: Missing material")
                    if "operations" not in answer:
                        errors.append(f"Line {line_num}: Missing operations")
                    else:
                        for op in answer["operations"]:
                            required_keys = ["category", "machine", "operation_time_min",
                                             "setup_time_min", "manning_pct", "num_operations"]
                            for k in required_keys:
                                if k not in op:
                                    errors.append(f"Line {line_num}: Operation missing '{k}'")
                except json.JSONDecodeError:
                    errors.append(f"Line {line_num}: Assistant content is not valid JSON")

    print(f"\n  Total samples: {total}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\n  ❌ ERRORS:")
        for e in errors[:20]:
            print(f"    {e}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more")

    if warnings:
        print(f"\n  ⚠️  WARNINGS:")
        for w in warnings[:10]:
            print(f"    {w}")

    if not errors:
        print(f"\n  ✅ All {total} samples valid!")


# ─── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FT v2 training data")
    parser.add_argument("--min-vp", type=int, default=3, help="Minimum VPs per part (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, no JSONL")
    parser.add_argument("--validate", action="store_true", help="Validate existing JSONL")
    parser.add_argument("--small-batch", action="store_true",
                        help="Include small-batch exception (≤5 ks with ≥1 VP). "
                             "WARNING: contaminates serial production times!")
    args = parser.parse_args()

    generate_ft_data(min_vp=args.min_vp, dry_run=args.dry_run, validate=args.validate,
                     small_batch=args.small_batch)
