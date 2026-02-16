"""OpenAI Vision - Prompts for single-call machining time estimation from PDF drawing image.

Single-call pipeline: image → full estimation including extraction + time.

Two prompt variants:
  - BASE: Full prompts with reference tables, calibration examples (for gpt-4o base model)
  - FT:   Compact prompts for fine-tuned model (tables learned from training data)
"""

from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# FINE-TUNED MODEL — compact prompts (tables/examples learned from training)
# ═══════════════════════════════════════════════════════════════════

OPENAI_FT_SYSTEM = """Jsi CNC technolog. Analyzuj výrobní výkres a odhadni produkční strojní čas.
POUZE produkční čas (spindle time): řezání, posuvy, rychloposuvy.
NE: upínání, kontrola, manipulace, seřízení.
Odpověz POUZE validním JSON."""


def build_openai_ft_prompt() -> str:
    """Compact user prompt for fine-tuned model.

    The fine-tuned model has reference tables, material multipliers,
    and calibration examples learned from 55 training examples.
    No need to repeat them in the prompt — just specify the task and JSON format.

    Returns:
        Compact prompt string with JSON format specification.
    """
    return """Analyzuj přiložený výrobní výkres. Urči typ dílu, materiál, rozměry, komplexitu a odhadni produkční strojní čas.

Odpověz v tomto JSON formátu:
{
  "part_type": "ROT|PRI|COMBINED",
  "complexity": "simple|medium|complex",
  "material_detected": "materiál z výkresu",
  "max_diameter_mm": null nebo číslo,
  "max_length_mm": číslo,
  "max_width_mm": null nebo číslo,
  "max_height_mm": null nebo číslo,
  "manufacturing_description": "stručný popis",
  "operations": ["operace1", "operace2"],
  "estimated_time_min": 12.5,
  "confidence": "high|medium|low",
  "reasoning": "stručný výpočet",
  "breakdown": [
    {"operation": "soustružení", "time_min": 9.0, "notes": "popis"}
  ]
}

estimated_time_min MUSÍ = SOUČET všech breakdown[].time_min."""


# ═══════════════════════════════════════════════════════════════════
# BASE MODEL — full prompts with reference tables and examples
# ═══════════════════════════════════════════════════════════════════

OPENAI_VISION_SYSTEM = """Jsi CNC technolog s 20 lety praxe v zakázkové strojírenské výrobě.
Tvůj úkol: podívej se na výrobní výkres a odhadni produkční strojní čas.

POSTUP:
1. Podívej se na výkres — urči typ dílu (ROT/PRI/COMBINED)
2. Přečti materiál z razítkového pole (Werkstoff, NENÍ Benennung!)
3. Urči celkové obalové rozměry (největší kóty na každou osu)
4. Odhadni komplexitu (simple/medium/complex) podle počtu prvků
5. Použij referenční tabulku pro odhad základního času
6. Koriguj materiálovým multiplikátorem
7. Přidej doplňkové časy (díry, závity, sražení)

DEFINICE TYPŮ:
- ROT: rotační díl (hřídel, čep, příruba na soustruhu) — dominantní ø rozměr
- PRI: prizmatický díl (deska, blok, skříň na frézce) — délka × šířka × výška
- COMBINED: rotační základ + frézované prvky (soustružení + frézování)

DEFINICE KOMPLEXITY:
- simple: ≤5 prvků, žádné H7/IT6 tolerance
- medium: 6-12 prvků NEBO H7 tolerance NEBO závity
- complex: 13+ prvků NEBO IT6 a přísnější NEBO Ra<0.8 NEBO 3D kontury

POUZE produkční strojní čas (spindle time):
- ANO: řezání, posuvy, rychloposuvy mezi řezy
- NE: upínání, kontrola, manipulace, seřízení, výměna nástrojů

PRAVIDLA:
- Piš POUZE to co VIDÍŠ na výkresu
- Materiál (Werkstoff) je JINÉ pole než Název dílu (Benennung)
- Celkový rozměr = NEJVĚTŠÍ kóta na danou osu, ne tolerovaný detail
- Díra ø uvnitř hranatého dílu NEZNAMENÁ že díl je rotační (ROT)

VŽDY odpovídej POUZE validním JSON, žádný markdown, žádný komentář."""


