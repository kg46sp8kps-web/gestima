"""GESTIMA - Quote Request Parser (AI Vision)

Parses uploaded PDF files. User classifies files in UI (auto-detected from filename).
Each file gets exactly ONE AI call:
- Request PDF -> gpt-4.1 (extracts customer + items table)
- Drawing PDF -> ft_v1 model (title block + TimeVision estimation)

Then matches drawings to items, parts + batches in DB.
Returns QuoteRequestReviewV2 for user review.
"""

import asyncio
import base64
import logging
import re
from typing import Optional

import fitz  # PyMuPDF
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.quote_request import (
    QuoteRequestReviewV2,
    DrawingAnalysis,
    DrawingMatch,
    CustomerMatch,
    PartMatch,
    ReviewSummary,
)
from app.services.openai_vision_service import (
    OPENAI_MODEL,
    is_fine_tuned_model,
    _parse_json_response,
)
from app.services.openai_vision_prompts import (
    OPENAI_FT_SYSTEM,
    build_openai_ft_prompt,
    OPENAI_VISION_SYSTEM,
    build_openai_vision_prompt,
)
from app.services.quote_service import QuoteService

logger = logging.getLogger(__name__)

MAX_IMAGE_DIM = 4096


# =============================================================================
# PDF bytes -> base64 image
# =============================================================================

def _bytes_to_base64_image(pdf_bytes: bytes, page_num: int = 0, dpi: int = 200) -> str:
    """Render a PDF page from bytes to a base64 PNG string."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF bytes: {exc}") from exc

    try:
        if page_num >= len(doc):
            raise ValueError(f"Page {page_num} out of range ({len(doc)} pages)")

        page = doc[page_num]
        scale = dpi / 72.0
        page_w = page.rect.width * scale
        page_h = page.rect.height * scale

        if max(page_w, page_h) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(page.rect.width, page.rect.height)

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        return base64.b64encode(png_bytes).decode("utf-8")
    finally:
        doc.close()


# =============================================================================
# AI call helper
# =============================================================================

def _call_vision(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    image_b64: str,
    detail: str = "high",
    max_tokens: int = 2000,
) -> dict:
    """Single OpenAI Vision call -> parsed JSON dict."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        store=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": detail,
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ],
    )
    raw = response.choices[0].message.content
    usage = response.usage
    if usage:
        logger.info(
            "OpenAI tokens: prompt=%d, completion=%d, total=%d (model=%s)",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
            model[:30],
        )
    return _parse_json_response(raw)


# =============================================================================
# Parse request PDF -> customer + items (gpt-4.1, ONE call)
# =============================================================================

PARSE_REQUEST_SYSTEM = (
    "Jsi asistent pro extrakci dat z poptavkovych dokumentu (quote requests / RFQ). "
    "Extrahuj ODESILATELE poptavky (zakaznika) a seznam polozek. Odpovez POUZE validnim JSON."
)

