"""
STEP + PDF Parser using Claude API — v2.0 (Generalized Manufacturing Prompt)

Combines STEP geometry (precise) with PDF annotations (context)
for maximum accuracy in feature recognition.

Architecture:
- STEP features (parsed internally) → structured summary for Claude
- PDF document → Claude extracts annotations and tolerances
- Merge → Correlates STEP dimensions with PDF callouts
- Output → Hierarchical operations with GESTIMA FeatureType enum values

v2.0 Changes:
- Prompt rewritten to cover ALL part types (turning, milling, combined)
- Claude outputs our exact FeatureType enum values
- Material group mapping to 8-digit internal codes
- Operation decomposition rules (H7→ream, <5mm→center drill, etc.)
- Prismatic profile_geometry support

Token optimization:
- Do NOT send raw STEP text (saves ~8K tokens)
- Send only parsed feature summary (~200 tokens)
- PDF trimmed to first 2 pages (saves ~90% tokens on multi-page PDFs)

Model: Claude Sonnet 4.5 (~38s per 1-page PDF, ~3K input + ~3K output tokens)
"""

import asyncio
import base64
import io
import json
import logging
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic, RateLimitError

from app.services.claude_utils import parse_claude_json_response

logger = logging.getLogger(__name__)

# Retry config for rate limits
MAX_RETRIES = 2
RETRY_BASE_DELAY = 15  # seconds

# Max PDF pages to send to Claude (technical drawings are 1-2 pages)
MAX_PDF_PAGES = 2

# Model selection
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


# ====================================================================
# MANUFACTURING ANALYSIS PROMPT v2.0
# ====================================================================
# Tento prompt je JÁDRO celého systému Feature Recognition.
# Každá změna musí být testována na reálných dílech.
#
# Principy:
# 1. Claude dostane PŘESNÉ názvy FeatureType z našeho enumu
# 2. Výstup se mapuje přímo na Part → Operation → Feature model
# 3. Pokrývá rotační (soustružení) i prismatické (frézování) díly
# 4. Obsahuje pravidla operační dekompozice z praxe
# 5. Materiálové skupiny s interními 8-digit kódy
# ====================================================================