# ═══════════════════════════════════════════════════════════════════
# FEATURES EXTRACTION — feature-only prompt (no time estimation)
# ═══════════════════════════════════════════════════════════════════

OPENAI_FEATURES_SYSTEM = """Jsi CNC technolog-analytik. Analyzuj výrobní výkres a extrahuj KOMPLETNÍ seznam features.

ČTENÍ VÝKRESU — krok po kroku:

1. RAZÍTKO (title block):
   - Materiál = pole "Werkstoff" nebo "Material" (NE "Benennung")
   - PA6, PA66, POM = plast. Messing = mosaz. 1.43xx = nerez. Ck45 = ocel.
   - Číslo výkresu, název dílu, hmotnost (Weight/Gewicht)

2. TYP DÍLU:
   - ROT = rotační (hřídel, čep, příruba, disk) — alespoň 1 pohled s ø
   - PRI = prizmatický (deska, L-profil, blok) — L×W×H
   - COMBINED = ROT základ + frézované prvky (plošky, drážky), NEBO ROT díl s M× na čele

3. OBVODOVÉ KONTURY (NEJDŮLEŽITĚJŠÍ — řídí čas obrábění!):
   Pro ROT díly:
   - Projdi HLAVNÍ pohled ZLEVA DOPRAVA
   - KAŽDÝ průměrový stupeň = 1× outer_diameter s délkou: "ø60 h9 ×28mm"
   - Hřídel se 4 stupni = 4× outer_diameter (NE méně!)
   - MENŠÍ průměry NEPŘEHLÉDNI (ø10 h8 na konci hřídele = stále outer_diameter)
   Pro PRI díly (STEJNĚ DŮLEŽITÉ jako ROT kontury!):
   - Celkový obrys: přečti VNĚJŠÍ KONTURU dílu — L-profil, T-profil, schodovitý blok
   - Šikmé hrany na obrysu = taper nebo chamfer (šikmina po celé délce = taper)
   - Výřezy v obrysu = pocket (uzavřené) nebo slot (otevřené)
   - Stupňovitý profil = zapiš jako pocket nebo step
   - Zaoblení na vnějším profilu = radius (R15, R10 na obrysových přechodech)
   - SPOČÍTEJ všechny prvky na obrysu — frézování obrysu je hlavní čas u PRI dílů!

4. VNITŘNÍ PRVKY (POZORNĚ! inner_diameter je ČASTO PŘEHLÉDNUT):
   - Díra SKRZ materiál = through_hole (malé ø bez tolerance, např. ø8.5)
   - VELKÉ písmeno na ø = inner_diameter: H7, H6, H13, F8, P8, E9, Z9, R9
     Příklady: ø1.6 H13 = inner_diameter! ø6 P8 = inner_diameter! ø55 Z9 = inner_diameter!
   - malé písmeno na ø = outer_diameter: h7, h6, g7, j6, h8, h12
   - Velký vnitřní ø BEZ tolerance (ø39, ø46 průchozí otvor) = inner_diameter (NE through_hole!)
   - POZOR: kóta "1.6 H13" znamená průměr ø1.6 s tolerancí H13 → inner_diameter!
   - Zahloubení (stupňovaný otvor — malý ø + velký ø) = counterbore
   - Kapsy = obdélníkový výřez (i s plnými R na koncích). SPOČÍTEJ VŠECHNY!

5. ZÁVITY — POZOR na směr:
   - M× na vnějším ø hřídele nebo čepu = thread_external
   - M× v díře (otvor se závitem) = thread_internal
   - Jak poznat: pokud je M8 značka NA HŘÍDELI (vnější kontura) = external
   - Pokud je M5 značka V DÍŘE (vnitřní kontura nebo boční otvor) = internal
   - U COMBINED dílů: M× na konci rotační části (na ose dílu) = thread_external!
   - U COMBINED dílů: M× v bočním otvoru = thread_internal

6. SPECIÁLNÍ PRVKY:
   - DIN 509 = zápich (groove) — úzká drážka na přechodu průměrů
   - Řezy (A-A, B-B): hledej frézované plochy (flat), kapsy, vnitřní profily
   - Úhel na povrchu (10°, 34°) u ROT dílu = taper (kužel), NE chamfer!
   - Chamfer = POUZE sražení HRANY (1×45°, 2×45°)

7. ZNAČKY:
   - Ra 1.6, Rz 6.3 = drsnost → surface_finish
   - N7, N8, N9 = drsnost (starý ISO systém) → surface_finish
   - Šipka + rámek + číslo (↗ 0.02 A) = geometrická tolerance → tolerance_geometric
   - ±0.1, +0.3/0, -0.2 = rozměrová tolerance → tolerance_dimensional

8. POZNÁMKY:
   - "alle Kanten brechen", "ISO 13715" = edge_break
   - "Srazení hran bez údaju 1×15°" = edge_break
   - Weight / Gewicht = weight

Odpověz POUZE validním JSON."""


