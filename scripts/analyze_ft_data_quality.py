"""FT Training Data Quality Analysis — Gestima

Standalone script (no FastAPI/SQLAlchemy), uses sqlite3 directly.
Replicates GT computation logic from app/services/ft_debug_service.py:
  - trimmed_mean_10
  - WC_CATEGORY mapping
  - min_vp=3

DO NOT modify any project files — analysis only.
"""

import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Optional

# ─── CONSTANTS (identical to ft_debug_service.py) ─────────────────────────────

DB_PATH = Path("/Users/lofas/Documents/__App_Claude/Gestima/gestima.db")

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
    "MILLTAP 700 5AX + WH3": "MILLTAP 700 5AX",
    "MILLTAP 700 + WH3": "MILLTAP 700 5AX",
    "FV20 (klasicka freza)": "MCV 750",
    "FV20 (klasická fréza)": "MCV 750",
    "VS20 (vrtacka)": "VS20",
    "VS20 (vrtačka)": "VS20",
}

CAT_ORDER = ["SAW", "LATHE", "MILL", "DRILL", "MANUAL", "QC"]

MIN_VP = 3


# ─── HELPERS (identical to ft_debug_service.py) ───────────────────────────────


def trimmed_mean_10(values: list[float]) -> float:
    """Trimmed mean 10% — remove 10% extremes from each side."""
    if not values:
        return 0.0
    if len(values) < 5:
        return median(values) if len(values) >= 3 else mean(values)
    n = len(values)
    trim = max(1, int(n * 0.10))
    sorted_vals = sorted(values)
    trimmed = sorted_vals[trim: n - trim]
    return mean(trimmed) if trimmed else mean(values)


def compute_cv(values: list[float]) -> Optional[float]:
    """Coefficient of variation: stdev/mean. None if < 2 samples or mean == 0."""
    if len(values) < 2:
        return None
    m = mean(values)
    if m == 0:
        return None
    return stdev(values) / m


def compute_gt_from_records(records: list[dict]) -> tuple[dict, Optional[float], Optional[float]]:
    """Compute ground truth operations from production records.

    Returns:
        (ops_by_category, max_time_cv, max_manning_cv)
        ops_by_category: dict[str, dict] with keys:
            actual_time, planned_time, norm_ratio, time_cv, manning_cv, n_vp, machine
    """
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
        actual_setup = row["actual_setup_min"] or 0.0
        actual_manning = row["actual_manning_coefficient"]
        planned_manning = row["manning_coefficient"]
        planned_time = row.get("planned_time_min") or 0.0
        vp_num = row["infor_order_number"]
        machine = WC_NORMALIZE.get(wc_name, wc_name)

        manning = actual_manning or planned_manning or 1.0
        if manning <= 2.0:
            manning *= 100

        vp_cat = vp_data[vp_num][category]
        vp_cat["times"].append(actual_time)
        vp_cat["setups"].append(actual_setup)
        vp_cat["mannings"].append(manning)
        vp_cat["machines"].append(machine)
        vp_cat["planned_times"].append(planned_time)
        vp_cat["count"] += 1

    if not vp_data:
        return {}, None, None

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

    ops_by_cat: dict = {}
    time_cvs: list[float] = []
    manning_cvs: list[float] = []

    for cat in CAT_ORDER:
        if cat not in category_vp_totals:
            continue
        agg = category_vp_totals[cat]
        n_vp = len(agg["total_times"])
        if n_vp < 1:
            continue

        machine_counts = Counter(agg["machines"])
        main_machine = machine_counts.most_common(1)[0][0]

        time_cv = compute_cv(agg["total_times"])
        manning_cv = compute_cv(agg["mannings"])

        if time_cv is not None:
            time_cvs.append(time_cv)
        if manning_cv is not None:
            manning_cvs.append(manning_cv)

        actual_time = round(trimmed_mean_10(agg["total_times"]), 4)

        planned_vals = [v for v in agg["total_planned"] if v > 0]
        planned_time: Optional[float] = (
            round(median(planned_vals), 4) if planned_vals else None
        )
        norm_ratio: Optional[float] = None
        if planned_time and planned_time > 0 and actual_time > 0:
            norm_ratio = round(actual_time / planned_time, 4)

        ops_by_cat[cat] = {
            "actual_time": actual_time,
            "planned_time": planned_time,
            "norm_ratio": norm_ratio,
            "time_cv": round(time_cv, 4) if time_cv is not None else None,
            "manning_cv": round(manning_cv, 4) if manning_cv is not None else None,
            "n_vp": n_vp,
            "machine": main_machine,
        }

    max_time_cv = max(time_cvs) if time_cvs else None
    max_manning_cv = max(manning_cvs) if manning_cvs else None
    return ops_by_cat, max_time_cv, max_manning_cv


