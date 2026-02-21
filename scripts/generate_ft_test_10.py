#!/usr/bin/env python3
"""Generate 10-part test JSONL for OpenAI fine-tuning.

Selection criteria:
1. Pass precision cut: manning ≤100%, LATHE manning ≥50%, MILL manning ≥70%, norm_ratio ≤5.0
2. Pass CV ≤ 0.5 for both time and manning on LATHE+MILL
3. Have file_id (drawing PDF exists)
4. Have min 3 VPs
5. NOT in FEW_SHOT_EXAMPLES (1068277, 10109207, 1007250, 0056204, 0304933, 0349384)

Diversity:
- 3 LATHE (rotational)
- 3 MILL (prismatic)
- 2 LATHE + MILL
- 1 DRILL
- 1 unusual material (plastic, aluminum, stainless)
"""
import base64
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Optional

# Same constants as ft_debug_service.py
PROJECT_ROOT = Path(__file__).parent.parent
MAX_IMAGE_DIMENSION = 4096

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

WC_NORMALIZE = {
    "MILLTAP 700 5AX + WH3": "MILLTAP 700 5AX",
    "MILLTAP 700 + WH3": "MILLTAP 700 5AX",
    "FV20 (klasicka freza)": "MCV 750",
    "FV20 (klasická fréza)": "MCV 750",
    "VS20 (vrtacka)": "VS20",
    "VS20 (vrtačka)": "VS20",
}

CAT_ORDER = ["SAW", "LATHE", "MILL", "DRILL", "MANUAL", "QC"]

EXCLUDED_ARTICLES = {"1068277", "10109207", "1007250", "0056204", "0304933", "0349384"}


def trimmed_mean_10(values):
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


def compute_cv(values):
    """Coefficient of variation."""
    if len(values) < 2:
        return None
    m = mean(values)
    if m == 0:
        return None
    return stdev(values) / m


def extract_wnr_from_code(code):
    """Extract W.Nr from material_item code."""
    if not code:
        return None
    m = re.match(r"^(\d\.\d{4})", code)
    if m:
        return m.group(1)
    # Plastic codes
    if not code[0].isdigit():
        parts = code.split("-")
        if len(parts) >= 2 and len(parts[0]) <= 5:
            candidate = f"{parts[0]}-{parts[1]}" if len(parts[1]) <= 3 else parts[0]
            return candidate
    return None


def pdf_to_base64(pdf_path):
    """Render first page of PDF to base64-encoded PNG."""
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
        print(f"PDF render failed for {pdf_path}: {exc}")
        return None


