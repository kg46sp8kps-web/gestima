"""Test FT v2 prompt — Technology Builder from drawing (few-shot with images).

GT format: per machine category (SAW/LATHE/MILL/DRILL), operation_time + setup + manning.
Sends 6 example drawings as few-shot, then tests on 6 new parts.
Usage: python scripts/test_ft_v2_prompt.py
"""

import json
import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF
from openai import OpenAI
from app.config import settings

# ─── CONFIG ──────────────────────────────────────────────────────────────

MODEL = "gpt-4.1-2025-04-14"
MAX_IMAGE_DIMENSION = 4096
PROJECT_ROOT = Path(__file__).parent.parent

# ─── MATERIAL NORM ALIASES (from DB material_norms table) ─────────────
# Maps any known alias (W.Nr, EN/ISO, CSN, AISI) → canonical W.Nr
# Used for material matching: AI may return "X14CrMoS17" which = "1.4104"

def _load_material_aliases() -> dict:
    """Load material norm aliases from DB → {alias_lower: w_nr}."""
    import sqlite3
    db_path = PROJECT_ROOT / "gestima.db"
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT w_nr, en_iso, csn, aisi FROM material_norms WHERE deleted_at IS NULL").fetchall()
    conn.close()
    aliases = {}
    for w_nr, en_iso, csn, aisi in rows:
        w_lower = (w_nr or "").strip().lower()
        if w_lower:
            aliases[w_lower] = w_nr
        for alias in (en_iso, csn, aisi):
            a = (alias or "").strip().lower()
            if a:
                aliases[a] = w_nr
    return aliases

MATERIAL_ALIASES = _load_material_aliases()


def resolve_material_norm(raw: str) -> str | None:
    """Resolve any material designation to canonical W.Nr via DB aliases."""
    if not raw or raw == "?":
        return None
    raw_lower = raw.strip().lower()
    # Direct match
    if raw_lower in MATERIAL_ALIASES:
        return MATERIAL_ALIASES[raw_lower]
    # Partial match (e.g. "C45E" contains "C45")
    for alias, w_nr in MATERIAL_ALIASES.items():
        if alias in raw_lower or raw_lower in alias:
            return w_nr
    return None

# ─── SYSTEM PROMPT ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """Jsi CNC technolog. Analyzuj výrobní výkres a navrhni technologický postup.
Zakázková strojírenská výroba, malá firma. Časy jsou per kus v minutách.
Odpověz POUZE validním JSON.

MATERIÁL:
- Přečti materiál z rohového razítka výkresu (W.Nr / ČSN / EN norma).
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
- plate: šířka × výška × délka (deska, přířez)

STROJE:
- BOMAR STG240A (pásová pila, vždy první operace)
- SMARTURN 160 (CNC soustruh ≤ø160mm)
- NLX 2000 (CNC soustruh, větší série, agresivnější podmínky)
- MASTURN 32 (CNC soustruh ≤ø320mm, velké díly)
- MCV 750 (CNC frézka 3-osá)
- MILLTAP 700 5AX (CNC frézka 5-osá, složitější tvary)
- TAJMAC H40 (CNC frézka 4-osá horizontální)
- VS20 (sloupová vrtačka — upíchnutí z druhé strany / odjehlení)
- MECHANIK (ruční práce — srážení, začištění)
- KONTROLA (výstupní kontrola)

PRAVIDLA:
- Strojní čas = čistý řez+posuvy per kus. NE setup, NE upínání.
- Jednoduché díly = málo operací. NEPŘIDÁVEJ zbytečné operace.
- Kooperace se NEPOČÍTÁ.
- Rotační díly ze soustruhu → téměř vždy následuje VS20 (upíchnutí z druhé strany, odjehlení).
- Více upnutí na frézce = více operací na tom samém stroji.