# ─── DATA LOADING ─────────────────────────────────────────────────────────────


def load_all_data(min_vp: int = MIN_VP) -> list[dict]:
    """Load all eligible parts and their production records. Returns list of part dicts."""

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Find parts with enough VPs
    parts_sql = """
        SELECT
            p.id            AS part_id,
            p.article_number,
            COUNT(DISTINCT pr.infor_order_number) AS vp_count
        FROM parts p
        JOIN production_records pr
            ON pr.part_id = p.id
            AND pr.source = 'infor'
            AND pr.actual_time_min > 0.05
        WHERE p.file_id IS NOT NULL
          AND p.article_number NOT LIKE 'DRE%'
          AND p.deleted_at IS NULL
        GROUP BY p.id, p.article_number
        HAVING vp_count >= ?
        ORDER BY vp_count DESC
    """

    parts_rows = conn.execute(parts_sql, (min_vp,)).fetchall()
    if not parts_rows:
        conn.close()
        return []

    part_ids = [r["part_id"] for r in parts_rows]
    part_id_tuple = tuple(part_ids)
    placeholders = ",".join("?" * len(part_ids))

    # Load production records
    records_sql = f"""
        SELECT
            pr.part_id,
            pr.infor_order_number,
            wc.name                     AS wc_name,
            pr.planned_time_min,
            pr.actual_time_min,
            pr.actual_setup_min,
            pr.actual_manning_coefficient,
            pr.manning_coefficient
        FROM production_records pr
        JOIN work_centers wc ON pr.work_center_id = wc.id
        WHERE pr.part_id IN ({placeholders})
          AND pr.source = 'infor'
          AND pr.actual_time_min > 0.05
    """

    records_rows = conn.execute(records_sql, part_id_tuple).fetchall()
    conn.close()

    # Group records by part_id
    records_by_part: dict[int, list[dict]] = defaultdict(list)
    for row in records_rows:
        records_by_part[row["part_id"]].append(dict(row))

    # Build part summaries with GT computation
    result = []
    for part_row in parts_rows:
        part_id = part_row["part_id"]
        part_records = records_by_part.get(part_id, [])
        ops_by_cat, max_time_cv, max_manning_cv = compute_gt_from_records(part_records)

        result.append({
            "part_id": part_id,
            "article_number": part_row["article_number"],
            "vp_count": part_row["vp_count"],
            "ops": ops_by_cat,
            "max_time_cv": max_time_cv,
            "max_manning_cv": max_manning_cv,
        })

    return result


# ─── FORMATTING HELPERS ────────────────────────────────────────────────────────


def hdr(title: str) -> None:
    """Print section header."""
    width = 80
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def sub(title: str) -> None:
    """Print subsection header."""
    print(f"\n--- {title} ---")


def fmt_pct(val: float) -> str:
    return f"{val:.1f}%"


def fmt_ratio(val: Optional[float]) -> str:
    if val is None:
        return "  N/A "
    return f"{val:6.3f}"


# ─── ANALYSIS 1: Norm ratio distribution ──────────────────────────────────────


def analysis_1_ratio_distribution(parts: list[dict]) -> None:
    """Distribution of norm_ratio (actual/planned) for LATHE and MILL."""
    hdr("ANALYSIS 1 — Norm Ratio Distribution (actual/planned)")

    buckets = [
        ("<0.3",   lambda r: r < 0.3),
        ("0.3-0.5", lambda r: 0.3 <= r < 0.5),
        ("0.5-0.7", lambda r: 0.5 <= r < 0.7),
        ("0.7-0.9", lambda r: 0.7 <= r < 0.9),
        ("0.9-1.1", lambda r: 0.9 <= r < 1.1),
        ("1.1-1.3", lambda r: 1.1 <= r < 1.3),
        ("1.3-1.5", lambda r: 1.3 <= r < 1.5),
        ("1.5-2.0", lambda r: 1.5 <= r < 2.0),
        ("2.0-3.0", lambda r: 2.0 <= r < 3.0),
        ("3.0+",    lambda r: r >= 3.0),
    ]

    for cat in ["LATHE", "MILL"]:
        ratios = []
        for p in parts:
            op = p["ops"].get(cat)
            if op and op["norm_ratio"] is not None:
                ratios.append(op["norm_ratio"])

        if not ratios:
            print(f"\n{cat}: no data")
            continue

        print(f"\n{cat}  (n={len(ratios)}, median={median(ratios):.3f}, "
              f"mean={mean(ratios):.3f}, stdev={stdev(ratios) if len(ratios) > 1 else 0:.3f})")
        print(f"  {'Bucket':<12} {'Count':>6}  {'%':>6}  {'CumPct':>7}")
        print(f"  {'-'*12} {'-'*6}  {'-'*6}  {'-'*7}")

        cum = 0
        for label, predicate in buckets:
            count = sum(1 for r in ratios if predicate(r))
            cum += count
            pct = count / len(ratios) * 100
            cum_pct = cum / len(ratios) * 100
            bar = "#" * int(pct / 2)
            print(f"  {label:<12} {count:>6}  {pct:>5.1f}%  {cum_pct:>6.1f}%  {bar}")