MANUFACTURING_RULES = """MANUFACTURING ANALYSIS RULES:

=== FEATURE TYPES (použij PŘESNĚ tyto hodnoty v poli "feature_type") ===

SOUSTRUŽENÍ:
  face         Zarovnání čela (from_diameter, depth)
  od_rough     Vnější hrubování (from_diameter→to_diameter, length)
  od_finish    Vnější dokončení (from_diameter→to_diameter, length)
  id_rough     Vnitřní hrubování (from_diameter→to_diameter, length)
  id_finish    Vnitřní dokončení (from_diameter→to_diameter, length)
  bore         Vyvrtávání (from_diameter→to_diameter, length)
  thread_od    Vnější závit na soustruhu (from_diameter, length, thread_pitch)
  thread_id    Vnitřní závit na soustruhu (from_diameter, length, thread_pitch)
  groove_od    Vnější zápich (from_diameter→to_diameter, width)
  groove_id    Vnitřní zápich (from_diameter→to_diameter, width)
  groove_face  Čelní zápich (width, depth)
  parting      Upíchnutí (from_diameter, blade_width)
  chamfer      Sražení hrany (width)
  radius       Zaoblení (corner_radius)
  knurl        Vroubkování (from_diameter, length)

VRTÁNÍ:
  center_drill Navrtání (to_diameter, depth)
  drill        Vrtání (to_diameter, depth)
  drill_deep   Hluboké vrtání >4×Ø (to_diameter, depth)
  ream         Vystružování H7/H6 (to_diameter, depth)
  tap          Závitování závitníkem (to_diameter, depth, thread_pitch)

FRÉZOVÁNÍ:
  mill_face        Frézování plochy (length, pocket_width, depth)
  mill_shoulder    Frézování osazení (length, depth)
  mill_pocket      Obdélníková kapsa (pocket_length, pocket_width, depth, corner_radius)
  mill_pocket_round Kruhová kapsa (to_diameter, depth)
  mill_slot        Drážka (length, width, depth)
  mill_keyway      Drážka pro pero (length, width, depth)
  mill_contour_od  Vnější obrys (length, depth)
  mill_contour_id  Vnitřní obrys (length, depth)
  mill_3d          3D frézování (length, depth)
  mill_drill       Vrtání na frézce (to_diameter, depth, count)
  mill_drill_deep  Hluboké vrtání na frézce (to_diameter, depth)
  mill_ream        Vystružování na frézce (to_diameter, depth)
  mill_tap         Závitování na frézce (to_diameter, depth, thread_pitch)
  mill_thread      Frézování závitu (to_diameter, depth, thread_pitch)
  mill_chamfer     Sražení na frézce (width)
  mill_deburr      Odjehlení na frézce
  mill_engrave     Gravírování

LIVE TOOLING (na soustruhu s poháněnými nástroji):
  lt_drill         Příčné vrtání (to_diameter, depth, count)
  lt_drill_axial   Axiální vrtání (to_diameter, depth, count)
  lt_tap           Příčné závitování (to_diameter, depth, thread_pitch)
  lt_flat          Frézování plošky (length, width, depth)
  lt_slot          Drážka na soustruhu (length, width, depth)

BROUŠENÍ:
  grind_od     Broušení vnější (from_diameter→to_diameter, length)
  grind_id     Broušení vnitřní (from_diameter→to_diameter, length)
  grind_face   Broušení plochy (from_diameter, depth)

DOKONČENÍ:
  deburr_manual Ruční odjehlení
  wash          Mytí
  inspect       Kontrola

=== NÁSTROJE (tool_number) ===

Každý feature MUSÍ mít přiřazený tool_number (T01, T02...).
Jeden nástroj dělá VÍCE features! Příklady:

SOUSTRUŽENÍ typické nástroje:
  T01 = CNMG hrubovací nůž → face, od_rough
  T02 = DNMG dokončovací nůž → od_finish, chamfer (vnější), radius, kužel
  T03 = Vnitřní hrubovací tyč → id_rough
  T04 = Vnitřní dokončovací tyč → id_finish, chamfer (vnitřní)
  T05 = Závitový nůž → thread_od
  T06 = Zapichovací nůž → groove_od, parting
  T07 = Vrták → center_drill, drill, drill_deep
  T08 = Výstružník → ream

FRÉZOVÁNÍ typické nástroje:
  T01 = Čelní fréza → mill_face
  T02 = Stopková fréza → mill_pocket, mill_slot, mill_contour_od/id
  T03 = Vrták → mill_drill
  T04 = Závitník → mill_tap
  T05 = Srážecí fréza → mill_chamfer

PRAVIDLA:
- Čísla nástrojů JSOU UNIKÁTNÍ v rámci celého dílu (ne jen operace!)
- Pokud jeden nástroj dělá 5 features, všech 5 má STEJNÝ tool_number
- tool_name = CZ popis nástroje (např. "CNMG hrubovací", "Vrták Ø18", "Výstružník Ø19 H7")
- REÁLNÝ díl má typicky 6-12 nástrojů

=== DEKOMPOZICE (KRITICKÉ - tady se dělají chyby!) ===

1. TOLERANCE H7/H6/H8 → VŽDY dvě operace:
   a) drill/bore (podměrný Ø, např. Ø18.5 pro H7 Ø19)
   b) ream (přesný Ø s tolerancí)

2. DÍRA Ø<5mm → VŽDY:
   a) center_drill (Ø3-4mm, hloubka 3-5mm)
   b) drill (požadovaný Ø)

3. HLUBOKÁ DÍRA (hloubka > 4× průměr):
   → Použij drill_deep místo drill (jiný cyklus, vyklápění)

4. ZÁVIT v díře → VŽDY sekvence:
   a) center_drill (pokud Ø<5mm)
   b) drill (jádrový Ø závitu, např. Ø6.8 pro M8)
   c) chamfer (náběh závitu)
   d) tap (závitování)

5. VNĚJŠÍ ZÁVIT na soustruhu:
   a) od_rough/od_finish (průměr závitu)
   b) groove_od (výběh závitu, pokud je)
   c) thread_od (řezání závitu)

6. SOUSTRUŽENÝ DÍL - typické pořadí:
   face → od_rough → od_finish → id_rough → id_finish → groove → thread → chamfer → parting

7. FRÉZOVANÝ DÍL - typické pořadí:
   mill_face → mill_pocket → mill_slot → mill_drill → mill_tap → mill_chamfer

8. POVRCH Ra<1.6μm → vyžaduje finish pass (od_finish/id_finish)
   POVRCH Ra<0.4μm → vyžaduje broušení (grind_od/grind_id)

9. TOLERANCE ≤ IT6 → vyžaduje broušení po soustružení

10. ZKOSENÍ = vždy samostatná operace chamfer (ne součást hrubování)

=== MATERIÁLOVÉ SKUPINY (8-digit interní kódy) ===

20910000=Hliník      20910001=Měď         20910002=Mosaz
20910003=Ocel auto   20910004=Ocel konstr  20910005=Ocel legov
20910006=Ocel nástr  20910007=Nerez        20910008=Plasty

W.Nr. mapování: 1.0x/1.1x→20910004, 1.2x→20910006, 1.4x→20910007,
1.5x-1.7x→20910005, 1.07/1.08→20910003, 3.x→20910000, 2.x→20910001/02

=== PROFILE_GEOMETRY (POINT-BASED CONTOUR) ===

Profil dílu se definuje jako SEZNAM BODŮ kontury (polyline), NE jako obdélníkové sekce!

ROTAČNÍ DÍL (type="rotational"):
  outer_contour = body VNĚJŠÍHO obrysu od levého čela doprava: [{r, z}]
    - r = poloměr od osy rotace (v mm)
    - z = pozice podél osy (0 = levé čelo, kladné doprava)
    - Body MUSÍ jít ZLEVA DOPRAVA (z rostoucí)
    - PRVNÍ bod: (r=0, z=0) na ose vlevo
    - POSLEDNÍ bod: (r=0, z=total_length) na ose vpravo
    - Kužely = lineární interpolace mezi body s různým r
    - Zaoblení R = přidat 2-3 mezilehlé body na oblouku
    - Zkosení (chamfer) = dva body s Δr a Δz
  inner_contour = body VNITŘNÍHO obrysu (díry, vývrtky): [{r, z}]
    - POUZE pokud existuje vnitřní dutina/díra
    - Body zleva doprava, r = poloměr díry od osy
    - Průchozí díra: konstantní r po celé délce
    - Stupňovitá díra: r se mění skokem
    - Slepá díra: ends before total_length
  holes = příčné/axiální díry mimo hlavní osu: [{diameter, depth, position: {axis, offset}}]
    - axis: "radial"|"axial", offset = vzdálenost od osy

Příklad pro hřídel Ø30 s přírubou Ø55 a dírou Ø19:
  outer_contour: [
    {"r": 0, "z": 0},
    {"r": 14, "z": 0},         // čelo (chamfer start)
    {"r": 15, "z": 1.5},       // chamfer end → Ø30 shaft
    {"r": 15, "z": 78.5},      // shaft end
    {"r": 14.2, "z": 79.8},    // cone 31°
    {"r": 13.5, "z": 80.6},    // R1 fillet → Ø27
    {"r": 13.5, "z": 82.4},    // Ø27 section end
    {"r": 14.1, "z": 83.1},    // R1 fillet
    {"r": 26.0, "z": 84.8},    // cone 82°
    {"r": 27.5, "z": 85.3},    // flange Ø55
    {"r": 27.5, "z": 89},      // bottom face
    {"r": 0, "z": 89}          // osa vpravo
  ]
  inner_contour: [
    {"r": 9.5, "z": 0},        // Ø19 through-bore start
    {"r": 9.5, "z": 89}        // Ø19 through-bore end
  ]

PRISMATICKÝ DÍL (type="prismatic"):
  bounding_box: {length, width, height}
  outer_contour = 2D obrys shora (XY): [{x, y}] — uzavřený polygon
  pockets = kapsy: [{contour: [{x,y}], depth}]
  holes = díry: [{x, y, diameter, depth}]

DŮLEŽITÉ pro profile_geometry:
- Čím VÍCE bodů, tím přesnější kontura (kužely, filety, chamfery)
- Pro zaoblení R použij minimálně 3 body na oblouku
- VŽDY začínej a končí na ose (r=0) pro rotační díly
- NIKDY nepoužívej obdélníkové "sections" — pouze body!

=== KALIBRACE PROFILE_GEOMETRY ===

STEP parser poskytuje PŘESNÉ průměry z 3D modelu. POVINNĚ je použij:
1. outer_contour MUSÍ obsahovat KAŽDÝ unikátní průměr ze STEP features
2. max(r) v outer_contour × 2 MUSÍ == max diameter ze STEP
3. Pokud STEP říká Ø30 a Ø55, kontura MUSÍ obsahovat body s r=15 a r=27.5
4. Axiální pozice (z) čti z PDF výkresu, ale průměry (r) VŽDY ze STEP!
5. total_length MUSÍ odpovídat celkové délce dílu z výkresu
6. inner_contour poloměr MUSÍ odpovídat STEP dírovým průměrům

KONTROLA (Claude si musí ověřit před odesláním):
- [ ] Všechny STEP průměry jsou v outer_contour nebo inner_contour
- [ ] max_diameter == max STEP diameter
- [ ] outer_contour začíná (r=0, z=0) a končí (r=0, z=total_length)
- [ ] Žádné záporné hodnoty r nebo z"""