PARSE_REQUEST_PROMPT = """Analyzuj tuto poptavku (RFQ / cenovy dotaz) a extrahuj:

1. **Zakaznik (ODESILATEL)** -- firma ktera POSILA poptavku, NE prijemce
2. **Polozky** -- article_number, drawing_number, nazev, mnozstvi, poznamky
3. **Metadata** -- cislo poptavky, datumy, poznamky

DULEZITE - IDENTIFIKACE ZAKAZNIKA:
Na poptavce jsou VZDY DVE firmy:
- PRIJEMCE (Shipping address / dodaci adresa) = nase firma, ktere poptavka prisla. TOTO NENI zakaznik!
- ODESILATEL (sender / hlavicka / paticka / logo) = firma ktera poptavku poslala. TOTO JE zakaznik!
Zakaznik je ta firma, ktera poptavku VYSTAVILA a POSLALA. Casto je v patce, hlavicce nebo logu.
Pokud je tam "Buyer" email, patri zakaznikovi (odesilateli).

Odpovez v JSON:
{
  "customer": {
    "company_name": "nazev firmy ODESILATELE",
    "contact_person": "jmeno kontaktni osoby" nebo null,
    "email": "email (napr. buyer)" nebo null,
    "phone": "telefon odesilatele" nebo null,
    "ico": "ICO (8-mistne, CZ) nebo Tax ID" nebo null
  },
  "items": [
    {
      "article_number": "CISTE cislo artiklu (jen cislo, BEZ prefixu/tagu)",
      "drawing_number": "cislo vykresu" nebo null,
      "name": "nazev dilu",
      "quantity": 10,
      "notes": "poznamky" nebo null
    }
  ],
  "customer_request_number": "cislo poptavky" nebo null,
  "request_date": "YYYY-MM-DD" nebo null,
  "offer_deadline": "YYYY-MM-DD" nebo null,
  "notes": "obecne poznamky" nebo null
}

PRAVIDLA:
- article_number je NEJDULEZITEJSI identifikator — pod timto cislem je dil evidovany.
  Extrahuj POUZE ciste numericke cislo artiklu. Odstan VSECHNY prefixy, tagy, znacky a zavorky.
  Priklady: "[kod-0561716]" -> "0561716", "ART-12345" -> "12345", "BYN-90057637" -> "90057637",
  "#0558666" -> "0558666", "Part 12345-00" -> "12345-00". Vzdy jen holé cislo artiklu!
- drawing_number: samostatne cislo vykresu pokud je v tabulce (napr. Drawing: D00253480-001).
  Muze byt uplne jiny nez article_number. Extrahuj jak je.
- quantity: zakladni pocet kusu (cele kladne cislo). Pouzij QTY z radku tabulky.
  Pokud je u polozky SCALED PRICES (napr. "SCALED PRICES: 4 / 20 / 40 / 80 / 200 pcs"),
  uloz CELY retezec "SCALED PRICES: 4 / 20 / 40 / 80 / 200" do notes a quantity = prvni cislo (4).
- contact_person: jmeno kontaktni osoby (buyer, napr. z emailu nebo podpisu)
- request_date: datum vystaveni/odeslani poptavky (Date, Datum, Issued)
- offer_deadline: deadline pro predlozeni nabidky (Deadline for submission, Platnost do)
  POZOR: toto NENI platnost nabidky, ale termín do kdy musime nabidku odeslat!
- Zakaznik = ODESILATEL poptavky, NE prijemce/dodaci adresa"""


def _get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Get number of pages in a PDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 1


def _call_vision_multi_page(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    images_b64: list[str],
    detail: str = "high",
    max_tokens: int = 4000,
) -> dict:
    """OpenAI Vision call with multiple images -> parsed JSON dict."""
    content: list[dict] = []
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": detail,
            },
        })
    content.append({"type": "text", "text": user_prompt})

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        store=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    )
    raw = response.choices[0].message.content
    usage = response.usage
    if usage:
        logger.info(
            "OpenAI tokens: prompt=%d, completion=%d, total=%d (model=%s, pages=%d)",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
            model[:30], len(images_b64),
        )
    return _parse_json_response(raw)


async def _parse_request_pdf(client: OpenAI, pdf_bytes: bytes, filename: str) -> dict:
    """Parse request PDF with gpt-4.1. ONE call, all pages."""
    page_count = _get_pdf_page_count(pdf_bytes)
    # Skip last page if 3+ pages (usually terms/footer only)
    pages_to_parse = min(page_count, 5)  # safety cap

    images_b64 = []
    for page_num in range(pages_to_parse):
        img = _bytes_to_base64_image(pdf_bytes, page_num=page_num, dpi=250)
        images_b64.append(img)

    logger.info("Parsing request %s: %d pages as images", filename, len(images_b64))

    if len(images_b64) == 1:
        result = _call_vision(
            client, "gpt-4.1", PARSE_REQUEST_SYSTEM, PARSE_REQUEST_PROMPT,
            images_b64[0], detail="high", max_tokens=4000,
        )
    else:
        result = _call_vision_multi_page(
            client, "gpt-4.1", PARSE_REQUEST_SYSTEM, PARSE_REQUEST_PROMPT,
            images_b64, detail="high", max_tokens=4000,
        )

    logger.info("Parsed request %s: %d items, customer=%s",
                 filename, len(result.get("items", [])),
                 result.get("customer", {}).get("company_name", "?"))
    return result