# ─── ANALYSIS 2: Combined filter matrix ───────────────────────────────────────


def analysis_2_filter_matrix(parts: list[dict]) -> None:
    """Matrix of filter combinations showing survival count and median norm ratio."""
    hdr("ANALYSIS 2 — Combined Filter Matrix")

    time_cv_limits = [0.3, 0.4, 0.5, 0.6, None]
    manning_cv_limits = [0.3, 0.4, 0.5, 0.6, None]
    ratio_ranges = [
        ("no limit", None, None),
        ("0.3-3.0",  0.3, 3.0),
        ("0.5-2.0",  0.5, 2.0),
        ("0.5-3.0",  0.5, 3.0),
    ]
    min_vp_list = [3, 5, 8]

    # We focus on the most useful axis: time_cv x ratio_range, with min_vp rows
    # for clarity. Manning CV is included as secondary analysis.

    total_parts = len(parts)

    for min_vp_val in min_vp_list:
        sub(f"Min VP = {min_vp_val}")

        # Filter parts with enough VPs
        vp_parts = [p for p in parts if p["vp_count"] >= min_vp_val]

        print(f"\n  Parts with VP >= {min_vp_val}: {len(vp_parts)}/{total_parts}")
        print(f"\n  {'Time CV':>8}  {'Ratio Range':>12}  {'N':>5}  {'%':>5}  "
              f"{'Median Ratio':>12}  {'MCV=0.5 N':>10}  {'MCV=0.5 %':>10}")
        print(f"  {'':>8}  {'':>12}  {'-'*5}  {'-'*5}  {'-'*12}  {'-'*10}  {'-'*10}")

        for time_cv_limit in [0.3, 0.4, 0.5, None]:
            for rr_label, rr_min, rr_max in ratio_ranges:
                # Apply filters per category (LATHE + MILL)
                surviving = []
                surviving_manning = []

                for p in vp_parts:
                    passes_all_cats = True
                    passes_manning = True
                    has_lathe_or_mill = False

                    for cat in ["LATHE", "MILL"]:
                        op = p["ops"].get(cat)
                        if op is None:
                            continue
                        has_lathe_or_mill = True

                        # Time CV filter
                        if time_cv_limit is not None and op["time_cv"] is not None:
                            if op["time_cv"] > time_cv_limit:
                                passes_all_cats = False
                                passes_manning = False
                                break

                        # Ratio filter
                        if op["norm_ratio"] is not None:
                            if rr_min is not None and op["norm_ratio"] < rr_min:
                                passes_all_cats = False
                                passes_manning = False
                                break
                            if rr_max is not None and op["norm_ratio"] > rr_max:
                                passes_all_cats = False
                                passes_manning = False
                                break

                        # Manning CV (secondary filter — test both with and without)
                        if op["manning_cv"] is not None and op["manning_cv"] > 0.5:
                            passes_manning = False

                    if not has_lathe_or_mill:
                        # Parts without LATHE/MILL don't contribute to ratio analysis
                        continue

                    if passes_all_cats:
                        # Collect all ratios from this part
                        for cat in ["LATHE", "MILL"]:
                            op = p["ops"].get(cat)
                            if op and op["norm_ratio"] is not None:
                                surviving.append(op["norm_ratio"])
                        # Count unique parts
                    if passes_manning:
                        for cat in ["LATHE", "MILL"]:
                            op = p["ops"].get(cat)
                            if op and op["norm_ratio"] is not None:
                                surviving_manning.append(op["norm_ratio"])

                # Count unique parts (not individual category observations)
                n_parts_surviving = 0
                n_parts_manning = 0
                for p in vp_parts:
                    passes_any_cat = False
                    passes_manning_any = False
                    has_lathe_or_mill = False
                    part_ok = True
                    part_manning_ok = True

                    for cat in ["LATHE", "MILL"]:
                        op = p["ops"].get(cat)
                        if op is None:
                            continue
                        has_lathe_or_mill = True

                        if time_cv_limit is not None and op["time_cv"] is not None:
                            if op["time_cv"] > time_cv_limit:
                                part_ok = False
                                part_manning_ok = False

                        if op["norm_ratio"] is not None:
                            if rr_min is not None and op["norm_ratio"] < rr_min:
                                part_ok = False
                                part_manning_ok = False
                            if rr_max is not None and op["norm_ratio"] > rr_max:
                                part_ok = False
                                part_manning_ok = False

                        if op["manning_cv"] is not None and op["manning_cv"] > 0.5:
                            part_manning_ok = False

                    if not has_lathe_or_mill:
                        continue
                    if part_ok:
                        n_parts_surviving += 1
                    if part_manning_ok:
                        n_parts_manning += 1

                # Compute ratios from surviving (unique part level)
                surviving_ratios = []
                for p in vp_parts:
                    part_ok = True
                    has_lathe_or_mill = False

                    for cat in ["LATHE", "MILL"]:
                        op = p["ops"].get(cat)
                        if op is None:
                            continue
                        has_lathe_or_mill = True

                        if time_cv_limit is not None and op["time_cv"] is not None:
                            if op["time_cv"] > time_cv_limit:
                                part_ok = False
                                break

                        if op["norm_ratio"] is not None:
                            if rr_min is not None and op["norm_ratio"] < rr_min:
                                part_ok = False
                                break
                            if rr_max is not None and op["norm_ratio"] > rr_max:
                                part_ok = False
                                break

                    if not has_lathe_or_mill or not part_ok:
                        continue

                    for cat in ["LATHE", "MILL"]:
                        op = p["ops"].get(cat)
                        if op and op["norm_ratio"] is not None:
                            surviving_ratios.append(op["norm_ratio"])

                parts_with_lm = sum(1 for p in vp_parts if any(p["ops"].get(c) for c in ["LATHE", "MILL"]))
                pct_surviving = n_parts_surviving / parts_with_lm * 100 if parts_with_lm > 0 else 0
                pct_manning = n_parts_manning / parts_with_lm * 100 if parts_with_lm > 0 else 0

                med_ratio = f"{median(surviving_ratios):.3f}" if surviving_ratios else "  N/A"
                tcv_label = f"cv<={time_cv_limit}" if time_cv_limit is not None else "no limit"

                print(f"  {tcv_label:>8}  {rr_label:>12}  {n_parts_surviving:>5}  "
                      f"{pct_surviving:>4.0f}%  {med_ratio:>12}  {n_parts_manning:>10}  "
                      f"{pct_manning:>9.0f}%")