def _build_manufacturing_prompt(
    step_features: List[Dict],
    has_step: bool = True,
    has_pdf: bool = True,
) -> str:
    """
    Sestaví manufacturing analysis prompt pro Claude API.

    Prompt je modulární:
    - Základ: MANUFACTURING_RULES (feature types, dekompozice, materiály)
    - Kontext: STEP features (pokud dostupné)
    - Přesnost: STEP+PDF merge vs. PDF-only varování

    Args:
        step_features: Features extrahované STEP parserem
        has_step: True pokud máme STEP soubor
        has_pdf: True pokud máme PDF výkres
    """
    # STEP context
    step_section = ""
    if step_features and has_step:
        feature_lines = []
        for f in step_features:
            parts = [f"type={f['type']}"]
            if 'diameter' in f:
                parts.append(f"Ø{f['diameter']}")
            if 'radius' in f:
                parts.append(f"R{f['radius']}")
            if 'angle' in f:
                parts.append(f"{f['angle']}°")
            if 'entity_id' in f:
                parts.append(f"#{f['entity_id']}")
            feature_lines.append("  " + ", ".join(parts))

        # Add diameter summary for contour calibration
        unique_diameters = sorted(set(
            f['diameter'] for f in step_features if 'diameter' in f
        ))
        calibration_section = ""
        if unique_diameters:
            calibration_section = f"""

KALIBRAČNÍ PRŮMĚRY ze STEP (MUSÍ být v outer/inner_contour):
  Průměry: {', '.join(f'Ø{d}' for d in unique_diameters)}
  Max Ø: {max(unique_diameters)}
  Min Ø: {min(unique_diameters)}"""

        step_section = f"""
STEP PARSER ({len(step_features)} features — PŘESNÁ geometrie z 3D modelu):
{chr(10).join(feature_lines)}{calibration_section}

STEP = SOURCE OF TRUTH pro rozměry. PDF doplňuje tolerance, materiál, povrch."""

    elif not has_step and has_pdf:
        step_section = """
⚠️ POUZE PDF (žádný STEP model) → rozměry méně přesné!
Čti rozměry z výkresu, confidence MAX 0.80."""

    # Precision context
    if has_step and has_pdf:
        precision = "STEP+PDF: nejvyšší přesnost. STEP rozměry > PDF. Confidence až 0.95."
    elif has_step:
        precision = "Pouze STEP: přesné rozměry, ale chybí tolerance a materiál. Confidence 0.70."
    else:
        precision = "Pouze PDF: čti z výkresu, méně přesné. Confidence max 0.80."

    return f"""Jsi zkušený CNC technolog. Analyzuj díl a navrhni kompletní výrobní postup.

{precision}
{step_section}

{MANUFACTURING_RULES}

=== OUTPUT JSON ===

{{
  "part_type": "rotational|prismatic|combined",
  "material_group": "20910004",
  "material_spec": "1.1191 (C45)",
  "stock": {{"type": "bar|plate|forging", "diameter": 55, "length": 100}},
  "operations": [
    {{
      "setup_id": "OP10",
      "description": "Soustružení - přední strana",
      "seq": 10,
      "operation_category": "turning",
      "operation_type": "seřizovací",
      "machine_type": "lathe_3ax",
      "machine_name": "Haas ST-20",
      "features": [
        {{
          "feature_type": "face",
          "seq": 1,
          "from_diameter": 55,
          "depth": 2,
          "tool_number": 1,
          "tool_name": "CNMG hrubovací",
          "note": "Zarovnání čela"
        }},
        {{
          "feature_type": "od_rough",
          "seq": 2,
          "from_diameter": 55,
          "to_diameter": 40,
          "length": 30,
          "z_start": 0,
          "z_end": 30,
          "tool_number": 1,
          "tool_name": "CNMG hrubovací",
          "note": "Hrubování Ø55→Ø40"
        }},
        {{
          "feature_type": "od_finish",
          "seq": 3,
          "from_diameter": 41,
          "to_diameter": 40,
          "length": 30,
          "tool_number": 2,
          "tool_name": "DNMG dokončovací",
          "note": "Dokončení Ø40"
        }}
      ]
    }},
    {{
      "setup_id": "OP20",
      "description": "Soustružení - zadní strana",
      "seq": 20,
      "operation_category": "turning",
      "operation_type": "výrobní",
      "machine_type": "lathe_3ax",
      "machine_name": "Haas ST-20",
      "features": [
        {{
          "feature_type": "drill",
          "seq": 1,
          "to_diameter": 18.5,
          "depth": 89,
          "tool_number": 5,
          "tool_name": "Vrták Ø18.5",
          "note": "Pilot pro Ø19 H7"
        }},
        {{
          "feature_type": "ream",
          "seq": 2,
          "to_diameter": 19,
          "depth": 89,
          "tool_number": 6,
          "tool_name": "Výstružník Ø19 H7",
          "note": "Ø19 H7 průchozí"
        }}
      ]
    }}
  ],
  "metadata": {{
    "part_number": "...",
    "drawing_number": "...",
    "material": "1.1191 (C45)",
    "surface_treatment": "...",
    "tolerance_standard": "ISO 2768-m"
  }},
  "profile_geometry": {{
    "type": "rotational",
    "outer_contour": [
      {{"r": 0, "z": 0}},
      {{"r": 14, "z": 0}}, {{"r": 15, "z": 1.5}},
      {{"r": 15, "z": 40}},
      {{"r": 27.5, "z": 42}}, {{"r": 27.5, "z": 50}},
      {{"r": 0, "z": 50}}
    ],
    "inner_contour": [
      {{"r": 9.5, "z": 0}}, {{"r": 9.5, "z": 50}}
    ],
    "total_length": 50,
    "max_diameter": 55
  }},
  "confidence": 0.95,
  "warnings": []
}}

CRITICAL:
- Odpověz POUZE platným JSON objektem — žádný text, komentáře ani markdown před nebo za JSON!
- feature_type MUSÍ být přesně z výše uvedeného seznamu!
- Dodržuj pravidla dekompozice (H7→ream, <5mm→center_drill, závit→pilot+tap)
- Každá feature MUSÍ mít rozměrové parametry (from_diameter, to_diameter, length, depth...)
- PREFEROVANĚ přidej z_start, z_end (axiální pozice začátku/konce feature od levého čela v mm) pro SVG vizualizaci
- Každá feature MUSÍ mít tool_number (int) a tool_name (str) — jeden nástroj = více features!
- tool_number jsou UNIKÁTNÍ v rámci celého dílu, NE v rámci operace
- Reálný díl má typicky 6-12 nástrojů
- Operace seřaď v pořadí výroby
- material_group = 8-digit kód z tabulky výše

KRITICKÉ - STRUCTURED OPERATIONS:
- KAŽDÁ operace MUSÍ mít: setup_id (OP10, OP20, OP30...), description, operation_type, machine_type, machine_name, features[]
- setup_id = operační číslo (OP10, OP20, OP30) — logické seskupení features podle upnutí/přenastavení
- description = CZ popis operace ("Soustružení - přední strana", "Frézování kapsy")
- operation_type = "seřizovací" (první výrobek s měřením) nebo "výrobní" (série)
- machine_type = typ stroje (lathe_3ax, mill_3ax, mill_5ax, grinder, etc.)
- machine_name = konkrétní stroj (Haas ST-20, DMG Mori NTX 1000, etc.)
- features[] = list features v rámci této operace/upnutí
- NIKDY nevracej flat list operací — vždy hierarchické: operations[].features[]!"""