# =============================================================================
# Parse drawing PDF -> TimeVision (ft_v1 or base model, ONE call)
# =============================================================================

async def _parse_drawing_pdf(
    client: OpenAI, pdf_bytes: bytes, filename: str,
) -> DrawingAnalysis:
    """Parse drawing PDF with ft_v1 (or base) model. ONE call."""
    img_b64 = _bytes_to_base64_image(pdf_bytes, dpi=300)

    ft = is_fine_tuned_model()
    if ft:
        model = OPENAI_MODEL
        sys_prompt = OPENAI_FT_SYSTEM
        user_prompt = build_openai_ft_prompt()
    else:
        model = "gpt-4.1"
        sys_prompt = OPENAI_VISION_SYSTEM
        user_prompt = build_openai_vision_prompt()

    try:
        result = _call_vision(
            client, model, sys_prompt, user_prompt,
            img_b64, detail="high", max_tokens=2000,
        )
        drawing_number = result.get("drawing_number")
        return DrawingAnalysis(
            filename=filename,
            drawing_number=drawing_number,
            article_number=drawing_number,
            material_hint=result.get("material_detected"),
            dimensions_hint=_format_dimensions(result),
            part_type=result.get("part_type", "PRI"),
            complexity=result.get("complexity", "medium"),
            estimated_time_min=float(result.get("estimated_time_min", 30.0)),
            max_diameter_mm=_safe_float(result.get("max_diameter_mm")),
            max_length_mm=_safe_float(result.get("max_length_mm")),
            confidence=_normalize_confidence(result.get("confidence", "medium")),
        )
    except Exception as exc:
        logger.error("Drawing parse failed for %s: %s", filename, exc)
        return DrawingAnalysis(filename=filename, confidence=0.0)


# =============================================================================
# Helpers
# =============================================================================

def _format_dimensions(result: dict) -> Optional[str]:
    """Format dimensions into human-readable string."""
    parts = []
    for key, prefix in [
        ("max_diameter_mm", "d"), ("max_length_mm", "L="),
        ("max_width_mm", "W="), ("max_height_mm", "H="),
    ]:
        val = result.get(key)
        if val:
            parts.append(f"{prefix}{val}")
    return " x ".join(parts) if parts else None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_confidence(val) -> float:
    """Convert confidence from string (high/medium/low) or float to 0-1."""
    if isinstance(val, (int, float)):
        return max(0.0, min(1.0, float(val)))
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(str(val).lower(), 0.5)


# =============================================================================
# Match drawings <-> items by article_number
# =============================================================================

def _extract_filename_tokens(filename: str) -> set[str]:
    """Extract meaningful tokens from drawing filename for matching.

    Example: '0561716_D00253480_000_2D_Gelso.pdf'
    -> {'0561716', 'd00253480', '000', '2d', 'gelso'}
    """
    name = filename.lower().rsplit(".", 1)[0]  # strip extension
    tokens = set(re.split(r"[_\-\s]+", name))
    tokens.discard("")
    return tokens


