"""GESTIMA - Geometry Extractor Service

Extracts structured geometry from STEP + PDF using Claude API.
Returns ONLY geometry description, NO manufacturing operations.

This is Phase 1 of ML-ready architecture:
  Phase 1: Claude extracts geometry (this file)
  Phase 2: Deterministic operation generator (operation_generator.py)
  Phase 3: Time calculation (time_calculator.py - existing)
  Phase 4: ML training data collection

ADR: Separation of concerns
- Claude = understand drawings (what is the part)
- Python = manufacturing strategy (how to make it)

v2.0 Changes (Phase 2 integration):
- Retry with rate-limit handling (2 retries, 15s delay)
- PDF trimming via trim_pdf_pages()
- Robust JSON parsing via parse_claude_json_response()
- PDF-only mode (extract_geometry_pdf_only())
- Unified model (same as step_pdf_parser)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic, RateLimitError

from app.services.claude_utils import parse_claude_json_response
from app.services.step_pdf_parser import trim_pdf_pages

logger = logging.getLogger(__name__)

# Unified model — same as step_pdf_parser for consistency
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Retry config (same as step_pdf_parser)
MAX_RETRIES = 2
RETRY_BASE_DELAY = 15  # seconds

# Max PDF pages to send
MAX_PDF_PAGES = 2


# ============================================================================
# MINIMAL PROMPT - Geometry extraction only
# ============================================================================

GEOMETRY_EXTRACTION_PROMPT = """Analyzuj STEP 3D model a PDF výkres.

**CRITICAL: Vrať JEN GEOMETRII dílu, NE výrobní operace!**

Tvůj výstup bude vstup pro deterministický generátor operací, takže MUSÍŠ být:
- **Kompletní**: Zachytit VŠECHNY features (holes, threads, chamfers, radii)
- **Přesný**: Rozměry z výkresu (ne approximate)
- **Strukturovaný**: JSON podle schématu níže

---

## VÝSTUPNÍ FORMÁT (JSON):

```json
{
  "part_type": "rotational" | "prismatic" | "sheet_metal",
  "material_spec": "C45 (1.0503)",
  "material_group": "20910004",

  "stock": {
    "type": "bar" | "plate" | "casting" | "forging",
    "dimensions": {
      "diameter": 60,    // for bar stock
      "length": 95,
      "width": null,     // for prismatic
      "height": null
    }
  },

  "profile_geometry": {
    "outer_contour": [
      {"r": 30.0, "z": 0.0},
      {"r": 30.0, "z": 48.0},
      {"r": 27.5, "z": 48.0},  // chamfer point
      {"r": 27.5, "z": 52.0},
      ...
    ],

    "inner_contour": [
      {"r": 9.5, "z": 0.0},
      {"r": 9.5, "z": 50.0},
      ...
    ],

    "features": [
      {
        "type": "hole",
        "diameter": 19.0,
        "depth": 50.0,
        "tolerance": "H7",
        "position": {"z": 0},
        "notes": "Průchozí díra, vystružená"
      },
      {
        "type": "thread_od",
        "diameter": 30.0,
        "pitch": 2.0,
        "length": 6.0,
        "spec": "M30×2",
        "hand": "right",
        "position": {"z": 42}
      },
      {
        "type": "chamfer",
        "width": 1.5,
        "angle": 45,
        "location": "od_top",
        "diameter": 55.0
      },
      {
        "type": "radius",
        "r": 10.0,
        "surface_type": "spherical",  // vs "corner_radius"
        "location": "transition_od",
        "position": {"z": 48}
      },
      {
        "type": "groove_od",
        "width": 3.0,
        "diameter": 25.0,
        "depth": 2.0,
        "position": {"z": 30}
      }
    ]
  },

  "tolerances": {
    "general": "ISO 2768-mK",
    "critical_dimensions": [
      {"feature": "Ø19 H7", "tolerance": "±0.018"},
      {"feature": "Ø55 h6", "tolerance": "-0.019/-0.002"}
    ]
  },

  "surface_finish": {
    "general": "Ra 3.2",
    "critical": [
      {"feature": "Ø19 H7", "finish": "Ra 1.6"},
      {"feature": "sphere R10", "finish": "Rz 10"}
    ]
  },

  "warnings": [
    "Kulová plocha R10 - vyžaduje speciální nástroj",
    "Tolerance H7 - nutné vystružení"
  ],

  "confidence": 0.95
}
```