def trim_pdf_pages(pdf_base64: str, max_pages: int = MAX_PDF_PAGES) -> str:
    """
    Trim PDF to first N pages to reduce token count.

    A 34-page PDF = 70K tokens ($0.25).
    A 1-page PDF = ~2K tokens ($0.006).

    Args:
        pdf_base64: Base64-encoded PDF
        max_pages: Max pages to keep (default: 2)

    Returns:
        Base64-encoded trimmed PDF
    """
    try:
        import fitz  # PyMuPDF

        pdf_bytes = base64.standard_b64decode(pdf_base64)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)

        if total_pages <= max_pages:
            doc.close()
            return pdf_base64  # Already small enough

        # Create new PDF with only first N pages
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=0, to_page=max_pages - 1)

        trimmed_bytes = new_doc.tobytes()
        new_doc.close()
        doc.close()

        trimmed_b64 = base64.standard_b64encode(trimmed_bytes).decode('utf-8')

        logger.info(
            f"Trimmed PDF: {total_pages} pages → {max_pages} pages, "
            f"{len(pdf_bytes)} bytes → {len(trimmed_bytes)} bytes"
        )

        return trimmed_b64

    except ImportError:
        logger.warning("PyMuPDF not installed, sending full PDF")
        return pdf_base64
    except Exception as e:
        logger.warning(f"Failed to trim PDF: {e}, sending full PDF")
        return pdf_base64