# ─── ANALYSIS 3: Outlier analysis ─────────────────────────────────────────────


def analysis_3_outliers(parts: list[dict]) -> None:
    """Parts with norm_ratio > 2.0 OR < 0.3 on any LATHE or MILL category."""
    hdr("ANALYSIS 3 — Outlier Analysis (norm_ratio > 2.0 OR < 0.3)")

    outliers = []
    for p in parts:
        for cat in ["LATHE", "MILL"]:
            op = p["ops"].get(cat)
            if op is None or op["norm_ratio"] is None:
                continue
            if op["norm_ratio"] > 2.0 or op["norm_ratio"] < 0.3:
                outliers.append({
                    "article_number": p["article_number"],
                    "category": cat,
                    "norm_ratio": op["norm_ratio"],
                    "actual_time": op["actual_time"],
                    "planned_time": op["planned_time"],
                    "time_cv": op["time_cv"],
                    "manning_cv": op["manning_cv"],
                    "n_vp": op["n_vp"],
                    "machine": op["machine"],
                    "vp_count": p["vp_count"],
                })

    print(f"\nTotal outlier observations: {len(outliers)}")
    total_with_ratio = sum(
        1 for p in parts
        for cat in ["LATHE", "MILL"]
        if p["ops"].get(cat) and p["ops"][cat]["norm_ratio"] is not None
    )
    print(f"Total observations with ratio: {total_with_ratio}")
    print(f"Outlier rate: {len(outliers)/total_with_ratio*100:.1f}%" if total_with_ratio else "")

    # CV analysis of outliers
    high_cv_outliers = [o for o in outliers if o["time_cv"] is not None and o["time_cv"] > 0.5]
    print(f"\nOutliers also with time_cv > 0.5: {len(high_cv_outliers)} / {len(outliers)} "
          f"({len(high_cv_outliers)/len(outliers)*100:.1f}%)" if outliers else "")

    # Machine breakdown
    machine_counts = Counter(o["machine"] for o in outliers)
    sub("Machine breakdown of outliers")
    for machine, cnt in machine_counts.most_common():
        print(f"  {machine:<25} {cnt:>4} outliers")

    # Ratio direction
    high_outliers = [o for o in outliers if o["norm_ratio"] > 2.0]
    low_outliers = [o for o in outliers if o["norm_ratio"] < 0.3]
    print(f"\nHigh outliers (ratio > 2.0): {len(high_outliers)}")
    print(f"Low outliers (ratio < 0.3):  {len(low_outliers)}")

    # Extreme ratio distribution
    sub("Ratio sub-ranges for high outliers")
    high_buckets = [(">10x", 10.0), (">5x", 5.0), (">3x", 3.0), (">2x", 2.0)]
    for label, threshold in high_buckets:
        cnt = sum(1 for o in outliers if o["norm_ratio"] >= threshold)
        print(f"  norm_ratio {label}: {cnt}")


