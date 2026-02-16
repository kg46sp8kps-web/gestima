"""OpenAI Vision - Single-call machining time estimation from PDF drawing.

Single-call pipeline:
  PDF → render to image → GPT-4o vision → JSON (extraction + estimation combined)

Supports both base GPT-4o and fine-tuned models for improved accuracy.
"""

import json
import base64
import logging
from pathlib import Path
from typing import Optional, Callable

import fitz  # PyMuPDF
from openai import OpenAI

from app.config import settings
from app.services.openai_vision_prompts import (
    OPENAI_VISION_SYSTEM,
    OPENAI_FT_SYSTEM,
    OPENAI_FEATURES_SYSTEM,
    build_openai_vision_prompt,
    build_openai_ft_prompt,
    build_features_prompt,
)

logger = logging.getLogger(__name__)

# OpenAI model to use
# Base model: "gpt-4o"
# Fine-tuned v1 (55 examples, 2026-02-13): "ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH"
OPENAI_MODEL = "ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH"


def is_fine_tuned_model() -> bool:
    """Check if the currently configured model is a fine-tuned model."""
    return OPENAI_MODEL.startswith("ft:")

MAX_IMAGE_DIMENSION = 4096  # OpenAI high-detail max tile size


def _pdf_to_base64_image(pdf_path: str, page_num: int = 0, dpi: int = 300) -> str:
    """Render a PDF page to a PNG image and return as base64 string.

    Automatically caps image dimensions to MAX_IMAGE_DIMENSION to stay within
    OpenAI vision API limits while maintaining 300+ DPI for standard drawings.

    Args:
        pdf_path: Path to the PDF file.
        page_num: Page number to render (0-indexed).
        dpi: Target resolution (will be reduced for oversized pages).

    Returns:
        Base64-encoded PNG image string.

    Raises:
        FileNotFoundError: If PDF file doesn't exist.
        RuntimeError: If PDF rendering fails.
    """
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.error("Failed to open PDF %s: %s", pdf_path, exc)
        raise RuntimeError(f"Failed to open PDF: {exc}") from exc

    try:
        if page_num >= len(doc):
            raise ValueError(
                f"Page {page_num} out of range (PDF has {len(doc)} pages)"
            )

        page = doc[page_num]

        # Calculate scale factor, cap at MAX_IMAGE_DIMENSION
        scale = dpi / 72.0
        page_w = page.rect.width * scale
        page_h = page.rect.height * scale

        if max(page_w, page_h) > MAX_IMAGE_DIMENSION:
            scale = MAX_IMAGE_DIMENSION / max(page.rect.width, page.rect.height)
            effective_dpi = scale * 72
            logger.info(
                "Capping image size: %dx%d → %dx%d (DPI %d→%d)",
                int(page_w), int(page_h),
                int(page.rect.width * scale), int(page.rect.height * scale),
                dpi, int(effective_dpi),
            )

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        logger.info(
            "Rendered %s page %d: %dx%d px, %d KB",
            Path(pdf_path).name, page_num, pix.width, pix.height,
            len(png_bytes) // 1024,
        )
        return base64.b64encode(png_bytes).decode("utf-8")
    except Exception as exc:
        logger.error("Failed to render PDF page: %s", exc)
        raise RuntimeError(f"Failed to render PDF page: {exc}") from exc
    finally:
        doc.close()