def _match_drawings_to_items(
    items: list[dict],
    analyses: list[DrawingAnalysis],
) -> list[DrawingMatch]:
    """Match drawings to request items using article_number + drawing_number.

    Strategy (ordered by confidence):
    1. AI Vision article/drawing number vs item article_number variants (0.95)
    2. AI Vision article/drawing number vs item drawing_number variants (0.90)
    3. Filename tokens vs item article_number variants (0.70)
    4. Filename tokens vs item drawing_number (0.65)
    """
    from app.services.article_number_matcher import ArticleNumberMatcher

    matches: list[DrawingMatch] = []

    for draw_idx, analysis in enumerate(analyses):
        has_ai_data = analysis.article_number or analysis.drawing_number
        has_filename = bool(analysis.filename)

        if not has_ai_data and not has_filename:
            matches.append(DrawingMatch(
                drawing_index=draw_idx, item_index=None,
                match_method="none", confidence=0.0,
            ))
            continue

        best_item_idx = None
        best_confidence = 0.0
        best_method = "none"

        # Build drawing identifiers from AI Vision
        draw_variants: set[str] = set()
        if analysis.article_number:
            draw_variants.update(
                v.lower() for v in ArticleNumberMatcher.generate_variants(analysis.article_number)
            )
        if analysis.drawing_number and analysis.drawing_number != analysis.article_number:
            draw_variants.update(
                v.lower() for v in ArticleNumberMatcher.generate_variants(analysis.drawing_number)
            )

        # Build filename tokens for fallback
        fn_tokens = _extract_filename_tokens(analysis.filename) if has_filename else set()

        for item_idx, item in enumerate(items):
            item_article = item.get("article_number", "")
            item_drawing = item.get("drawing_number", "")

            # -- Strategy 1: AI vision vs item article_number --
            if draw_variants and item_article:
                item_art_variants = set(
                    v.lower() for v in ArticleNumberMatcher.generate_variants(item_article)
                )
                if draw_variants & item_art_variants:
                    conf = 0.95
                    if conf > best_confidence:
                        best_confidence = conf
                        best_item_idx = item_idx
                        best_method = "ai_vision"

            # -- Strategy 2: AI vision vs item drawing_number --
            if draw_variants and item_drawing and best_confidence < 0.90:
                item_draw_variants = set(
                    v.lower() for v in ArticleNumberMatcher.generate_variants(item_drawing)
                )
                if draw_variants & item_draw_variants:
                    conf = 0.90
                    if conf > best_confidence:
                        best_confidence = conf
                        best_item_idx = item_idx
                        best_method = "ai_vision"

            # -- Strategy 3: Filename tokens vs item article_number --
            if fn_tokens and item_article and best_confidence < 0.70:
                item_art_variants = set(
                    v.lower() for v in ArticleNumberMatcher.generate_variants(item_article)
                )
                if fn_tokens & item_art_variants:
                    conf = 0.70
                    if conf > best_confidence:
                        best_confidence = conf
                        best_item_idx = item_idx
                        best_method = "filename"

            # -- Strategy 4: Filename tokens vs item drawing_number --
            if fn_tokens and item_drawing and best_confidence < 0.65:
                item_draw_variants = set(
                    v.lower() for v in ArticleNumberMatcher.generate_variants(item_drawing)
                )
                # Drawing numbers like D00253480-000: check base token match
                if fn_tokens & item_draw_variants:
                    conf = 0.65
                    if conf > best_confidence:
                        best_confidence = conf
                        best_item_idx = item_idx
                        best_method = "filename"

        matches.append(DrawingMatch(
            drawing_index=draw_idx, item_index=best_item_idx,
            match_method=best_method, confidence=best_confidence,
        ))

    return matches


# =============================================================================
# Partner matching
# =============================================================================

async def _match_partner(customer_data: dict, db: AsyncSession) -> CustomerMatch:
    """Match customer data against existing partners in DB."""
    from app.models.partner import Partner

    company_name = customer_data.get("company_name", "")
    ico = customer_data.get("ico")

    partner_id = None
    partner_number = None
    partner_exists = False
    match_confidence = 0.0

    if ico:
        result = await db.execute(
            select(Partner).where(
                Partner.ico == ico, Partner.deleted_at.is_(None),
            ).limit(1)
        )
        partner = result.scalar_one_or_none()
        if partner:
            partner_id = partner.id
            partner_number = partner.partner_number
            partner_exists = True
            match_confidence = 0.99
            logger.info("Partner matched by ICO %s: %s", ico, partner.company_name)

    if not partner_exists and company_name:
        search_term = f"%{company_name.strip()[:30]}%"
        result = await db.execute(
            select(Partner).where(
                Partner.company_name.ilike(search_term),
                Partner.deleted_at.is_(None),
            ).limit(1)
        )
        partner = result.scalar_one_or_none()
        if partner:
            partner_id = partner.id
            partner_number = partner.partner_number
            partner_exists = True
            match_confidence = 0.7
            logger.info("Partner matched by name '%s': %s", company_name, partner.company_name)

    return CustomerMatch(
        company_name=company_name,
        contact_person=customer_data.get("contact_person"),
        email=customer_data.get("email"),
        phone=customer_data.get("phone"),
        ico=ico,
        partner_id=partner_id,
        partner_number=partner_number,
        partner_exists=partner_exists,
        match_confidence=match_confidence,
    )