async def analyze_step_pdf_with_claude(
    step_text: str,
    pdf_base64: str,
    step_features: List[Dict],
    anthropic_api_key: str
) -> Dict:
    """
    Analyze STEP + PDF together using Claude API.

    This is the BEST approach - Claude can correlate:
    - STEP: CYLINDRICAL_SURFACE(diameter=19.0)
    - PDF:  "Ø19 H7 durch"
    → Operation: drilling Ø18.5 → reaming Ø19 H7 through

    Args:
        step_text: STEP file text (used only for feature summary, not sent raw)
        pdf_base64: Base64-encoded PDF file
        step_features: Features extracted by internal parser
        anthropic_api_key: Anthropic API key

    Returns:
        Dict with operations, features, metadata, cost, confidence
    """
    # Build compact prompt (NO raw STEP text - saves ~8K tokens!)
    prompt = _build_compact_prompt(step_features)

    # Trim PDF to first 2 pages (insurance for multi-page PDFs)
    trimmed_pdf = trim_pdf_pages(pdf_base64)

    return await _call_claude_with_retry(
        anthropic_api_key=anthropic_api_key,
        pdf_base64=trimmed_pdf,
        prompt=prompt,
        step_features=step_features,
        source='step_pdf_merge'
    )


async def analyze_pdf_only_with_claude(
    pdf_base64: str,
    anthropic_api_key: str
) -> Dict:
    """
    Analyze PDF only (no STEP geometry).

    Less accurate than STEP+PDF merge, but better than nothing.
    Claude will try to extract dimensions from PDF text/drawings.
    """
    prompt = _build_manufacturing_prompt(
        step_features=[],
        has_step=False,
        has_pdf=True,
    )

    # Trim PDF to first 2 pages
    trimmed_pdf = trim_pdf_pages(pdf_base64)

    result = await _call_claude_with_retry(
        anthropic_api_key=anthropic_api_key,
        pdf_base64=trimmed_pdf,
        prompt=prompt,
        step_features=[],
        source='pdf_only'
    )

    # Cap confidence for PDF-only
    if result.get('success'):
        result['confidence'] = min(result.get('confidence', 0.70), 0.80)

    return result