# ─── ANALYSIS 4: Optimal filter recommendation ────────────────────────────────


def _apply_filter(
    parts: list[dict],
    time_cv_max: Optional[float] = None,
    manning_cv_max: Optional[float] = None,
    ratio_min: Optional[float] = None,
    ratio_max: Optional[float] = None,
    min_vp_override: Optional[int] = None,
    target_cats: list[str] = None,
) -> tuple[list[dict], list[float], list[float], list[float]]:
    """Apply filters and return (surviving_parts, lathe_ratios, mill_ratios, all_ratios)."""
    if target_cats is None:
        target_cats = ["LATHE", "MILL"]

    surviving = []
    lathe_ratios = []
    mill_ratios = []

    for p in parts:
        if min_vp_override is not None and p["vp_count"] < min_vp_override:
            continue

        part_ok = True
        has_target_cat = False

        for cat in target_cats:
            op = p["ops"].get(cat)
            if op is None:
                continue
            has_target_cat = True

            if time_cv_max is not None and op["time_cv"] is not None:
                if op["time_cv"] > time_cv_max:
                    part_ok = False
                    break

            if manning_cv_max is not None and op["manning_cv"] is not None:
                if op["manning_cv"] > manning_cv_max:
                    part_ok = False
                    break

            if op["norm_ratio"] is not None:
                if ratio_min is not None and op["norm_ratio"] < ratio_min:
                    part_ok = False
                    break
                if ratio_max is not None and op["norm_ratio"] > ratio_max:
                    part_ok = False
                    break

        if not has_target_cat or not part_ok:
            continue

        surviving.append(p)

        for cat in target_cats:
            op = p["ops"].get(cat)
            if op and op["norm_ratio"] is not None:
                if cat == "LATHE":
                    lathe_ratios.append(op["norm_ratio"])
                elif cat == "MILL":
                    mill_ratios.append(op["norm_ratio"])

    all_ratios = lathe_ratios + mill_ratios
    return surviving, lathe_ratios, mill_ratios, all_ratios


def _ratio_stats(ratios: list[float]) -> str:
    """Format ratio statistics."""
    if not ratios:
        return "N/A"
    med = median(ratios)
    mn = mean(ratios)
    sd = stdev(ratios) if len(ratios) > 1 else 0
    return f"med={med:.3f} mean={mn:.3f} std={sd:.3f}"