---

## FEATURE TYPES (kompletní seznam):

**ROTATIONAL:**
- `hole` - díra (diameter, depth, tolerance)
- `thread_od` - vnější závit (diameter, pitch, length, spec)
- `thread_id` - vnitřní závit
- `chamfer` - zkosení (width, angle, location)
- `radius` - rádius (r, surface_type: "corner_radius" | "spherical" | "toroidal")
- `groove_od` - vnější drážka (width, diameter, depth)
- `groove_id` - vnitřní drážka
- `taper` - kužel (angle, length, from_diameter, to_diameter)
- `knurl` - rýhování (type, pitch, length)

**PRISMATIC (frézy):**
- `pocket` - kapsa (length, width, depth, corner_radius)
- `slot` - drážka (length, width, depth)
- `hole_pattern` - kruhovka děr (diameter, count, bolt_circle_diameter)
- `contour_2d` - 2D obrys (points: [{x,y}])
- `surface_3d` - 3D plocha (pouze identifikace, ne toolpath)

**BOTH:**
- `chamfer` - všude kde je zkosení
- `radius` - všude kde je zaoblení
- `flat` - ploška (pro hranaté části na rotačních dílech)

---

## KRITICKÁ PRAVIDLA:

### 1. KOMPLETNOST - nesmíš zapomenout:
✓ Všechny díry (i malé Ø4 středící důlky)
✓ Všechny závity (hledej "M\\d+×\\d+" v PDF)
✓ Všechny sražení (1×45°, 2×45°)
✓ Všechny rádiusy (R1, R10, atd.)
✓ Tolerance (H7, h6, ISO 2768)
✓ Povrchové úpravy (Ra, Rz)

### 2. PŘESNOST rozměrů:
- Použij VÝKRES (PDF), ne jen STEP model
- STEP model může mít zaokrouhlené rozměry (19.05 → 19.0)
- STEP model NEOBSAHUJE tolerance (H7, h6)
- STEP model NEOBSAHUJE závity (jsou jen jako válce)

### 3. KONTURA (outer_contour, inner_contour):
- Body jsou v pořadí od levého čela doprava (z=0 → z=max)
- Zahrnuje VŠECHNY změny průměru včetně chamferů
- Minimum 2 body (start + end), obvykle 10-30 bodů
- Pro kužele: přidej intermediate points (každých 5-10mm)

### 4. FEATURES vs KONTURA:
- **Kontura** = základní tvar (co vidíš v cross-section)
- **Features** = speciální prvky (hole, thread, chamfer, radius)
- Příklad: Díra Ø19 H7
  - Kontura: inner_contour má body pro Ø19
  - Feature: {type: "hole", diameter: 19, tolerance: "H7"}

### 5. SPHERICAL SURFACE vs CORNER RADIUS:
❌ ŠPATNĚ: R10 corner radius
✓ SPRÁVNĚ: R10 spherical surface (pokud je šrafovaná oblast na výkresu)

Rozdíl:
- corner_radius = malé zaoblení hrany (R1, R2)
- spherical = kulová plocha (R10, R15, obvykle šrafovaná)

---

## VERIFICATION (před odesláním odpovědi):

1. ✓ Zkontroluj že outer_contour má >= 2 body
2. ✓ Spočítej závity v PDF (M30×2) → musí být ve features
3. ✓ Spočítej tolerance v PDF (H7, h6) → musí být v tolerances
4. ✓ Zkontroluj že depth <= stock length (jinak warning)
5. ✓ confidence >= 0.8 (jinak warning)

---

## PŘÍKLAD (pro tento díl PDM-249322):

