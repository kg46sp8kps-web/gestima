"""
PDF Context Extractor — Simplified Claude prompt for manufacturing metadata

Extracts manufacturing context from PDF drawings using Claude vision API.
NOT for geometry (deterministic STEP parser does that).
ONLY for PDF-specific annotations: tolerances, threads, material, surface treatment.

Token savings: ~80% vs full geometry extraction
- Input: ~200 tokens (vs ~800 with STEP data)
- Output: ~300 tokens (vs ~3000 with operations)

Architecture:
- Deterministic geometry from STEP (step_parser.py)
- Manufacturing metadata from PDF (this file)
- Merged by analysis_service.py
"""

import base64
import logging
from typing import Dict
from anthropic import Anthropic

from app.services.claude_utils import parse_claude_json_response

logger = logging.getLogger(__name__)

# Model selection (same as step_pdf_parser for consistency)
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Max PDF pages to send (technical drawings are 1-2 pages)
MAX_PDF_PAGES = 2


# ============================================================================
# MINIMAL CONTEXT-ONLY PROMPT
# ============================================================================

PDF_CONTEXT_PROMPT = """Analyzuj výrobní výkres (PDF) a extrahuj POUZE výrobní kontext.

NEPOSÍLEJ geometrii ani rozměry — ty máme z STEP souboru!

**Tvůj úkol: Najít JENOM tyto informace z výkresu:**

1. **Material** — Materiálové číslo nebo třída:
   - W.Nr. (např. "1.4571", "1.0503")
   - DIN standard (např. "C45", "42CrMo4")
   - EN standard (např. "EN 1.4301")

2. **Tolerances** — Tolerance uvedené na výkresu:
   - Obecná tolerance (např. "ISO 2768-mK")
   - Specifické tolerance na rozměry (např. "Ø19 H7", "85 h6")

3. **Threads** — Závity specifikované na výkresu:
   - Označení (např. "M30×2", "M8", "G1/4")
   - Délka závitu pokud uvedena (mm)

4. **Surface treatment** — Povrchová úprava:
   - Kalení (např. "Nitrieren", "HRC 58-62")
   - Povlakování (např. "Zn", "Brünieren", "eloxovat")

5. **Surface roughness** — Drsnost povrchu:
   - Ra hodnoty (např. "Ra 1.6", "Ra 0.8")
   - Rz hodnoty (např. "Rz 10")
   - Lokace (např. "shaft", "bore", "all surfaces")

---

**VÝSTUPNÍ FORMÁT (JSON):**

```json
{
  "material": "1.4571",
  "tolerance_standard": "ISO 2768-mK",
  "tolerances": [
    {"feature": "Ø19", "tolerance": "H7"},
    {"feature": "85", "tolerance": "h6"}
  ],
  "threads": [
    {"spec": "M30×2", "length": 77.5},
    {"spec": "M8", "length": null}
  ],
  "surface_treatment": "Nitrieren",
  "roughness": [
    {"value": "Ra 1.6", "location": "shaft"},
    {"value": "Ra 0.8", "location": "bore"}
  ]
}
```

**PRAVIDLA:**
- Vrať POUZE informace EXPLICITNĚ uvedené ve výkresu
- Pokud info chybí, vynech pole (NE null hodnoty pro top-level klíče!)
- NEHÁZEJ geometrii — máme ji z STEP!
- Pokud výkres neobsahuje žádnou z těchto info, vrať prázdné pole/null

**PŘÍKLAD prázdného výsledku (pokud výkres neobsahuje context):**
```json
{
  "tolerances": [],
  "threads": []
}
```
"""


async def extract_pdf_context(
    pdf_path: str,
    api_key: str,
    max_pages: int = MAX_PDF_PAGES
) -> Dict:
    """
    Extract manufacturing context from PDF using Claude vision.

    Args:
        pdf_path: Path to PDF file
        api_key: Anthropic API key
        max_pages: Max PDF pages to send (default 2)

    Returns:
        {
            'material': str or None,
            'tolerance_standard': str or None,
            'tolerances': List[Dict],
            'threads': List[Dict],
            'surface_treatment': str or None,
            'roughness': List[Dict],
            'source': 'pdf_context',
            'success': True/False,
            'error': str (if success=False)
        }

    Example:
        >>> result = await extract_pdf_context('drawing.pdf', api_key)
        >>> result['material']
        '1.4571'
        >>> result['threads']
        [{'spec': 'M30×2', 'length': 77.5}]
    """
    try:
        # Read PDF file
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        except FileNotFoundError:
            logger.error(f"PDF file not found: {pdf_path}")
            return _empty_context(error=f"File not found: {pdf_path}")
        except OSError as e:
            logger.error(f"Failed to read PDF file {pdf_path}: {e}")
            return _empty_context(error=f"Read error: {e}")

        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # Trim to max_pages (reuse trim logic from step_pdf_parser)
        trimmed_pdf = _trim_pdf_pages(pdf_base64, max_pages)

        # Call Claude API (sync client)
        client = Anthropic(api_key=api_key)

        logger.info(f"Calling Claude API for PDF context extraction: {pdf_path}")

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": trimmed_pdf
                        }
                    },
                    {
                        "type": "text",
                        "text": PDF_CONTEXT_PROMPT
                    }
                ]
            }]
        )

        # Parse JSON response
        result = parse_claude_json_response(response.content)

        # Validate result is a dict
        if not isinstance(result, dict):
            logger.warning(
                f"Claude returned non-dict result: {type(result).__name__}"
            )
            return _empty_context(error="Invalid response format")

        # Add metadata
        result['source'] = 'pdf_context'
        result['success'] = True

        # Ensure lists exist (parse_claude_json_response returns empty dict on missing keys)
        result.setdefault('tolerances', [])
        result.setdefault('threads', [])
        result.setdefault('roughness', [])

        logger.info(
            f"PDF context extracted: material={result.get('material')}, "
            f"tolerances={len(result['tolerances'])}, "
            f"threads={len(result['threads'])}"
        )

        return result

    except Exception as e:
        logger.error(f"PDF context extraction failed: {e}", exc_info=True)
        return _empty_context(error=str(e))


def _empty_context(error: str = None) -> Dict:
    """
    Return empty context dict on failure.

    Args:
        error: Optional error message

    Returns:
        Empty context with success=False
    """
    result = {
        'material': None,
        'tolerance_standard': None,
        'tolerances': [],
        'threads': [],
        'surface_treatment': None,
        'roughness': [],
        'source': 'pdf_context',
        'success': False
    }
    if error:
        result['error'] = error
    return result


def _trim_pdf_pages(pdf_base64: str, max_pages: int) -> str:
    """
    Trim PDF to first N pages to reduce token count.

    A 34-page PDF = 70K tokens.
    A 1-page PDF = ~2K tokens.

    Args:
        pdf_base64: Base64-encoded PDF
        max_pages: Max pages to keep

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
            return pdf_base64

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