def analysis_4_optimal_filters(parts: list[dict]) -> None:
    """Test predefined filter combinations and report quality metrics."""
    hdr("ANALYSIS 4 — Optimal Filter Recommendation")

    total_hours = 0.0
    for p in parts:
        for cat in ["LATHE", "MILL"]:
            op = p["ops"].get(cat)
            if op:
                total_hours += op["actual_time"]

    filter_sets = [
        ("A", "time_cv<=0.5 AND manning_cv<=0.5",
         dict(time_cv_max=0.5, manning_cv_max=0.5)),
        ("B", "A + ratio 0.5-2.0",
         dict(time_cv_max=0.5, manning_cv_max=0.5, ratio_min=0.5, ratio_max=2.0)),
        ("C", "A + ratio 0.3-3.0",
         dict(time_cv_max=0.5, manning_cv_max=0.5, ratio_min=0.3, ratio_max=3.0)),
        ("D", "time_cv<=0.4 + ratio 0.5-2.5",
         dict(time_cv_max=0.4, ratio_min=0.5, ratio_max=2.5)),
        ("E", "time_cv<=0.5 only + ratio 0.5-2.5",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=2.5)),
        ("F", "min_vp=5 + time_cv<=0.5 + ratio 0.5-2.5",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=2.5, min_vp_override=5)),
        ("G", "time_cv<=0.6 + ratio 0.4-2.5",
         dict(time_cv_max=0.6, ratio_min=0.4, ratio_max=2.5)),
        ("H", "time_cv<=0.5 + ratio 0.5-3.0",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=3.0)),
    ]

    print(f"\n{'ID':<4} {'Description':<38} {'N Parts':>7}  {'Lathe':^20}  {'Mill':^20}  {'All':^20}  {'Good%':>6}")
    print(f"{'':4} {'':38} {'':>7}  {'med/mean/std':^20}  {'med/mean/std':^20}  {'med/mean/std':^20}  {'':>6}")
    print("-" * 130)

    filter_results = {}

    for fid, desc, kwargs in filter_sets:
        surviving, lathe_r, mill_r, all_r = _apply_filter(parts, **kwargs)
        good_pct = (sum(1 for r in all_r if 0.7 <= r <= 1.5) / len(all_r) * 100) if all_r else 0

        filter_results[fid] = {
            "n": len(surviving),
            "lathe_r": lathe_r,
            "mill_r": mill_r,
            "all_r": all_r,
            "good_pct": good_pct,
            "hours": sum(
                (p["ops"].get(c, {}) or {}).get("actual_time", 0.0)
                for p in surviving for c in ["LATHE", "MILL"]
            ),
        }

        print(f"  {fid:<2}  {desc:<38} {len(surviving):>7}  "
              f"{_ratio_stats(lathe_r):^20}  "
              f"{_ratio_stats(mill_r):^20}  "
              f"{_ratio_stats(all_r):^20}  "
              f"{good_pct:>5.1f}%")

    # Correction coefficients
    sub("Correction coefficients (1/median_ratio)")
    print(f"\n  {'ID':<4} {'Correction':>10}  {'Interpretation'}")
    print(f"  {'':4} {'':>10}  {'(multiply AI estimates by this factor)'}")
    for fid, _, _ in filter_sets:
        data = filter_results[fid]
        if data["all_r"]:
            med = median(data["all_r"])
            corr = 1.0 / med if med > 0 else None
            interp = "plans underestimate" if corr and corr > 1 else "plans overestimate"
            print(f"  {fid:<4} {corr:>10.3f}  {interp}" if corr else f"  {fid:<4} {'N/A':>10}")


# ─── ANALYSIS 5: 2-4x outlier deep dive ──────────────────────────────────────


def analysis_5_outlier_deep_dive(parts: list[dict]) -> None:
    """Deep dive into parts where any category has norm_ratio > 2.0."""
    hdr("ANALYSIS 5 — '2-4x Outlier' Deep Dive (norm_ratio > 2.0)")

    offenders = []
    for p in parts:
        for cat in ["LATHE", "MILL"]:
            op = p["ops"].get(cat)
            if op is None or op["norm_ratio"] is None:
                continue
            if op["norm_ratio"] > 2.0:
                offenders.append({
                    "article_number": p["article_number"],
                    "category": cat,
                    "norm_ratio": op["norm_ratio"],
                    "actual_time": op["actual_time"],
                    "planned_time": op["planned_time"],
                    "time_cv": op["time_cv"],
                    "manning_cv": op["manning_cv"],
                    "n_vp": op["n_vp"],
                    "machine": op["machine"],
                    "vp_count": p["vp_count"],
                })

    offenders.sort(key=lambda x: x["norm_ratio"], reverse=True)

    print(f"\nTotal observations with norm_ratio > 2.0: {len(offenders)}")

    # Unique parts
    unique_parts = set(o["article_number"] for o in offenders)
    print(f"Unique parts affected: {len(unique_parts)}")

    # What % are also high-CV
    high_cv_count = sum(1 for o in offenders if o["time_cv"] is not None and o["time_cv"] > 0.5)
    if offenders:
        print(f"\nOf these, also have time_cv > 0.5: {high_cv_count}/{len(offenders)} "
              f"({high_cv_count/len(offenders)*100:.1f}%)")
        med_cv = median([o["time_cv"] for o in offenders if o["time_cv"] is not None] or [0])
        print(f"Median time_cv of these outliers: {med_cv:.3f}")

    # Dataset change if we remove ratio > 2.0
    all_obs_count = sum(
        1 for p in parts
        for cat in ["LATHE", "MILL"]
        if p["ops"].get(cat) and p["ops"][cat]["norm_ratio"] is not None
    )
    all_parts_count = sum(
        1 for p in parts
        if any(p["ops"].get(c) and p["ops"][c]["norm_ratio"] is not None
               for c in ["LATHE", "MILL"])
    )
    parts_removed = len(unique_parts)
    parts_remaining = all_parts_count - parts_removed
    print(f"\nIf we remove all parts with ratio > 2.0:")
    print(f"  Parts before: {all_parts_count}")
    print(f"  Parts removed: {parts_removed} ({parts_removed/all_parts_count*100:.1f}%)")
    print(f"  Parts remaining: {parts_remaining} ({parts_remaining/all_parts_count*100:.1f}%)")

    # Top 20 worst offenders
    sub("Top 20 worst offenders")
    print(f"\n  {'#':>3}  {'Article':>10}  {'Cat':>5}  {'Ratio':>7}  "
          f"{'Actual':>7}  {'Planned':>8}  {'TimCV':>6}  {'ManCV':>6}  {'VP':>3}  Machine")
    print(f"  {'-'*3}  {'-'*10}  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*3}  {'-'*20}")

    for i, o in enumerate(offenders[:20], 1):
        tcv = f"{o['time_cv']:.3f}" if o["time_cv"] is not None else "  N/A"
        mcv = f"{o['manning_cv']:.3f}" if o["manning_cv"] is not None else "  N/A"
        plan = f"{o['planned_time']:.2f}" if o["planned_time"] is not None else "   N/A"
        print(f"  {i:>3}  {o['article_number']:>10}  {o['category']:>5}  "
              f"{o['norm_ratio']:>7.3f}  {o['actual_time']:>7.2f}  {plan:>8}  "
              f"{tcv:>6}  {mcv:>6}  {o['n_vp']:>3}  {o['machine']}")

    # Ratio sub-buckets of these outliers
    sub("Ratio distribution among >2.0 outliers")
    sub_buckets = [(">10x", 10.0), ("5-10x", 5.0), ("3-5x", 3.0), ("2-3x", 2.0)]
    print(f"\n  {'Range':<10}  {'Count':>5}  {'%':>6}")
    for i, (label, low) in enumerate(sub_buckets):
        high = sub_buckets[i-1][1] if i > 0 else float("inf")
        cnt = sum(1 for o in offenders if o["norm_ratio"] >= low and
                  (i == 0 or o["norm_ratio"] < sub_buckets[i-1][1]))
        pct = cnt / len(offenders) * 100 if offenders else 0
        print(f"  {label:<10}  {cnt:>5}  {pct:>5.1f}%")