```json
{
  "part_type": "rotational",
  "material_spec": "C45 (1.0503)",
  "material_group": "20910004",
  "stock": {
    "type": "bar",
    "dimensions": {"diameter": 60, "length": 95}
  },
  "profile_geometry": {
    "outer_contour": [
      {"r": 30, "z": 0},
      {"r": 30, "z": 1},
      {"r": 27.5, "z": 1},
      {"r": 27.5, "z": 48},
      {"r": 27.75, "z": 48.5},
      {"r": 28, "z": 49},
      {"r": 55, "z": 49},
      {"r": 55, "z": 0}
    ],
    "inner_contour": [
      {"r": 0, "z": 0},
      {"r": 0, "z": 2},
      {"r": 9.5, "z": 2},
      {"r": 9.5, "z": 50},
      {"r": 0, "z": 50},
      {"r": 0, "z": 48}
    ],
    "features": [
      {"type": "hole", "diameter": 19, "depth": 50, "tolerance": "H7"},
      {"type": "thread_od", "diameter": 30, "pitch": 2.0, "length": 6, "spec": "M30×2"},
      {"type": "chamfer", "width": 1.5, "angle": 45, "location": "od_top", "diameter": 55},
      {"type": "radius", "r": 10, "surface_type": "spherical", "location": "transition"}
    ]
  },
  "confidence": 0.95
}
```

---