JSON formát:
{
  "material_norm": "1.0503",
  "stock": {"shape": "round_bar|flat_bar|square_bar|plate", "diameter_mm": null, "width_mm": null, "height_mm": null, "length_mm": null},
  "operations": [
    {"category": "SAW|LATHE|MILL|DRILL|MANUAL|QC", "machine": "...", "operation_time_min": 0.0, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1}
  ]
}"""

# ─── FEW-SHOT EXAMPLES (6: 3 ROT + 3 PRIZ) ─────────────────────────────

FEW_SHOT_EXAMPLES = {
    # ── ROT 1: Buchse ø9.8×8, automatová ocel, malý jednoduchý díl ──
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
    # ── ROT 2: Huelse ø18×27, automatová ocel, tolerance h9 → QC ──
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
    # ── ROT 3: Ring ø24.9×7, automatová ocel ──
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
    # ── PRIZ 1: Spannpratze, konstrukční ocel C45, tyč plochá ──
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
    # ── PRIZ 2: Platte Schlauchhalter, POM-C plast, deska, 4 upnutí → QC ──
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
    # ── PRIZ 3: Haltearm Kabelablage, hliník AlMg4.5Mn, deska litá → QC ──
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

# ─── TEST PARTS (5: 3 ROT + 2 PRIZ) ────────────────────────────────────
# GT loaded from data/ft_v2_ground_truth.json

TEST_ARTICLES = ["10070319", "10806334", "0341350", "0302361", "0343417", "0057224"]
TEST_PDFS = {
    "10070319": "uploads/parts/10529262/10070319_02.pdf",       # ROT: Buchse 35
    "10806334": "uploads/parts/10136679/10806334_02.pdf",       # ROT: Pressurering
    "0341350": "uploads/parts/10846271/0341350_000-betaserie.pdf",  # ROT: Zentrierhuelse
    "0302361": "uploads/parts/10049886/0302361_D00040920_000.pdf",  # PRIZ: Endplatte Kolben
    "0343417": "uploads/parts/10552324/0343417_D00108242_005.pdf",  # PRIZ: Halter Rastbolzen
    "0057224": "uploads/parts/10198908/0057224_50231_001.pdf",  # PRIZ: Anschlagplatte
}

# ─── HELPERS ─────────────────────────────────────────────────────────────

def pdf_to_base64(pdf_path: str) -> str:
    """Render PDF first page to base64 PNG."""
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


def build_few_shot_messages() -> list:
    """Build few-shot example messages: image → JSON answer pairs."""
    messages = []
    for article, example in FEW_SHOT_EXAMPLES.items():
        pdf_path = PROJECT_ROOT / example["pdf"]
        if not pdf_path.exists():
            print(f"  ⚠️  Few-shot PDF nenalezen: {pdf_path}")
            continue
        img_b64 = pdf_to_base64(str(pdf_path))
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"}},
                {"type": "text", "text": "Analyzuj výkres a navrhni technologický postup."},
            ],
        })
        messages.append({
            "role": "assistant",
            "content": json.dumps(example["answer"], ensure_ascii=False),
        })
    return messages


def call_gpt_fewshot(few_shot_msgs: list, test_image_b64: str) -> dict:
    """Call GPT-4.1 with few-shot examples + test drawing."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(few_shot_msgs)
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_b64}", "detail": "high"}},
            {"type": "text", "text": "Analyzuj výkres a navrhni technologický postup."},
        ],
    })

    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.2, max_tokens=2000,
    )
    raw = response.choices[0].message.content
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    usage = response.usage
    print(f"   Tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
    return json.loads(raw)


def compare(article: str, ai_result: dict, gt: dict):
    """Compare AI result with ground truth per machine category."""
    name = gt["name"]
    print(f"\n{'='*70}")
    print(f"  {article} — {name}")
    print(f"{'='*70}")

    # ── Material comparison (via DB alias resolution) ──
    gt_wnr = gt.get("material_norm", gt.get("material_w_nr", "?"))
    ai_raw = ai_result.get("material_norm", ai_result.get("material_w_nr", ai_result.get("material", "?")))

    # Resolve both through DB aliases to canonical W.Nr
    gt_resolved = resolve_material_norm(gt_wnr) or gt_wnr
    ai_resolved = resolve_material_norm(ai_raw) or ai_raw

    if gt_resolved and ai_resolved and gt_resolved == ai_resolved:
        wnr_match = "✅"
        match_detail = f"(={gt_resolved})" if ai_raw != gt_wnr else ""
    else:
        wnr_match = "❌"
        match_detail = f"(resolved: AI→{ai_resolved}, GT→{gt_resolved})" if ai_resolved != ai_raw else ""

    print(f"\n  MATERIÁL:  AI={ai_raw}  |  GT={gt_wnr}  {wnr_match} {match_detail}")

    # ── Stock comparison ──
    gt_stock = gt.get("stock", {})
    ai_stock = ai_result.get("stock", {})
    print(f"  POLOTOVAR: AI={ai_stock}  |  GT={gt_stock}")

    # Support both old "machines" key and new "operations" key in AI output and GT
    gt_ops = gt.get("operations", gt.get("machines", []))
    ai_ops = ai_result.get("operations", ai_result.get("machines", []))

    gt_by_cat = {m["category"]: m for m in gt_ops}
    ai_by_cat = {m["category"]: m for m in ai_ops}

    all_cats = sorted(set(list(gt_by_cat.keys()) + list(ai_by_cat.keys())),
                      key=lambda c: ["SAW","LATHE","MILL","DRILL","MANUAL","QC","OTHER"].index(c) if c in ["SAW","LATHE","MILL","DRILL","MANUAL","QC","OTHER"] else 99)

    print(f"\n  {'cat':<8} {'machine':<20} {'AI time':>8} {'GT time':>8} {'Δ':>7} {'AI stp':>7} {'GT stp':>7} {'AI mn':>6} {'GT mn':>6} {'AI #':>4} {'GT #':>4}")
    print(f"  {'-'*8} {'-'*20} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*6} {'-'*6} {'-'*4} {'-'*4}")

    ai_prod_total = 0
    gt_prod_total = 0
    ai_setup_total = 0
    gt_setup_total = 0

    for cat in all_cats:
        ai_m = ai_by_cat.get(cat)
        gt_m = gt_by_cat.get(cat)

        # Support both old and new key names
        ai_t = ai_m.get("operation_time_min", ai_m.get("total_time_min", 0)) if ai_m else 0
        gt_t = gt_m.get("operation_time_min", gt_m.get("total_time_min", 0)) if gt_m else 0
        ai_s = ai_m.get("setup_time_min", ai_m.get("total_setup_min", 0)) if ai_m else 0
        gt_s = gt_m.get("setup_time_min", gt_m.get("total_setup_min", 0)) if gt_m else 0
        ai_mn = ai_m.get("manning_pct", 100) if ai_m else 0
        gt_mn = gt_m.get("manning_pct", 100) if gt_m else 0
        ai_n = ai_m.get("num_operations", 0) if ai_m else 0
        gt_n = gt_m.get("num_operations", 0) if gt_m else 0
        machine = (ai_m or gt_m or {}).get("machine", "?")

        delta = ai_t - gt_t if gt_m else 0
        delta_str = f"{delta:+.2f}" if gt_m else "N/A"

        is_prod = cat not in ("QC",)
        marker = "" if ai_m and gt_m else (" ← MISS" if not ai_m else " ← EXTRA")

        if is_prod:
            ai_prod_total += ai_t
            gt_prod_total += gt_t
            ai_setup_total += ai_s
            gt_setup_total += gt_s

        print(f"  {cat:<8} {machine:<20} {ai_t:>8.2f} {gt_t:>8.2f} {delta_str:>7} {ai_s:>7.0f} {gt_s:>7.0f} {ai_mn:>6.0f} {gt_mn:>6.0f} {ai_n:>4} {gt_n:>4}{marker}")

    delta_total = ai_prod_total - gt_prod_total
    pct = (delta_total / gt_prod_total * 100) if gt_prod_total > 0 else 0

    print(f"\n  STROJNÍ ČAS: AI={ai_prod_total:.2f} | GT={gt_prod_total:.2f} | Δ={delta_total:+.2f} ({pct:+.0f}%)")
    print(f"  SETUP:       AI={ai_setup_total:.0f} | GT={gt_setup_total:.0f} | Δ={ai_setup_total - gt_setup_total:+.0f}")

    return {
        "article": article,
        "name": name,
        "ai_time": ai_prod_total,
        "gt_time": gt_prod_total,
        "delta_pct": pct,
        "ai_setup": ai_setup_total,
        "gt_setup": gt_setup_total,
        "wnr_ok": wnr_match == "✅",
    }


# ─── MAIN ────────────────────────────────────────────────────────────────

def main():
    print(f"Model: {MODEL}")
    print(f"Few-shot: 6 příkladů (3 ROT + 3 PRIZ) s obrázky výkresů")
    print(f"Test: {len(TEST_ARTICLES)} dílů\n")

    # Load ground truth
    gt_path = PROJECT_ROOT / "data" / "ft_v2_ground_truth.json"
    with open(gt_path) as f:
        all_gt = json.load(f)

    # Build few-shot messages
    print("📚 Načítám few-shot příklady...")
    t0 = time.time()
    few_shot_msgs = build_few_shot_messages()
    print(f"   {len(few_shot_msgs) // 2} příkladů načteno ({time.time() - t0:.1f}s)\n")

    results = []

    for article in TEST_ARTICLES:
        pdf_rel = TEST_PDFS[article]
        pdf_path = PROJECT_ROOT / pdf_rel
        gt = all_gt[article]

        if not pdf_path.exists():
            print(f"❌ PDF nenalezen: {pdf_path}")
            continue

        print(f"\n📐 {article} — {gt['name']} ({pdf_path.name})...")

        try:
            img_b64 = pdf_to_base64(str(pdf_path))
            print(f"   PNG: {len(img_b64) // 1024} KB")

            ai_result = call_gpt_fewshot(few_shot_msgs, img_b64)

            # Save raw
            out_dir = PROJECT_ROOT / "data"
            out_dir.mkdir(exist_ok=True)
            out_file = out_dir / f"ft_v2_test_{article}.json"
            with open(out_file, "w") as f:
                json.dump(ai_result, f, indent=2, ensure_ascii=False)

            r = compare(article, ai_result, gt)
            results.append(r)

        except Exception as e:
            print(f"❌ Chyba: {e}")
            import traceback
            traceback.print_exc()

    # ── Summary ──
    if results:
        print(f"\n\n{'='*70}")
        print(f"  CELKOVÉ SHRNUTÍ")
        print(f"{'='*70}")
        print(f"\n  {'art':<12} {'name':<30} {'AI time':>8} {'GT time':>8} {'Δ%':>7}  {'AI stp':>7} {'GT stp':>7}")
        print(f"  {'-'*12} {'-'*30} {'-'*8} {'-'*8} {'-'*7}  {'-'*7} {'-'*7}")

        tot_ai = tot_gt = tot_ai_s = tot_gt_s = 0
        for r in results:
            print(f"  {r['article']:<12} {r['name'][:30]:<30} {r['ai_time']:>8.2f} {r['gt_time']:>8.2f} {r['delta_pct']:>+6.0f}%  {r['ai_setup']:>7.0f} {r['gt_setup']:>7.0f}")
            tot_ai += r["ai_time"]
            tot_gt += r["gt_time"]
            tot_ai_s += r["ai_setup"]
            tot_gt_s += r["gt_setup"]

        delta_all = tot_ai - tot_gt
        pct_all = (delta_all / tot_gt * 100) if tot_gt > 0 else 0
        print(f"\n  CELKEM STROJNÍ: AI={tot_ai:.2f} | GT={tot_gt:.2f} | Δ={delta_all:+.2f} ({pct_all:+.0f}%)")
        print(f"  CELKEM SETUP:   AI={tot_ai_s:.0f} | GT={tot_gt_s:.0f}")
        avg_abs_pct = sum(abs(r["delta_pct"]) for r in results) / len(results)
        print(f"  MAPE (průměr |Δ%|): {avg_abs_pct:.0f}%")

        # ── Material accuracy ──
        wnr_ok = sum(1 for r in results if r.get("wnr_ok"))
        print(f"\n  MATERIÁL: material_norm správně {wnr_ok}/{len(results)}")


if __name__ == "__main__":
    main()