# ─── ANALYSIS 6: Training sample quality score ────────────────────────────────


def analysis_6_quality_score(parts: list[dict]) -> None:
    """Compute composite quality score for each filter combination."""
    hdr("ANALYSIS 6 — Training Sample Quality Score")

    # Total production hours (for coverage score)
    total_hours = sum(
        (p["ops"].get(c) or {}).get("actual_time", 0.0)
        for p in parts for c in ["LATHE", "MILL"]
    )

    filter_sets = [
        ("A", "time_cv<=0.5 AND manning_cv<=0.5",
         dict(time_cv_max=0.5, manning_cv_max=0.5)),
        ("B", "A + ratio 0.5-2.0",
         dict(time_cv_max=0.5, manning_cv_max=0.5, ratio_min=0.5, ratio_max=2.0)),
        ("C", "A + ratio 0.3-3.0",
         dict(time_cv_max=0.5, manning_cv_max=0.5, ratio_min=0.3, ratio_max=3.0)),
        ("D", "time_cv<=0.4 + ratio 0.5-2.5",
         dict(time_cv_max=0.4, ratio_min=0.5, ratio_max=2.5)),
        ("E", "time_cv<=0.5 only + ratio 0.5-2.5",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=2.5)),
        ("F", "min_vp=5 + time_cv<=0.5 + ratio 0.5-2.5",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=2.5, min_vp_override=5)),
        ("G", "time_cv<=0.6 + ratio 0.4-2.5",
         dict(time_cv_max=0.6, ratio_min=0.4, ratio_max=2.5)),
        ("H", "time_cv<=0.5 + ratio 0.5-3.0",
         dict(time_cv_max=0.5, ratio_min=0.5, ratio_max=3.0)),
    ]

    print(f"\n  Scoring formula:")
    print(f"    Size score      = N/1000 (capped at 1.0)")
    print(f"    Consistency     = 1 - std(norm_ratio)  (lower std = better)")
    print(f"    Accuracy        = 1 - |median_ratio - 1.0|  (closer to 1.0 = better)")
    print(f"    Coverage        = % of total production hours covered")
    print(f"    Composite       = 0.3*size + 0.3*consistency + 0.2*accuracy + 0.2*coverage")

    print(f"\n  {'ID':<4} {'N':>6}  {'Size':>6}  {'Consis':>7}  {'Accur':>7}  "
          f"{'Cover':>7}  {'Score':>7}  Description")
    print("-" * 100)

    scores = []

    for fid, desc, kwargs in filter_sets:
        surviving, lathe_r, mill_r, all_r = _apply_filter(parts, **kwargs)
        n = len(surviving)

        if not all_r:
            print(f"  {fid:<4} {n:>6}  {'N/A':>6}  {'N/A':>7}  {'N/A':>7}  {'N/A':>7}  {'N/A':>7}  {desc}")
            continue

        # Scores
        size_score = min(1.0, n / 1000.0)
        sd = stdev(all_r) if len(all_r) > 1 else 0
        consistency_score = max(0.0, 1.0 - sd)
        med = median(all_r)
        accuracy_score = max(0.0, 1.0 - abs(med - 1.0))

        surviving_hours = sum(
            (p["ops"].get(c) or {}).get("actual_time", 0.0)
            for p in surviving for c in ["LATHE", "MILL"]
        )
        coverage_score = min(1.0, surviving_hours / total_hours) if total_hours > 0 else 0.0

        composite = (
            0.3 * size_score
            + 0.3 * consistency_score
            + 0.2 * accuracy_score
            + 0.2 * coverage_score
        )

        scores.append((fid, desc, n, size_score, consistency_score, accuracy_score, coverage_score, composite))

        print(f"  {fid:<4} {n:>6}  {size_score:>6.3f}  {consistency_score:>7.3f}  "
              f"{accuracy_score:>7.3f}  {coverage_score:>7.3f}  {composite:>7.3f}  {desc}")

    if scores:
        best = max(scores, key=lambda x: x[7])
        print(f"\n  RECOMMENDED: Filter '{best[0]}' — {best[1]}")
        print(f"  Composite score: {best[7]:.3f}, N={best[2]} parts")