**NEZAPOMEŇ:**
- Vrať JEN JSON (v ```json bloku)
- NE operations, NE tools, NE G-code!
- JEN geometrie co vidíš na výkresu

Začni analýzou:
"""

# PDF-only variant (no STEP context mention)
GEOMETRY_PDF_ONLY_PROMPT = """Analyzuj PDF technický výkres.

**CRITICAL: Vrať JEN GEOMETRII dílu, NE výrobní operace!**

Nemáš k dispozici STEP 3D model, takže extrahuj rozměry POUZE z PDF výkresu.
Confidence bude nižší (max 0.80) protože některé rozměry mohou chybět.

Dodržuj STEJNÝ výstupní formát jako pro STEP+PDF analýzu (viz schéma výše).
""" + GEOMETRY_EXTRACTION_PROMPT.split("Začni analýzou:")[0] + "Začni analýzou:\n"


# ============================================================================
# MAIN API FUNCTIONS
# ============================================================================


async def extract_geometry_with_claude(
    step_text: str,
    pdf_base64: str,
    step_features: list,
    anthropic_api_key: str,
) -> Dict[str, Any]:
    """
    Extract structured geometry from STEP + PDF using Claude API.

    Returns ONLY geometry, not manufacturing operations.
    Operations will be generated deterministically by operation_generator.py.

    Features:
    - PDF trimming to reduce token cost
    - Retry with rate-limit handling
    - Robust JSON parsing via parse_claude_json_response()

    Args:
        step_text: First 50KB of STEP file
        pdf_base64: Base64-encoded PDF drawing
        step_features: Pre-parsed STEP features from internal parser
        anthropic_api_key: Anthropic API key

    Returns:
        {
            "success": bool,
            "geometry": {...},  // parsed geometry JSON
            "raw_response": str,
            "cost": float,
            "warnings": list,
            "error": str | None
        }
    """
    step_context = _build_step_context(step_features)
    prompt = GEOMETRY_EXTRACTION_PROMPT + "\n\n" + step_context

    # Trim PDF to save tokens
    trimmed_pdf = trim_pdf_pages(pdf_base64, MAX_PDF_PAGES)

    return await _call_geometry_claude(
        anthropic_api_key=anthropic_api_key,
        pdf_base64=trimmed_pdf,
        prompt=prompt,
    )


async def extract_geometry_pdf_only(
    pdf_base64: str,
    anthropic_api_key: str,
) -> Dict[str, Any]:
    """
    Extract geometry from PDF only (no STEP model).

    Less accurate than STEP+PDF but usable for deterministic pipeline.
    Confidence capped at 0.80.

    Args:
        pdf_base64: Base64-encoded PDF drawing
        anthropic_api_key: Anthropic API key

    Returns:
        Same format as extract_geometry_with_claude()
    """
    trimmed_pdf = trim_pdf_pages(pdf_base64, MAX_PDF_PAGES)

    result = await _call_geometry_claude(
        anthropic_api_key=anthropic_api_key,
        pdf_base64=trimmed_pdf,
        prompt=GEOMETRY_PDF_ONLY_PROMPT,
    )

    # Cap confidence for PDF-only
    if result.get("success") and result.get("geometry"):
        geo = result["geometry"]
        geo["confidence"] = min(geo.get("confidence", 0.70), 0.80)

    return result


# ============================================================================
# INTERNAL: Claude API call with retry
# ============================================================================


async def _call_geometry_claude(
    anthropic_api_key: str,
    pdf_base64: str,
    prompt: str,
) -> Dict[str, Any]:
    """
    Call Claude API for geometry extraction with retry logic.

    Handles rate limits (429) with exponential backoff.
    Uses parse_claude_json_response() for robust JSON extraction.
    """
    client = AsyncAnthropic(api_key=anthropic_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Geometry extraction Claude call "
                f"(attempt {attempt + 1}/{MAX_RETRIES})"
            )

            response = await client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }],
            )

            # Parse response with robust JSON extraction
            raw_text = response.content[0].text if response.content else ""
            geometry = parse_claude_json_response(response.content)

            if not geometry or not isinstance(geometry, dict):
                logger.error(
                    f"Geometry extraction: JSON parse returned empty. "
                    f"Raw preview: {raw_text[:300]}"
                )
                return {
                    "success": False,
                    "error": "Claude response missing valid JSON geometry",
                    "raw_response": raw_text,
                    "cost": 0.0,
                }

            # Calculate cost (Sonnet 4.5: $3/M input, $15/M output)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

            logger.info(
                f"Geometry extraction complete: "
                f"in={input_tokens}, out={output_tokens}, "
                f"cost=${cost:.4f}, "
                f"part_type={geometry.get('part_type')}, "
                f"features={len(geometry.get('profile_geometry', {}).get('features', []))}"
            )

            return {
                "success": True,
                "geometry": geometry,
                "raw_response": raw_text,
                "cost": round(cost, 4),
                "warnings": geometry.get("warnings", []),
                "error": None,
            }

        except RateLimitError as e:
            delay = RETRY_BASE_DELAY * (attempt + 1)
            logger.warning(
                f"Rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}). "
                f"Waiting {delay}s. Error: {e}"
            )

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("All retry attempts exhausted (rate limit)")
                return {
                    "success": False,
                    "error": (
                        f"API rate limit exceeded after {MAX_RETRIES} retries. "
                        "Wait 1-2 minutes and try again."
                    ),
                    "error_code": "RATE_LIMIT",
                    "raw_response": "",
                    "cost": 0.0,
                }

        except Exception as e:
            logger.error(f"Geometry extraction failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "raw_response": "",
                "cost": 0.0,
            }

    # Safety fallback (should not reach)
    return {
        "success": False,
        "error": "Unexpected retry exhaustion",
        "raw_response": "",
        "cost": 0.0,
    }


# ============================================================================
# HELPERS
# ============================================================================


def _build_step_context(step_features: list) -> str:
    """Build context from pre-parsed STEP features."""
    if not step_features:
        return ""

    context = "\n\n## STEP MODEL CONTEXT:\n\n"
    context += f"Nalezeno {len(step_features)} geometrických prvků:\n"

    for i, feat in enumerate(step_features[:20], 1):  # limit to 20
        ftype = feat.get('type', 'unknown')
        if ftype == 'cylindrical':
            context += f"  {i}. Válec Ø{feat.get('diameter', '?')}mm\n"
        elif ftype == 'hole':
            context += f"  {i}. Díra Ø{feat.get('diameter', '?')}mm\n"
        elif ftype == 'cone':
            context += f"  {i}. Kužel {feat.get('angle', '?')}° R{feat.get('radius', '?')}\n"
        elif ftype == 'radius':
            context += f"  {i}. Rádius R{feat.get('radius', '?')}mm\n"

    if len(step_features) > 20:
        context += f"  ... a {len(step_features) - 20} dalších\n"

    context += "\nPOZOR: STEP model NEOBSAHUJE tolerance a závity! Použij PDF výkres.\n"

    return context