async def _call_claude_with_retry(
    anthropic_api_key: str,
    pdf_base64: str,
    prompt: str,
    step_features: List[Dict],
    source: str
) -> Dict:
    """
    Call Claude API with automatic retry for rate limits (429).

    Rate limit: Anthropic free tier = 30K input tokens/minute.
    A PDF document alone uses ~50-70K tokens.
    Retry waits for the rate limit window to reset.
    """
    client = AsyncAnthropic(api_key=anthropic_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Claude API call (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"source={source}"
            )

            response = await client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=8192,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Parse response
            result = parse_claude_json_response(response.content)

            # Diagnostic logging — verify JSON was parsed correctly
            if result and isinstance(result, dict):
                op_count = len(result.get('operations', []))
                feat_count = sum(
                    len(op.get('features', []))
                    for op in result.get('operations', [])
                    if isinstance(op, dict)
                )
                logger.info(
                    f"Claude JSON parsed OK: "
                    f"keys={list(result.keys())}, "
                    f"operations={op_count}, "
                    f"total_features={feat_count}, "
                    f"has_profile_geometry={'profile_geometry' in result}"
                )
            else:
                # Parse returned empty — log raw response for debugging
                raw_text = ""
                if response.content and len(response.content) > 0:
                    raw_text = getattr(response.content[0], 'text', '')[:300]
                logger.error(
                    f"Claude JSON parse returned EMPTY result! "
                    f"type={type(result).__name__}, "
                    f"raw_response_preview: {raw_text}"
                )

            # Calculate cost (Sonnet 4.5: $3/M input, $15/M output)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

            logger.info(
                f"Claude API complete: "
                f"in={input_tokens} tokens, "
                f"out={output_tokens} tokens, "
                f"cost=${cost:.4f}"
            )

            # Transform hierarchical output → flat operations
            # (backward compatible with existing frontend)
            flat_operations = _flatten_operations(result)
            raw_features = _extract_raw_features(result)

            # Diagnostic: log operation counts at each stage
            raw_ops = result.get('operations', [])
            logger.info(
                f"Operation pipeline: "
                f"raw_operations={len(raw_ops)}, "
                f"flat_operations={len(flat_operations)}, "
                f"raw_features={len(raw_features)}"
            )
            if raw_ops and len(raw_ops) > 0:
                first_op = raw_ops[0]
                logger.info(
                    f"First raw operation keys: {list(first_op.keys())}, "
                    f"has 'features': {'features' in first_op}, "
                    f"has 'operation_type': {'operation_type' in first_op}"
                )
            if len(raw_ops) > 0 and len(flat_operations) == 0:
                logger.error(
                    f"OPERATIONS LOST during flattening! "
                    f"raw_ops[0] sample: {json.dumps(raw_ops[0], default=str)[:500]}"
                )

            return {
                'success': True,
                'operations': flat_operations,  # Backward compat: flat list
                'operation_groups': result.get('operations', []),  # NEW v2.1: hierarchical
                'features': raw_features if raw_features else step_features,
                'metadata': result.get('metadata', {}),
                'profile_geometry': result.get('profile_geometry'),
                'confidence': result.get('confidence', 0.85),
                'cost': cost,
                'warnings': result.get('warnings', []),
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                # New v2 fields
                'part_type': result.get('part_type', 'rotational'),
                'material_group': result.get('material_group'),
                'material_spec': result.get('material_spec'),
                'stock': result.get('stock'),
                'raw_operations': result.get('operations', []),  # Preserve hierarchical (deprecated, use operation_groups)
            }

        except RateLimitError as e:
            delay = RETRY_BASE_DELAY * (attempt + 1)
            logger.warning(
                f"Rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}). "
                f"Waiting {delay}s before retry. Error: {e}"
            )

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("All retry attempts exhausted (rate limit)")
                return {
                    'success': False,
                    'error': f'API rate limit exceeded after {MAX_RETRIES} retries. '
                             f'Your plan allows 30K tokens/minute. '
                             f'Wait 1-2 minutes and try again.',
                    'error_code': 'RATE_LIMIT',
                    'operations': [],
                    'features': step_features,
                    'metadata': {},
                    'confidence': 0.0,
                    'cost': 0.0,
                    'warnings': [
                        'Rate limit exceeded - try again in 1-2 minutes',
                        'Consider upgrading your Anthropic API plan for higher limits'
                    ]
                }

        except Exception as e:
            logger.error(f"Claude API failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'operations': [],
                'features': step_features,
                'metadata': {},
                'confidence': 0.0,
                'cost': 0.0,
                'warnings': [f"Claude API failed: {str(e)}"]
            }

    # Should not reach here, but safety fallback
    return {
        'success': False,
        'error': 'Unexpected retry exhaustion',
        'operations': [],
        'features': step_features,
        'metadata': {},
        'confidence': 0.0,
        'cost': 0.0,
        'warnings': ['Internal error - please try again']
    }


def _build_compact_prompt(step_features: List[Dict]) -> str:
    """
    Build prompt for STEP + PDF merge.

    Delegates to _build_manufacturing_prompt() with STEP context.
    Kept as wrapper for backward compatibility with existing callers.
    """
    return _build_manufacturing_prompt(
        step_features=step_features,
        has_step=True,
        has_pdf=True,
    )


# ====================================================================
# OUTPUT TRANSFORMERS
# ====================================================================
# Claude v2 output je hierarchický: operations[].features[]
# Frontend očekává flat: operations[] (každá feature = 1 operace)
# Tyto funkce zajišťují backward kompatibilitu.
# ====================================================================

def _flatten_operations(claude_result: Dict) -> List[Dict]:
    """
    Transformuje hierarchický output z Claude v2 na flat operace.

    Claude v2 vrací:
        {"operations": [{"seq": 10, "operation_category": "turning",
          "features": [{"feature_type": "od_rough", ...}, ...]}]}

    Frontend očekává:
        [{"operation_type": "turning", "feature_type": "od_rough",
          "tool": "...", "params": {...}, "estimated_time_min": ...}]

    Pokud Claude vrátí starý flat formát, projde nezměněn.
    """
    operations = claude_result.get('operations', [])
    if not operations:
        return []

    # Detekce: starý flat formát (má operation_type přímo) vs. nový hierarchický
    first = operations[0]
    is_hierarchical = 'features' in first and isinstance(first.get('features'), list)

    if not is_hierarchical:
        # Starý formát — přidej feature_type pokud chybí
        for op in operations:
            if 'feature_type' not in op:
                op['feature_type'] = _infer_feature_type(op)
        return operations

    # Nový hierarchický formát → flatten
    flat = []
    for op_group in operations:
        category = op_group.get('operation_category', 'unknown')
        op_seq = op_group.get('seq', 0)

        for feature in op_group.get('features', []):
            feature_type = feature.get('feature_type', 'unknown')

            # Sestav params z feature fields
            params = {}
            for key in ['from_diameter', 'to_diameter', 'length', 'depth',
                        'width', 'pocket_length', 'pocket_width', 'corner_radius',
                        'thread_pitch', 'blade_width', 'count',
                        'diameter', 'tolerance', 'thread_spec']:
                if key in feature and feature[key] is not None:
                    params[key] = feature[key]

            # Backward-compatible depth handling
            if 'depth' in params and params['depth'] == 'through':
                params['depth'] = 'through'
            elif 'depth' not in params and feature.get('through'):
                params['depth'] = 'through'

            # Tool info from Claude (new) or fallback to generated
            tool_number = feature.get('tool_number')
            tool_name = feature.get('tool_name') or _suggest_tool(feature_type, params)

            flat.append({
                'operation_type': category,
                'feature_type': feature_type,
                'tool': tool_name,
                'tool_number': tool_number,
                'tool_name': tool_name,
                'params': params,
                'estimated_time_min': feature.get('estimated_time_min', 0.0),
                'confidence': feature.get('confidence', 0.9),
                'notes': feature.get('note', ''),
            })

    return flat


def _extract_raw_features(claude_result: Dict) -> List[Dict]:
    """
    Extrahuje raw features z Claude v2 hierarchického outputu.

    Sbírá features ze všech operačních skupin a vrací jako flat list
    kompatibilní s existujícím frontend zobrazením.
    """
    operations = claude_result.get('operations', [])
    if not operations:
        return claude_result.get('features', [])

    first = operations[0]
    is_hierarchical = 'features' in first and isinstance(first.get('features'), list)

    if not is_hierarchical:
        return claude_result.get('features', [])

    features = []
    for op_group in operations:
        for f in op_group.get('features', []):
            feat = {
                'type': f.get('feature_type', 'unknown'),
                'source': 'claude_v2',
            }
            if 'to_diameter' in f:
                feat['diameter'] = f['to_diameter']
            elif 'from_diameter' in f:
                feat['diameter'] = f['from_diameter']
            if 'thread_pitch' in f:
                tp = f['thread_pitch']
                d = f.get('from_diameter') or f.get('to_diameter', 0)
                feat['spec'] = f"M{d}x{tp}"
            if f.get('depth') == 'through' or f.get('through'):
                feat['through'] = True
            if 'length' in f:
                feat['length'] = f['length']
            if 'note' in f:
                feat['tolerance'] = _extract_tolerance(f['note'])

            features.append(feat)

    return features


def _infer_feature_type(operation: Dict) -> str:
    """Odvodí feature_type ze starého flat formátu (best effort)."""
    op_type = operation.get('operation_type', '').lower()
    params = operation.get('params', {})

    if 'drill' in op_type:
        d = params.get('diameter', 0)
        depth = params.get('depth', 0)
        if isinstance(depth, (int, float)) and d > 0 and depth > 4 * d:
            return 'drill_deep'
        return 'drill'
    elif 'ream' in op_type:
        return 'ream'
    elif 'thread' in op_type or 'tap' in op_type:
        return 'tap'
    elif 'chamfer' in op_type:
        return 'chamfer'
    elif 'center' in op_type:
        return 'center_drill'
    elif 'turning' in op_type or 'lathe' in op_type:
        return 'od_rough'
    elif 'face' in op_type:
        return 'face'
    elif 'groove' in op_type:
        return 'groove_od'
    elif 'parting' in op_type:
        return 'parting'
    elif 'mill' in op_type or 'pocket' in op_type:
        return 'mill_pocket'
    elif 'grind' in op_type:
        return 'grind_od'
    return 'unknown'


def _suggest_tool(feature_type: str, params: Dict) -> str:
    """Navrhne nástroj na základě feature_type a parametrů."""
    d = params.get('to_diameter') or params.get('from_diameter') or params.get('diameter', 0)

    tool_map = {
        'face': 'CNMG soustružnický nůž',
        'od_rough': 'CNMG hrubovací',
        'od_finish': 'DNMG dokončovací',
        'id_rough': 'vnitřní hrubovací',
        'id_finish': 'vnitřní dokončovací',
        'bore': f'vyvrtávací tyč Ø{d}',
        'center_drill': f'navrtávák Ø{min(d, 4) if d else 3}',
        'drill': f'vrták Ø{d}',
        'drill_deep': f'vrták hluboký Ø{d}',
        'ream': f'výstružník Ø{d}',
        'tap': f'závitník M{d}',
        'thread_od': 'závitový nůž vnější',
        'thread_id': 'závitový nůž vnitřní',
        'groove_od': 'zapichovací nůž',
        'groove_id': 'vnitřní zapichovací',
        'parting': 'upichovací nůž',
        'chamfer': 'srážecí nůž',
        'radius': 'rádiusový nůž',
        'mill_face': 'čelní fréza',
        'mill_pocket': 'stopková fréza',
        'mill_slot': 'drážkovací fréza',
        'mill_drill': f'vrták Ø{d}',
        'mill_tap': f'závitník M{d}',
        'mill_chamfer': 'srážecí fréza',
        'grind_od': 'brusný kotouč',
    }
    return tool_map.get(feature_type, f'{feature_type} nástroj')


def _extract_tolerance(text: str) -> Optional[str]:
    """Extrahuje toleranci z textu (H7, h6, ISO 2768-m)."""
    if not text:
        return None
    import re
    match = re.search(r'[HhGgJjKkMmNnPpRrSs]\d{1,2}', text)
    return match.group(0) if match else None