# ─── SUMMARY ─────────────────────────────────────────────────────────────────


def summary(parts: list[dict]) -> None:
    """Print overall dataset summary."""
    hdr("DATASET SUMMARY")

    total = len(parts)
    with_lathe = sum(1 for p in parts if p["ops"].get("LATHE"))
    with_mill = sum(1 for p in parts if p["ops"].get("MILL"))
    with_both = sum(1 for p in parts if p["ops"].get("LATHE") and p["ops"].get("MILL"))
    with_saw = sum(1 for p in parts if p["ops"].get("SAW"))

    lathe_ratios = [p["ops"]["LATHE"]["norm_ratio"] for p in parts
                    if p["ops"].get("LATHE") and p["ops"]["LATHE"]["norm_ratio"] is not None]
    mill_ratios = [p["ops"]["MILL"]["norm_ratio"] for p in parts
                   if p["ops"].get("MILL") and p["ops"]["MILL"]["norm_ratio"] is not None]
    all_ratios = lathe_ratios + mill_ratios

    print(f"\nTotal parts loaded (min_vp={MIN_VP}): {total}")
    print(f"  With LATHE operations: {with_lathe} ({with_lathe/total*100:.1f}%)")
    print(f"  With MILL operations:  {with_mill} ({with_mill/total*100:.1f}%)")
    print(f"  With BOTH L+M:         {with_both} ({with_both/total*100:.1f}%)")
    print(f"  With SAW:              {with_saw} ({with_saw/total*100:.1f}%)")
    print(f"\nLATHE norm_ratio: n={len(lathe_ratios)}, "
          f"median={median(lathe_ratios):.3f}, mean={mean(lathe_ratios):.3f}"
          if lathe_ratios else "\nLATHE: no ratios")
    print(f"MILL  norm_ratio: n={len(mill_ratios)}, "
          f"median={median(mill_ratios):.3f}, mean={mean(mill_ratios):.3f}"
          if mill_ratios else "MILL:  no ratios")
    print(f"TOTAL norm_ratio: n={len(all_ratios)}, "
          f"median={median(all_ratios):.3f}, mean={mean(all_ratios):.3f}"
          if all_ratios else "TOTAL: no ratios")

    # VP count distribution
    vp_counts = [p["vp_count"] for p in parts]
    sub("VP count distribution")
    for threshold in [3, 5, 8, 10, 15, 20]:
        cnt = sum(1 for v in vp_counts if v >= threshold)
        print(f"  Parts with VP >= {threshold:>2}: {cnt:>5} ({cnt/total*100:.1f}%)")


# ─── MAIN ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run all analyses."""
    print(f"\nGESTIMA FT Training Data Quality Analysis")
    print(f"Database: {DB_PATH}")
    print(f"GT logic: trimmed_mean_10 | WC_CATEGORY mapping | min_vp={MIN_VP}")

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"\nLoading data...")
    parts = load_all_data(min_vp=MIN_VP)
    print(f"Loaded {len(parts)} parts.")

    if not parts:
        print("No data found. Exiting.")
        sys.exit(1)

    summary(parts)
    analysis_1_ratio_distribution(parts)
    analysis_2_filter_matrix(parts)
    analysis_3_outliers(parts)
    analysis_4_optimal_filters(parts)
    analysis_5_outlier_deep_dive(parts)
    analysis_6_quality_score(parts)

    print("\n" + "=" * 80)
    print("  Analysis complete.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
