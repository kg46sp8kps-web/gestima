"""GESTIMA - PDF Vision Service (Universal Context Extractor)

Universal service for extracting metadata context from PDF drawings via Claude Vision API.

SCOPE: Lightweight context extraction (NOT full feature detection)
- Part number (for filename matching)
- Material designation (ČSN/EN/DIN/W.Nr/AISI)
- ROT/PRI hint (from orthographic views)
- Confidence score

REUSABLE: Quote module + Parts/Technology module + Manual Estimation

Architecture:
- Input: PDF path
- Output: VisionContext schema (3 fields + confidence)
- API: Claude Sonnet 4.5 Vision (claude-sonnet-4-20250514)

See: ADR-042 (Proxy Features ML Architecture - Vision integration)
"""

import os
import base64
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from io import BytesIO

import anthropic
from pdf2image import convert_from_path
from PIL import Image

from app.schemas.vision_context import VisionContext

logger = logging.getLogger(__name__)


class PdfVisionService:
    """Extract metadata context from PDF drawings using Claude Vision API."""

    def __init__(self):
        """Initialize Anthropic client with API key from environment."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4.5
        self.max_tokens = 1000  # Context extraction is lightweight

    def extract_context(self, pdf_path: Path) -> Optional[VisionContext]:
        """
        Extract metadata context from PDF drawing.

        Extracts ONLY:
        - Part number (from titleblock)
        - Material designation (W.Nr/EN/ČSN/AISI)
        - ROT/PRI hint (from geometric views)

        Args:
            pdf_path: Path to PDF drawing file

        Returns:
            VisionContext schema with extracted metadata, or None if extraction fails

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If API key not configured
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # 1. Convert PDF first page to image
            logger.debug(f"Converting PDF to image: {pdf_path.name}")
            images = convert_from_path(
                str(pdf_path),
                dpi=200,
                first_page=1,
                last_page=1
            )

            if not images:
                logger.error(f"PDF conversion failed for {pdf_path.name}")
                return None

            # 2. Encode to base64
            img_base64 = self._image_to_base64(images[0])

            # 3. Build context extraction prompt
            prompt = self._build_context_prompt()

            # 4. Call Vision API
            logger.debug(f"Calling Vision API for {pdf_path.name}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # 5. Parse JSON response
            content_text = response.content[0].text

            # Strip markdown if present
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()

            result = json.loads(content_text)

            # 6. Build VisionContext schema
            context = VisionContext(
                part_number=result.get("part_number", "UNKNOWN"),
                material_designation=result.get("material_designation", "UNKNOWN"),
                rot_pri_hint=result.get("rot_pri_hint", "UNKNOWN"),
                confidence=result.get("confidence", 0.5),
                extraction_timestamp=datetime.now(timezone.utc).isoformat(),
                pdf_filename=pdf_path.name
            )

            logger.info(
                f"Vision context extracted: {context.part_number} "
                f"({context.rot_pri_hint}, {context.confidence:.0%} confidence)"
            )

            return context

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error for {pdf_path.name}: {e}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {pdf_path.name}: {e}")
            return None

        except Exception as e:
            logger.error(f"Vision context extraction failed for {pdf_path.name}: {e}")
            return None

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string for API transmission."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')

    def _build_context_prompt(self) -> str:
        """Build optimized prompt for lightweight context extraction."""
        return """Analyzuj tento výkres a extrahuj POUZE základní metadata.

1. **ČÍSLO DÍLU:**
   - Najdi číslo dílu v rámečku s popisem (výkres č., drawing number)
   - Příklady: "JR811181", "PDM-280739", "3DM_90057637"
   - Pokud není, vrať "UNKNOWN"

2. **MATERIÁL:**
   - Najdi materiálové označení (Materiál, Mat., W.Nr)
   - Příklady: "11 500", "1.4305", "C45", "EN 10025", "Al 6061"
   - Pokud není, vrať "UNKNOWN"

3. **TYP DÍLU (ROT nebo PRI):**
   - **ROT (rotační/soustružený):** Kruhový průřez, hlavní plochy jsou válcové
     - Indikátory: symboly Ø (průměr), průřez kruhu, strojní závity
   - **PRI (prizmatický/frézovaný):** Obdélníkový průřez, rovinné plochy
     - Indikátory: rozměry délka × šířka × výška, kapsy, pravoúhlé hrany
   - **UNKNOWN:** Nelze určit z výkresu

Odpověz POUZE JSON (žádný markdown):
{
  "part_number": "...",
  "material_designation": "...",
  "rot_pri_hint": "ROT|PRI|UNKNOWN",
  "confidence": 0.0-1.0
}

**Pravidla:**
- Confidence 0.9-1.0: Všechna pole jasně čitelná
- Confidence 0.7-0.9: Většina polí nalezena, jedno pole nejisté
- Confidence 0.5-0.7: Dva+ pole nejisté
- Confidence <0.5: Výkres špatně čitelný nebo chybí většina dat

VRAŤ POUZE JSON, NIC JINÉHO!"""