def build_features_prompt() -> str:
    """Build user prompt for features extraction (no time estimation).

    V4 prompt — improved PRI contour extraction, self-validation checklist,
    negative examples for common mistakes. Focus on time-relevant features.

    Returns:
        Formatted prompt string for feature-only extraction.
    """
    return """Analyzuj přiložený výrobní výkres. Extrahuj KAŽDÝ feature.

FORMÁT ODPOVĚDI:
{
  "drawing_number": "z razítka",
  "part_name": "z razítka",
  "part_type": "ROT|PRI|COMBINED",
  "material": {
    "designation": "přesně z výkresu",
    "standard": "norma (DIN, EN, W.Nr.)",
    "group": "ocel|nerez|hliník|mosaz|plast|titan|litina|měď"
  },
  "overall_dimensions": {
    "max_diameter_mm": null,
    "max_length_mm": null,
    "max_width_mm": null,
    "max_height_mm": null
  },
  "features": [
    {"type": "TYP", "count": N, "detail": "rozměry s délkou/hloubkou", "location": "kde"}
  ],
  "general_notes": ["poznámky z výkresu"],
  "feature_summary": {
    "total_features": 0,
    "holes_total": 0,
    "threads_total": 0,
    "tight_tolerances": 0,
    "surface_finish_count": 0
  }
}

══════════════════════════════════════════
FEATURE TYPY — ČASOVĚ RELEVANTNÍ (priorita!)
══════════════════════════════════════════

VNĚJŠÍ PRŮMĚRY (ROT — KAŽDÝ stupeň zvlášť, VŽDY s délkou!):
  outer_diameter — "ø60 h9 ×28mm" nebo "ø25 ×36mm"
  (malé písmeno h7/g6/j6/h8/h12 = VNĚJŠÍ)

VNITŘNÍ PRŮMĚRY:
  inner_diameter — vnitřní vyvrtání/vysoustružení: "ø46 průchozí", "ø21 H7", "ø6 P8"
  (VELKÉ písmeno H7/H6/H13/F8/E9/P8/Z9/R9 = VNITŘNÍ)
  POZOR: velký vnitřní ø BEZ tolerance (ø39, ø46) = TAKÉ inner_diameter!

DÍRY:
  through_hole — průchozí díra: "ø8.5" nebo "4× ø5.3"
  blind_hole — slepá díra: "ø6 hloubka 15mm"
  counterbore — zahloubení: "ø5.3/ø9.4 ×5.5mm"
  countersink — kuželové sražení: "90° ø10"
  reamed_hole — přesná díra H7: "ø10 H7"

ZÁVITY:
  thread_external — na vnějším ø hřídele: "M8 ×18mm" nebo "M6"
  thread_internal — v díře: "4× M5 hloubka 10mm"

KONTURY:
  chamfer — sražení HRANY: "1×45°" (ne kužel povrchu!)
  radius — rádius: "R1", "R15 na obrysovém přechodu", "Kugel R193 -0.05"
  groove — zápich: "DIN 509-E0.6×0.3" nebo "3×1.5mm"
  pocket — kapsa (uzavřený výřez s dnem): "80×22×3.4mm, 3× paralelní"
  slot — průchozí drážka (otevřená): "8×40mm"
  keyway — drážka pro pero: "6×3.5×20mm"
  flat — frézovaná plocha na ROT dílu (z řezu A-A!): "šířka 14mm ×délka"
  taper — kuželový povrch: "34° kužel" nebo "10° úhel" (NE chamfer!)
  knurling — vroubkování: "RAA 0.8"

══════════════════════════════════════════
FEATURE TYPY — INFORMAČNÍ (zapiš ale neřídí čas)
══════════════════════════════════════════

KVALITA:
  surface_finish — "Ra 1.6" nebo "Rz 6.3" nebo "N7"
  tolerance_dimensional — "ø60 h9" nebo "36 ±0.1"
  tolerance_geometric — "házení 0.02 k A"
  general_tolerance — "ISO 2768-mK"

INFO:
  material, edge_break, deburr, weight, drawing_note

═══ PŘÍKLAD 1 — ROT stupňovaná hřídel (11SMnPb30+C) ═══
4 průměry, 2 závity (M8 external + M6 external), zápich, frézovaná plocha:
{
  "features": [
    {"type": "outer_diameter", "count": 1, "detail": "ø25 ×36mm", "location": "pravá strana"},
    {"type": "outer_diameter", "count": 1, "detail": "ø20 j6 ×79mm", "location": "hlavní stupeň"},
    {"type": "outer_diameter", "count": 1, "detail": "ø18 h8 ×22mm", "location": "za zápichem"},
    {"type": "outer_diameter", "count": 1, "detail": "ø10 h8 ×(25)mm", "location": "levý konec"},
    {"type": "inner_diameter", "count": 1, "detail": "ø6 P8 průchozí", "location": "centrální"},
    {"type": "thread_external", "count": 1, "detail": "M8 ×3.5mm", "location": "levý konec"},
    {"type": "thread_external", "count": 1, "detail": "M6 ×15mm", "location": "pravý konec"},
    {"type": "groove", "count": 1, "detail": "DIN 509-E0.6×0.3", "location": "ø20→ø18"},
    {"type": "flat", "count": 1, "detail": "šířka 14mm ×18mm (řez A-A)", "location": "na ø20"},
    {"type": "chamfer", "count": 2, "detail": "1×45°", "location": "oba konce"},
    {"type": "chamfer", "count": 1, "detail": "0.3×45°", "location": "pravý konec"},
    {"type": "surface_finish", "count": 2, "detail": "Rz 10"},
    {"type": "surface_finish", "count": 1, "detail": "Rz 25"},
    {"type": "tolerance_dimensional", "count": 1, "detail": "ø20 j6"},
    {"type": "tolerance_dimensional", "count": 1, "detail": "36 ±0.1"},
    {"type": "tolerance_geometric", "count": 2, "detail": "házení 0.04 k B"},
    {"type": "tolerance_geometric", "count": 1, "detail": "válcovitost 0.05 k A"},
    {"type": "general_tolerance", "count": 1, "detail": "ISO 2768-mK"},
    {"type": "edge_break", "count": 1, "detail": "ISO 13715"},
    {"type": "weight", "count": 1, "detail": "0.295 kg"}
  ]
}
Poznámka: M8 a M6 jsou OBA na vnější kontuře hřídele → thread_EXTERNAL (ne internal!)

═══ PŘÍKLAD 2 — COMBINED díl (náboj s kuželem) ═══
5 vnějších ø, 2 vnitřní ø, M8 external, 10° kužel:
{
  "features": [
    {"type": "outer_diameter", "count": 1, "detail": "ø52 ×13mm"},
    {"type": "outer_diameter", "count": 1, "detail": "ø44 ×17mm"},
    {"type": "outer_diameter", "count": 1, "detail": "ø28 h7 ×13.5mm"},
    {"type": "outer_diameter", "count": 1, "detail": "ø28 h6 ×18mm"},
    {"type": "outer_diameter", "count": 1, "detail": "ø22 h6 ×2.5mm"},
    {"type": "inner_diameter", "count": 1, "detail": "ø21 H7"},
    {"type": "inner_diameter", "count": 1, "detail": "ø17 F8"},
    {"type": "thread_external", "count": 1, "detail": "M8", "location": "levý konec"},
    {"type": "taper", "count": 1, "detail": "10° kužel"},
    {"type": "chamfer", "count": 1, "detail": "0.5×45°"},
    {"type": "radius", "count": 1, "detail": "R0.2"},
    {"type": "radius", "count": 1, "detail": "R0.6"},
    {"type": "surface_finish", "count": 1, "detail": "Rz 25"},
    {"type": "surface_finish", "count": 2, "detail": "Rz 6.3"},
    {"type": "tolerance_geometric", "count": 4, "detail": "házení 0.02 k A"},
    {"type": "general_tolerance", "count": 1, "detail": "ISO 2768-mK"},
    {"type": "edge_break", "count": 1, "detail": "1×15° sražení hran"},
    {"type": "weight", "count": 1, "detail": "0.26 kg"}
  ]
}

═══ PŘÍKLAD 3 — PRI díl (hliníkový hebel s kapsami) ═══
L-profil 165×73.5×15mm, 3 paralelní kapsy, zahloubení, rádiusy na obrysu:
{
  "features": [
    {"type": "through_hole", "count": 2, "detail": "ø5.3"},
    {"type": "counterbore", "count": 1, "detail": "ø5.3/ø9.4 ×5.5mm"},
    {"type": "pocket", "count": 3, "detail": "80×22×3.4mm paralelní"},
    {"type": "radius", "count": 2, "detail": "R15 na obrysovém přechodu"},
    {"type": "radius", "count": 1, "detail": "R7 na obrysovém přechodu"},
    {"type": "surface_finish", "count": 1, "detail": "Ra 3.2"},
    {"type": "tolerance_dimensional", "count": 1, "detail": "22 +0.2/-0.1"},
    {"type": "tolerance_dimensional", "count": 1, "detail": "3.4 ±0.1"},
    {"type": "general_tolerance", "count": 1, "detail": "ISO 2768-mH"},
    {"type": "drawing_note", "count": 1, "detail": "Nicht vermasste Radien R10"}
  ]
}
Poznámka: R15, R7 jsou na VNĚJŠÍM OBRYSU (frézování kontury) — zapiš JE!

══════════════════════════════════════════
ČASTÉ CHYBY — vyhni se jim!
══════════════════════════════════════════
❌ Velký vnitřní ø (ø39, ø46) zapsat jako through_hole → SPRÁVNĚ: inner_diameter
❌ M8 na konci COMBINED dílu → thread_internal. SPRÁVNĚ: je NA HŘÍDELI = thread_external
❌ Flat z řezu A-A přehlédnout → SPRÁVNĚ: VŽDY kontroluj řezy!
❌ outer_diameter bez délky: "ø60 h9" → SPRÁVNĚ: "ø60 h9 ×28mm"
❌ U PRI dílu zapomenout na obrysové rádiusy (R15, R10) → SPRÁVNĚ: jsou časově relevantní!
❌ Kapsy na PRI dílu — zapsat 1 místo 3 → SPRÁVNĚ: SPOČÍTEJ všechny viditelné

══════════════════════════════════════════
SELF-CHECK (zkontroluj PŘED odesláním!)
══════════════════════════════════════════
Pro ROT díly:
  □ Jsou VŠECHNY průměrové stupně jako outer_diameter? Spočítej je na výkresu!
  □ Má KAŽDÝ outer_diameter délku v detail stringu? (×28mm)
  □ Jsou vnitřní otvory s VELKÝM písmenem (H7,F8) jako inner_diameter?
  □ Kontroloval jsi řezy A-A, B-B? Neobsahují flat/pocket/keyway?
Pro PRI díly:
  □ Popsal jsi vnější obrys? (rádiusy na přechodech, šikminy, výřezy)
  □ Spočítal jsi VŠECHNY kapsy? (2, 3, 4 paralelní?)
  □ Jsou zahloubení jako counterbore (ne jako 2× through_hole)?
Pro VŠECHNY díly:
  □ Jsou závity M× správně external vs internal podle LOKACE?
  □ Jsou úhly na povrchu (10°, 34°) jako taper, NE chamfer?

KRITICKÁ PRAVIDLA:
1. KAŽDÝ průměrový stupeň = samostatný outer_diameter (i malé ø na konci!)
2. Závit M× NA HŘÍDELI = thread_external. M× V DÍŘE = thread_internal
3. Úhel na povrchu (10°, 34°) = taper, NE chamfer. Chamfer = POUZE sražení HRANY
4. Řez A-A/B-B: hledej flat, pocket, vnitřní profil — NEPŘEHLÉDNI
5. Kapsy: SPOČÍTEJ kolik jich vidíš (mohou být 2-3-4 paralelní)
6. Zahloubení: ø malý/ø velký = counterbore (NE dva through_hole)
7. VELKÉ písmeno = VNITŘNÍ (H7, H6, F8, P8). malé = VNĚJŠÍ (h7, g6, j6)
8. N7/N8/N9 = drsnost (surface_finish), NE tolerance
9. Hmotnost, edge_break, poznámky — ZAPIŠ i tyto info features
10. overall_dimensions = OBALOVÉ rozměry celého dílu
11. PRI obrysové rádiusy (R15, R10, R7) = radius features — jsou časově relevantní!"""