async def estimate_from_pdf_openai(
    pdf_path: str,
    similar_parts: Optional[list] = None,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    """Single-call estimation: PDF image → GPT-4o vision → extraction + time estimate.

    Args:
        pdf_path: Path to the PDF drawing file.
        similar_parts: Optional list of similar parts for context.
        on_step: Optional callback for progress reporting.

    Returns:
        Dict with both extraction fields and estimation fields:
        {
            "part_type", "complexity", "material_detected",
            "max_diameter_mm", "max_length_mm", "max_width_mm", "max_height_mm",
            "manufacturing_description", "operations",
            "estimated_time_min", "confidence", "reasoning", "breakdown"
        }

    Raises:
        FileNotFoundError: If PDF file doesn't exist.
        ValueError: If OpenAI API key is not configured.
        RuntimeError: If OpenAI API call fails or returns invalid JSON.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured. Set it in .env file.")

    # Step 1: Render PDF to image
    if on_step:
        on_step("Rendering PDF to image...")

    try:
        image_b64 = _pdf_to_base64_image(pdf_path)
    except Exception as exc:
        logger.error("PDF rendering failed for %s: %s", path.name, exc)
        raise

    logger.info("PDF rendered to image: %s (%d bytes b64)", path.name, len(image_b64))

    # Step 2: Call vision model
    ft = is_fine_tuned_model()
    model_label = "fine-tuned" if ft else "base GPT-4o"
    if on_step:
        on_step(f"OpenAI {model_label} vision odhad...")

    # Fine-tuned model uses compact prompts (tables learned from training data)
    # Base model uses full prompts with reference tables and calibration examples
    if ft:
        sys_prompt = OPENAI_FT_SYSTEM
        user_prompt = build_openai_ft_prompt()
        logger.info("Using COMPACT prompts for fine-tuned model")
    else:
        sys_prompt = OPENAI_VISION_SYSTEM
        user_prompt = build_openai_vision_prompt(similar_parts=similar_parts)
        logger.info("Using FULL prompts for base model")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # 2 attempts: high detail → auto detail
    # No fallback to minimal prompt — better to fail than return garbage estimates
    strategies = [
        ("high", sys_prompt, user_prompt),
        ("auto", sys_prompt, user_prompt),
    ]

    raw_text = None
    for attempt, (detail_mode, sys_prompt, usr_prompt) in enumerate(strategies, 1):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=2000,
                temperature=0,
                store=True,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": detail_mode,
                                },
                            },
                            {"type": "text", "text": usr_prompt},
                        ],
                    },
                ],
            )
        except Exception as exc:
            logger.error("OpenAI API call failed (attempt %d, detail=%s): %s", attempt, detail_mode, exc)
            if attempt == len(strategies):
                raise RuntimeError(f"OpenAI API call failed: {exc}") from exc
            continue

        raw_text = response.choices[0].message.content
        logger.info("OpenAI response (attempt %d, detail=%s, %d chars): %s...",
                     attempt, detail_mode, len(raw_text), raw_text[:200])

        # Check for refusal — try next strategy
        if raw_text and ("can't assist" in raw_text.lower() or "cannot assist" in raw_text.lower()
                         or "i'm sorry" in raw_text.lower()):
            logger.warning("OpenAI refused (attempt %d/%d, detail=%s): %s",
                           attempt, len(strategies), detail_mode, raw_text[:100])
            if attempt < len(strategies):
                logger.info("Retrying with strategy %d...", attempt + 1)
                continue
            raise RuntimeError(f"OpenAI refused to process drawing: {raw_text[:200]}")

        # Success
        break

    # Extract JSON from response (handle potential markdown wrapping)
    result = _parse_json_response(raw_text)

    # Log token usage
    usage = response.usage
    if usage:
        logger.info(
            "OpenAI tokens: prompt=%d, completion=%d, total=%d",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
        )

    logger.info(
        "OpenAI estimation: %s, %s, %.1f min (confidence: %s)",
        result.get("part_type"),
        result.get("material_detected"),
        result.get("estimated_time_min", 0),
        result.get("confidence"),
    )

    return result


async def extract_features_from_pdf_openai(
    pdf_path: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    """Extract features from PDF drawing using OpenAI vision (base gpt-4o).

    This function ONLY extracts features (no time estimation).
    Uses base gpt-4o model for feature extraction (NOT fine-tuned model).

    Args:
        pdf_path: Path to the PDF drawing file.
        on_step: Optional callback for progress reporting.

    Returns:
        Dict with extracted features:
        {
            "drawing_number", "part_name", "part_type",
            "material": {"designation", "standard", "group"},
            "overall_dimensions": {"max_diameter_mm", "max_length_mm", ...},
            "features": [{"type", "count", "detail", "location"}, ...],
            "general_notes": [...],
            "feature_summary": {...}
        }

    Raises:
        FileNotFoundError: If PDF file doesn't exist.
        ValueError: If OpenAI API key is not configured.
        RuntimeError: If OpenAI API call fails or returns invalid JSON.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured. Set it in .env file.")

    # Step 1: Render PDF to image
    if on_step:
        on_step("Rendering PDF to image...")

    try:
        image_b64 = _pdf_to_base64_image(pdf_path)
    except Exception as exc:
        logger.error("PDF rendering failed for %s: %s", path.name, exc)
        raise

    logger.info("PDF rendered to image for features: %s (%d bytes b64)", path.name, len(image_b64))

    # Step 2: Call vision model (ALWAYS use base gpt-4o, NOT fine-tuned)
    if on_step:
        on_step("OpenAI gpt-4.1 feature extraction...")

    sys_prompt = OPENAI_FEATURES_SYSTEM
    user_prompt = build_features_prompt()
    logger.info("Using base gpt-4.1 for feature extraction (NOT fine-tuned model)")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # 2 attempts: high detail → auto detail
    strategies = [
        ("high", sys_prompt, user_prompt),
        ("auto", sys_prompt, user_prompt),
    ]

    raw_text = None
    for attempt, (detail_mode, sys_prompt, usr_prompt) in enumerate(strategies, 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",  # Base model for features — better vision than gpt-4o
                max_tokens=4000,  # Features need more output than time estimation
                temperature=0,
                store=True,  # Log to OpenAI dashboard
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": detail_mode,
                                },
                            },
                            {"type": "text", "text": usr_prompt},
                        ],
                    },
                ],
            )
        except Exception as exc:
            logger.error("OpenAI API call failed (attempt %d, detail=%s): %s", attempt, detail_mode, exc)
            if attempt == len(strategies):
                raise RuntimeError(f"OpenAI API call failed: {exc}") from exc
            continue

        raw_text = response.choices[0].message.content
        logger.info("OpenAI response (attempt %d, detail=%s, %d chars): %s...",
                     attempt, detail_mode, len(raw_text), raw_text[:200])

        # Check for refusal — try next strategy
        if raw_text and ("can't assist" in raw_text.lower() or "cannot assist" in raw_text.lower()
                         or "i'm sorry" in raw_text.lower()):
            logger.warning("OpenAI refused (attempt %d/%d, detail=%s): %s",
                           attempt, len(strategies), detail_mode, raw_text[:100])
            if attempt < len(strategies):
                logger.info("Retrying with strategy %d...", attempt + 1)
                continue
            raise RuntimeError(f"OpenAI refused to process drawing: {raw_text[:200]}")

        # Success
        break

    # Extract JSON from response (handle potential markdown wrapping)
    result = _parse_json_response(raw_text)

    # Log token usage
    usage = response.usage
    if usage:
        logger.info(
            "OpenAI tokens (features): prompt=%d, completion=%d, total=%d",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
        )

    features_count = len(result.get("features", []))
    logger.info(
        "OpenAI feature extraction: %s, %s, %d features extracted",
        result.get("part_type"),
        result.get("drawing_number"),
        features_count,
    )

    return result


def _parse_json_response(raw_text: str) -> dict:
    """Parse JSON from OpenAI response, handling markdown code blocks.

    Args:
        raw_text: Raw response text from OpenAI.

    Returns:
        Parsed dict.

    Raises:
        RuntimeError: If JSON parsing fails.
    """
    text = raw_text.strip()

    # Strip markdown code block if present
    if text.startswith("```"):
        # Remove opening ```json or ```
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        # Remove closing ```
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI JSON response: %s\nRaw: %s", exc, raw_text[:500])
        raise RuntimeError(
            f"OpenAI returned invalid JSON: {exc}. Raw response: {raw_text[:200]}"
        ) from exc