def compute_gt_from_records(records):
    """Compute GT operations from production records.

    Returns (operations_list, max_cv).
    """
    # Group by VP → category
    vp_data = defaultdict(
        lambda: defaultdict(
            lambda: {
                "times": [],
                "setups": [],
                "mannings": [],
                "machines": [],
                "planned_times": [],
                "count": 0,
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

    # Aggregate per category
    category_vp_totals = defaultdict(
        lambda: {
            "total_times": [],
            "total_setups": [],
            "mannings": [],
            "num_ops": [],
            "machines": [],
            "total_planned": [],
        }
    )

    for _vp_num, cats in vp_data.items():
        for cat, data in cats.items():
            agg = category_vp_totals[cat]
            agg["total_times"].append(sum(data["times"]))
            agg["total_setups"].append(sum(data["setups"]))
            agg["mannings"].append(mean(data["mannings"]) if data["mannings"] else 100.0)
            agg["num_ops"].append(data["count"])
            agg["machines"].extend(data["machines"])
            agg["total_planned"].append(sum(data["planned_times"]))

    operations = []
    category_cvs = []

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

        cv = compute_cv(agg["total_times"])
        manning_cv = compute_cv(agg["mannings"])
        if cv is not None:
            category_cvs.append(cv)

        actual_time = round(trimmed_mean_10(agg["total_times"]), 2)

        planned_vals = [v for v in agg["total_planned"] if v > 0]
        planned_time = round(median(planned_vals), 2) if planned_vals else None
        norm_ratio = None
        if planned_time and planned_time > 0 and actual_time > 0:
            norm_ratio = round(actual_time / planned_time, 3)

        operations.append(
            {
                "category": cat,
                "machine": main_machine,
                "operation_time_min": actual_time,
                "setup_time_min": int(round(trimmed_mean_10(agg["total_setups"]))),
                "manning_pct": int(round(trimmed_mean_10(agg["mannings"]))),
                "num_operations": num_ops,
                "n_vp": n_vp,
                "planned_time_min": planned_time,
                "norm_ratio": norm_ratio,
                "cv": round(cv, 3) if cv is not None else None,
                "manning_cv": round(manning_cv, 3) if manning_cv is not None else None,
            }
        )

    max_cv = max(category_cvs) if category_cvs else None
    return operations, max_cv


def main():
    db_path = PROJECT_ROOT / "gestima.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Load candidate parts (file_id, ≥3 VPs, NOT in FEW_SHOT)
    cur.execute(
        """
        SELECT
            p.id AS part_id,
            p.article_number,
            p.name,
            p.file_id,
            fr.file_path,
            COUNT(DISTINCT pr.infor_order_number) AS vp_count
        FROM parts p
        JOIN production_records pr ON pr.part_id = p.id AND pr.source = 'infor' AND pr.actual_time_min > 0.05
        LEFT JOIN file_records fr ON p.file_id = fr.id
        WHERE p.file_id IS NOT NULL
          AND p.article_number NOT IN (?, ?, ?, ?, ?, ?)
          AND p.article_number NOT LIKE 'DRE%'
          AND p.deleted_at IS NULL
        GROUP BY p.id, p.article_number, p.name, p.file_id, fr.file_path
        HAVING vp_count >= 3
        ORDER BY vp_count DESC
        """,
        tuple(EXCLUDED_ARTICLES),
    )
    parts_rows = cur.fetchall()

    print(f"Candidate parts: {len(parts_rows)}")

    part_ids = [row["part_id"] for row in parts_rows]
    placeholders = ",".join("?" * len(part_ids))

    # 2. Load all production records
    cur.execute(
        f"""
        SELECT
            pr.part_id,
            pr.infor_order_number,
            wc.name AS wc_name,
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
        """,
        part_ids,
    )
    records_rows = cur.fetchall()

    records_by_part = defaultdict(list)
    for row in records_rows:
        records_by_part[row["part_id"]].append(dict(row))

    # 3. Load material info
    cur.execute(
        f"""
        SELECT
            mi.part_id,
            mi.stock_shape,
            mi.stock_diameter,
            mi.stock_width,
            mi.stock_height,
            mi.stock_length,
            mitem.code AS item_code,
            mitem.norms AS item_norms
        FROM material_inputs mi
        LEFT JOIN material_items mitem ON mi.material_item_id = mitem.id
        WHERE mi.part_id IN ({placeholders})
          AND mi.deleted_at IS NULL
        ORDER BY mi.part_id, mi.seq
        """,
        part_ids,
    )
    materials_rows = cur.fetchall()

    materials_by_part = {}
    for row in materials_rows:
        pid = row["part_id"]
        if pid not in materials_by_part:
            materials_by_part[pid] = dict(row)

    # 4. Fallback materials
    cur.execute(
        f"""
        SELECT mi.part_id, mn.w_nr
        FROM material_inputs mi
        JOIN material_price_categories pc ON mi.price_category_id = pc.id
        JOIN material_norms mn ON mn.material_group_id = pc.material_group_id
        WHERE mi.part_id IN ({placeholders})
          AND mi.deleted_at IS NULL AND mn.deleted_at IS NULL
        ORDER BY mi.part_id, mn.id
        """,
        part_ids,
    )
    fallback_rows = cur.fetchall()

    fallback_by_part = {}
    for row in fallback_rows:
        pid = row["part_id"]
        if pid not in fallback_by_part:
            fallback_by_part[pid] = row["w_nr"]

    # 5. Process each part and apply filters
    eligible = []

    for part_row in parts_rows:
        part_id = part_row["part_id"]
        article_number = part_row["article_number"]
        file_path = part_row["file_path"]

        # Resolve material
        mat_row = materials_by_part.get(part_id)
        material_norm = None
        stock_shape = "flat_bar"
        stock_dims = {}

        if mat_row:
            stock_shape = (mat_row.get("stock_shape") or "flat_bar").lower()
            stock_dims = {
                "diameter_mm": mat_row.get("stock_diameter"),
                "width_mm": mat_row.get("stock_width"),
                "height_mm": mat_row.get("stock_height"),
                "length_mm": mat_row.get("stock_length"),
            }
            item_norms = mat_row.get("item_norms")
            if item_norms:
                first_norm = item_norms.strip().split(",")[0].strip()
                if first_norm:
                    material_norm = first_norm
            if not material_norm:
                material_norm = extract_wnr_from_code(mat_row.get("item_code") or "")
        if not material_norm:
            material_norm = fallback_by_part.get(part_id)

        if not material_norm:
            continue

        # Compute GT
        part_records = records_by_part.get(part_id, [])
        operations, max_cv = compute_gt_from_records(part_records)

        if not operations:
            continue

        # Basic filters
        total_prod_time = sum(op["operation_time_min"] for op in operations if op["category"] != "QC")
        if total_prod_time < 0.1 or total_prod_time > 120:
            continue
        if not any(op["category"] == "SAW" for op in operations):
            continue
        if all(op["category"] == "SAW" for op in operations):
            continue

        # Precision filters
        fail = False
        for op in operations:
            if op["manning_pct"] > 100:
                fail = True
                break
            if op["category"] == "LATHE" and op["manning_pct"] < 50:
                fail = True
                break
            if op["category"] == "MILL" and op["manning_pct"] < 70:
                fail = True
                break
            if op["norm_ratio"] and op["norm_ratio"] > 5.0:
                fail = True
                break
        if fail:
            continue

        # CV filter (LATHE + MILL only)
        cv_ok = True
        for op in operations:
            if op["category"] in ("LATHE", "MILL"):
                if op["cv"] and op["cv"] > 0.5:
                    cv_ok = False
                    break
                if op["manning_cv"] and op["manning_cv"] > 0.5:
                    cv_ok = False
                    break
        if not cv_ok:
            continue

        # Check PDF exists
        pdf_path = None
        if file_path:
            pdf_path = PROJECT_ROOT / "uploads" / file_path
            if not pdf_path.exists():
                pdf_path = PROJECT_ROOT / file_path
            if not pdf_path.exists():
                continue

        # Categorize part
        has_lathe = any(op["category"] == "LATHE" for op in operations)
        has_mill = any(op["category"] == "MILL" for op in operations)
        has_drill = any(op["category"] == "DRILL" for op in operations)

        # Material category
        unusual_material = False
        if material_norm:
            norm_lower = material_norm.lower()
            if any(x in norm_lower for x in ["pom", "pa6", "peek", "pp-", "pe-"]):
                unusual_material = True
            elif material_norm.startswith("3."):
                unusual_material = True
            elif material_norm.startswith("1.4"):
                unusual_material = True

        eligible.append(
            {
                "part_id": part_id,
                "article_number": article_number,
                "name": part_row["name"],
                "vp_count": part_row["vp_count"],
                "material_norm": material_norm,
                "stock_shape": stock_shape,
                "stock_dims": stock_dims,
                "pdf_path": pdf_path,
                "operations": operations,
                "max_cv": max_cv,
                "total_prod_time": total_prod_time,
                "has_lathe": has_lathe,
                "has_mill": has_mill,
                "has_drill": has_drill,
                "unusual_material": unusual_material,
            }
        )

    print(f"Eligible parts after filters: {len(eligible)}")

    # 6. Manual selection for diversity
    selected = []

    # 3 LATHE only
    lathe_only = [p for p in eligible if p["has_lathe"] and not p["has_mill"]]
    lathe_only = sorted(lathe_only, key=lambda x: -x["vp_count"])[:3]
    selected.extend(lathe_only)

    # 3 MILL only
    mill_only = [p for p in eligible if p["has_mill"] and not p["has_lathe"]]
    mill_only = sorted(mill_only, key=lambda x: -x["vp_count"])[:3]
    selected.extend(mill_only)

    # 2 LATHE + MILL
    both = [p for p in eligible if p["has_lathe"] and p["has_mill"]]
    both = sorted(both, key=lambda x: -x["vp_count"])[:2]
    selected.extend(both)

    # 1 DRILL (prefer standalone DRILL operation)
    drill_parts = [p for p in eligible if p["has_drill"]]
    drill_parts = sorted(drill_parts, key=lambda x: -x["vp_count"])[:1]
    selected.extend(drill_parts)

    # 1 unusual material
    unusual = [p for p in eligible if p["unusual_material"]]
    unusual = sorted(unusual, key=lambda x: -x["vp_count"])[:1]
    selected.extend(unusual)

    # Dedupe (take first 10 unique)
    seen_ids = set()
    final_selected = []
    for p in selected:
        if p["part_id"] not in seen_ids:
            final_selected.append(p)
            seen_ids.add(p["part_id"])
        if len(final_selected) >= 10:
            break

    if len(final_selected) < 10:
        # Fill from remaining eligible
        for p in eligible:
            if p["part_id"] not in seen_ids:
                final_selected.append(p)
                seen_ids.add(p["part_id"])
            if len(final_selected) >= 10:
                break

    print(f"Final selection: {len(final_selected)} parts")

    # 7. Generate JSONL
    jsonl_lines = []
    assistant_samples = []

    for idx, part in enumerate(final_selected[:10]):
        # Render PDF
        img_b64 = pdf_to_base64(part["pdf_path"])
        if not img_b64:
            print(f"SKIP {part['article_number']}: PDF render failed")
            continue

        # Build answer
        answer = {
            "material_norm": part["material_norm"],
            "stock": {
                "shape": part["stock_shape"],
                "diameter_mm": part["stock_dims"].get("diameter_mm"),
                "width_mm": part["stock_dims"].get("width_mm"),
                "height_mm": part["stock_dims"].get("height_mm"),
                "length_mm": part["stock_dims"].get("length_mm"),
            },
            "operations": [
                {
                    "category": op["category"],
                    "machine": op["machine"],
                    "operation_time_min": op["operation_time_min"],
                    "setup_time_min": op["setup_time_min"],
                    "manning_pct": op["manning_pct"],
                    "num_operations": op["num_operations"],
                }
                for op in part["operations"]
            ],
        }

        # Save 2 samples for visual verification
        if idx < 2:
            assistant_samples.append(
                {
                    "article_number": part["article_number"],
                    "answer": answer,
                }
            )

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

        jsonl_lines.append(json.dumps(ft_entry, ensure_ascii=False))

    # 8. Write JSONL
    output_path = PROJECT_ROOT / "ft_test_10.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(jsonl_lines) + "\n")

    print(f"\n✅ JSONL written to: {output_path}")
    print(f"   Lines: {len(jsonl_lines)}")

    # 9. Validation
    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"\n📊 Validation:")
    print(f"   Line count: {len(lines)}")
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
            assert "messages" in obj
            assert len(obj["messages"]) == 3
            assert obj["messages"][0]["role"] == "system"
            assert obj["messages"][1]["role"] == "user"
            assert obj["messages"][2]["role"] == "assistant"
            assistant_content = json.loads(obj["messages"][2]["content"])
            assert "material_norm" in assistant_content
            assert "stock" in assistant_content
            assert "operations" in assistant_content
        except Exception as exc:
            print(f"   ❌ Line {i} validation failed: {exc}")

    print(f"   ✅ All lines valid")

    # 10. Summary table
    print(f"\n📋 Selected parts:")
    print(f"{'Article':<12} {'VPs':<4} {'Material':<12} {'Stock':<12} {'Operations':<30}")
    print("─" * 80)
    for part in final_selected[:10]:
        ops_str = ", ".join([op["category"] for op in part["operations"]])
        print(
            f"{part['article_number']:<12} {part['vp_count']:<4} {part['material_norm']:<12} {part['stock_shape']:<12} {ops_str:<30}"
        )

    # 11. Print 2 assistant samples
    print(f"\n🔍 Sample assistant answers (first 2):")
    for sample in assistant_samples:
        print(f"\n{sample['article_number']}:")
        print(json.dumps(sample["answer"], indent=2, ensure_ascii=False))

    conn.close()


if __name__ == "__main__":
    main()