# =============================================================================
# Main entry point
# =============================================================================

async def parse_quote_request_v2(
    request_bytes: dict[str, bytes],
    drawing_bytes: dict[str, bytes],
    db: AsyncSession,
) -> QuoteRequestReviewV2:
    """Parse uploaded PDF files. ONE AI call per file.

    User already classified files in the UI (auto-detected from filename).
    No heuristics, no double calls.

    Args:
        request_bytes: Dict of filename -> PDF bytes (request PDFs)
        drawing_bytes: Dict of filename -> PDF bytes (drawing PDFs)
        db: Database session

    Returns:
        QuoteRequestReviewV2 for user review
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured. Set it in .env file.")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    if not request_bytes:
        raise ValueError("Nahrajte alespon jeden soubor poptavky.")

    request_filename = next(iter(request_bytes))
    if len(request_bytes) > 1:
        logger.warning("Multiple request PDFs, using first: %s", request_filename)

    logger.info(
        "Parsing: 1 request (%s) + %d drawings",
        request_filename, len(drawing_bytes),
    )

    # ALL calls in parallel — request + drawings, one call each
    request_task = _parse_request_pdf(client, request_bytes[request_filename], request_filename)
    drawing_tasks = [
        _parse_drawing_pdf(client, pdf_bytes, fname)
        for fname, pdf_bytes in drawing_bytes.items()
    ]

    all_results = await asyncio.gather(request_task, *drawing_tasks)
    request_data = all_results[0]
    drawing_analyses: list[DrawingAnalysis] = list(all_results[1:])

    items_raw = request_data.get("items", [])
    customer_raw = request_data.get("customer", {})

    if not items_raw:
        raise ValueError(
            f"Z poptavky {request_filename} nebyly extrahovany zadne polozky. "
            "Zkontrolujte, zda PDF obsahuje tabulku s dily."
        )

    logger.info(
        "AI done: %d items extracted, %d drawings analyzed — total %d API calls",
        len(items_raw), len(drawing_analyses), 1 + len(drawing_analyses),
    )

    # Match drawings <-> items
    drawing_matches = _match_drawings_to_items(items_raw, drawing_analyses)

    # Match partner in DB
    customer_match = await _match_partner(customer_raw, db)

    # Match parts + batches in DB
    part_matches: list[PartMatch] = []
    for item in items_raw:
        pm = await QuoteService.match_item(
            article_number=item.get("article_number", ""),
            drawing_number=item.get("drawing_number"),
            name=item.get("name", ""),
            quantity=int(item.get("quantity", 1)),
            notes=item.get("notes"),
            db=db,
        )
        part_matches.append(pm)

    # Summary
    unique_articles = set(pm.article_number for pm in part_matches)
    summary = ReviewSummary(
        total_items=len(part_matches),
        unique_parts=len(unique_articles),
        matched_parts=sum(1 for pm in part_matches if pm.part_exists),
        new_parts=sum(1 for pm in part_matches if not pm.part_exists),
        missing_batches=sum(
            1 for pm in part_matches
            if pm.batch_match and pm.batch_match.status == "missing"
        ),
    )

    return QuoteRequestReviewV2(
        customer=customer_match,
        items=part_matches,
        customer_request_number=request_data.get("customer_request_number"),
        request_date=request_data.get("request_date"),
        offer_deadline=request_data.get("offer_deadline"),
        notes=request_data.get("notes"),
        summary=summary,
        drawing_analyses=drawing_analyses,
        drawing_matches=drawing_matches,
    )