# ═══════════════════════════════════════════════════════════════════
# BASE MODEL — full prompts with reference tables and examples
# ═══════════════════════════════════════════════════════════════════


def build_openai_vision_prompt(
    similar_parts: Optional[list] = None,
) -> str:
    """Build user prompt for OpenAI single-call vision estimation.

    Model extracts everything itself from the image (part type, dimensions, operations, time).

    Args:
        similar_parts: Optional list of similar parts from DB (for calibration context)

    Returns:
        Formatted prompt string with reference tables and calibration examples
    """

    similar_parts_text = ""
    if similar_parts:
        parts_lines = []
        for i, sp in enumerate(similar_parts, 1):
            dims = ""
            if sp.get("max_diameter_mm"):
                dims = f"ø{sp['max_diameter_mm']:.0f}×{sp.get('max_length_mm', 0):.0f}mm"
            elif sp.get("max_length_mm"):
                dims = f"{sp['max_length_mm']:.0f}mm"
            parts_lines.append(
                f"  #{i} (podobnost {sp['similarity_score']:.0%}): "
                f"{sp['pdf_filename']}, {sp['part_type']}, {sp['complexity']}, "
                f"{dims}, Reálný čas: {sp['actual_time_min']:.0f} min"
            )
        similar_parts_text = "\n".join(parts_lines)
    else:
        similar_parts_text = "  Žádné podobné díly v databázi (cold start)."

    return f"""Podívej se na přiložený výrobní výkres a odhadni produkční strojní čas.

═══════════════════════════════════════════════════════
MATERIÁLOVÉ MULTIPLIKÁTORY (založené na reálných řezných datech)
═══════════════════════════════════════════════════════
Hodnoty vychází z reálných MRR (Material Removal Rate) a řezných rychlostí:

  Materiál         | MRR cm³/min | Vc m/min | Multiplikátor
  Hliník (Al)      |    800      |   350    |  ×0.40
  Plast (POM,PA)   |   1200      |   400    |  ×0.30
  Mosaz / Bronz    |    650      |   250    |  ×0.50
  Měď (Cu)         |    500      |   200    |  ×0.55
  Litina           |    200      |   150    |  ×0.80
  Ocel automat.    |    300      |   220    |  ×0.85
  Ocel konstr.     |    250      |   180    |  ×1.00 (baseline)
  Ocel legovaná    |    180      |   160    |  ×1.20
  Nerez (1.43xx)   |    150      |   140    |  ×1.20
  Nástrojová ocel  |    120      |   120    |  ×1.50
  Titan            |     80      |    60    |  ×2.00

POZOR k multiplikátorům:
- Multiplikátor platí POUZE na řezný čas (aktivní záběr).
- Neproduktivní časy (rychloposuvy, přejezdy, polohování) jsou STEJNÉ pro všechny materiály.
- U JEDNODUCHÝCH dílů (málo záběrů) je neproduktivní čas velká část → reálný dopad materiálu je MENŠÍ.
- Příklad: nerez simple díl — neříkej "×1.20 na celý čas", ale přidej jen 10-20% na řezný čas.

═══════════════════════════════════════════════════════
REFERENČNÍ TABULKA — STROJNÍ ČASY PRO OCEL (×1.00)
═══════════════════════════════════════════════════════
FRÉZOVANÉ DÍLY (PRI):
  Triviální díl (≤3 kontury, žádné díry/závity): 0.3–1.0 min
  Malá destička (do 100×50×10mm, simple):      1–3 min
  Malá destička (do 100×50×10mm, medium):       3–6 min
  Střední díl (do 200×100×30mm, simple):        4–8 min
  Střední díl (do 200×100×30mm, medium):        6–12 min
  Střední díl (do 200×100×30mm, complex):      10–25 min
  Velký díl (300+mm, simple):                   8–15 min
  Velký díl (300+mm, medium):                  12–30 min
  Velký díl (300+mm, complex):                 25–60 min

SOUSTRUŽENÉ DÍLY (ROT):
  Triviální díl (≤3 kontury, žádné díry/závity): 0.3–1.0 min
  Malý čep (do ø30×50mm, simple):               1–3 min
  Malý čep (do ø30×50mm, medium):               3–6 min
  Střední hřídel (do ø80×200mm, simple):        3–8 min
  Střední hřídel (do ø80×200mm, medium):        6–15 min
  Střední hřídel (do ø80×200mm, complex):      10–25 min
  Velká hřídel (ø100+, 300+mm, simple):        10–20 min
  Velká hřídel (ø100+, 300+mm, medium):        15–35 min
  Velká hřídel (ø100+, 300+mm, complex):       25–60 min

COMBINED DÍLY (ROT + frézování):
  Malý (do ø60×30mm, simple):                   2–4 min
  Malý (do ø60×30mm, medium):                   4–8 min
  Střední (do ø100×80mm, medium):               8–18 min
  Velký (ø100+, complex):                      15–40 min

DOPLŇKOVÉ ČASY (ocel — TAKY násob multiplikátorem):
  1 díra průchozí (bez závitu):                  0.2–0.3 min
  1 díra + závit M3–M8:                          0.3–0.6 min
  1 díra H7 (vystružování):                      0.4–0.8 min
  1 sražení hrany:                               0.05–0.15 min
  1 kapsa/drážka:                                0.5–2.0 min

═══════════════════════════════════════════════════════
PODOBNÉ DÍLY Z DATABÁZE (reálné výrobní časy)
═══════════════════════════════════════════════════════
{similar_parts_text}

═══════════════════════════════════════════════════════
KALIBRAČNÍ PŘÍKLADY (reálná výroba, ověřené časy)
═══════════════════════════════════════════════════════
Příklad 1: COMBINED ø59×21mm, EN AW-6082 T6 (hliník), medium
  → Reálný čas: 3 min (soustružení + vystružování + 3× závit M6)
  Postup: COMBINED malý medium 4-8 min × 0.40 (Al) = 1.6-3.2 min základ
  + vystružování + 3× M6 závity → celkem ~3 min

Příklad 2: PRI 165×73.5×15mm, AlMg4.5Mn (hliník), medium, 5 děr + závity
  → Reálný čas: max 10 min
  Postup: střední díl medium 6-12 min × 0.40 = 2.4-4.8 min
  + 5 děr/závitů ~2 min × 0.40 = 0.8 min
  + L-profil s výřezem → celkem ~8-10 min

Příklad 3: PRI 85×70×55mm, EN AW-Al Si MgMn (hliník), medium
  → Reálný čas: 10-15 min
  Postup: střední díl medium 6-12 min × 0.40 = 2.4-4.8 min
  + hloubka 55mm = víc záběrů → ×1.5 = 3.6-7.2 min
  + otvory/kapsy → celkem 10-14 min

Příklad 4: ROT malý, 1.4305 (nerez), simple — jen vnější kontury, žádné díry/závity
  → Reálný čas: max 1 min
  Postup: triviální díl 0.3-1.0 min základ. Nerez ×1.20 ale jen na řezný čas
  (řezný čas ~0.3 min, neproduktivní ~0.5 min) → 0.3×1.20 + 0.5 = 0.86 min → ~1 min

Příklad 5: ROT malý, 1.4305 (nerez), simple — čep s pár záběry a sražením
  → Reálný čas: 1-2 min
  Postup: malý čep simple → základ 1.5 min.
  Řezný podíl ~60% = 0.9 min × 1.20 + neproduktivní 0.6 min = 1.68 min → ~1.7 min

Příklad 6: ROT střední, 1.4305 (nerez), medium — hřídel se zápichy
  → Reálný čas: 5-8 min
  Postup: střední hřídel medium → základ 6 min.
  Řezný podíl ~70% = 4.2 min × 1.20 + neproduktivní 1.8 min = 6.84 min → ~7 min

═══════════════════════════════════════════════════════
POSTUP ODHADU
═══════════════════════════════════════════════════════
1. Z výkresu urči: typ dílu, materiál, rozměry, komplexitu
2. SPOČÍTEJ PRVKY: kolik kontur/záběrů, kolik děr, kolik závitů?
3. Pokud ≤3 kontury a žádné díry/závity → TRIVIÁLNÍ díl (0.3-1.0 min pro ocel)
4. Jinak: najdi odpovídající řádek v referenční tabulce → vezmi DOLNÍ TŘETINU rozsahu
5. Urči materiálový multiplikátor podle materiálu
6. VYNÁSOB základní čas multiplikátorem
7. Přidej doplňkové časy (díry, závity...) — TAKY vynásobené multiplikátorem
8. Sečti → výsledek
POZOR: Multiplikátor aplikuj POUZE na řezný čas, ne na celkový!
U jednoduchých dílů je většina času neproduktivní → multiplikátor má malý dopad.

═══════════════════════════════════════════════════════
KRITICKÁ PRAVIDLA
═══════════════════════════════════════════════════════
1. estimated_time_min MUSÍ = SOUČET všech breakdown[].time_min
2. Každý breakdown[].time_min UŽ OBSAHUJE materiálový multiplikátor
3. V reasoning ukaž KONKRÉTNÍ výpočet s multiplikátorem
4. Confidence:
   - "high": podobný díl ±20% rozměrů
   - "medium": cold start, jasný díl v referenční tabulce
   - "low": neznámé rozměry, neobvyklý díl

═══════════════════════════════════════════════════════
ODPOVĚĎ — PŘESNĚ tento JSON formát:
═══════════════════════════════════════════════════════
{{
  "part_type": "ROT|PRI|COMBINED",
  "complexity": "simple|medium|complex",
  "material_detected": "materiál z výkresu",
  "max_diameter_mm": null nebo číslo (pro ROT/COMBINED),
  "max_length_mm": číslo,
  "max_width_mm": null nebo číslo (pro PRI),
  "max_height_mm": null nebo číslo (pro PRI),
  "manufacturing_description": "stručný popis co se obrábí",
  "operations": ["operace1", "operace2"],
  "estimated_time_min": 12.5,
  "confidence": "medium",
  "reasoning": "ROT ø80×150mm ocel. Ref: střední hřídel medium 6-15 min, dolní třetina=9min × 1.00=9.0. Díry: 2×0.3=0.6. Závity: 1×0.5=0.5. Celkem=9.0+0.6+0.5=10.1 min",
  "breakdown": [
    {{"operation": "soustružení", "time_min": 9.0, "notes": "základ 9 min ocel × 1.00"}},
    {{"operation": "vrtání", "time_min": 0.6, "notes": "2 díry × 0.3 min"}},
    {{"operation": "závitování", "time_min": 0.5, "notes": "1× M8"}}
  ]
}}

KRITICKÉ: Výše je POUZE ukázka formátu. Analyzuj PŘILOŽENÝ výkres a vypočítej SKUTEČNÝ čas!"""
