"""GESTIMA - Quote Request Parser (Claude AI)

Parses quote request PDFs using Claude 3.5 Sonnet Vision API.

Features:
- PDF → structured JSON extraction
- Customer info + items list
- Confidence scoring
- Error handling + fallback
"""

import base64
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from app.schemas.quote_request import (
    QuoteRequestExtraction,
    CustomerExtraction,
    ItemExtraction,
)

logger = logging.getLogger(__name__)


# Claude prompt for quote request extraction
QUOTE_REQUEST_PROMPT = """
Analyze this quote request form PDF and extract structured data.

This is a B2B quote request (poptávka) with customer information and a table of parts/items.

Return ONLY valid JSON matching this EXACT schema (no markdown, no explanations):

{
  "customer": {
    "company_name": "string (REQUIRED - company/organization name)",
    "contact_person": "string | null (name of contact person)",
    "email": "string | null (email address)",
    "phone": "string | null (phone number)",
    "ico": "string | null (Czech business ID - 8 digits)",
    "confidence": 0.0-1.0 (how confident are you about this data)
  },
  "items": [
    {
      "article_number": "string (REQUIRED - part number / drawing number - MUST BE EXACT!)",
      "name": "string (REQUIRED - part description/name)",
      "quantity": integer (REQUIRED - number of pieces, MUST BE > 0)",
      "notes": "string | null (any notes/comments for this item)",
      "confidence": 0.0-1.0 (how confident are you about this item)
    }
  ],
  "valid_until": "YYYY-MM-DD | null (quote validity deadline)",
  "notes": "string | null (any additional information)"
}

CRITICAL RULES:
1. Extract ALL items from the table - even if same article_number repeats multiple times
2. article_number MUST be EXACT (no typos, no modifications!)
3. If you see "ABC-123" in PDF, return exactly "ABC-123" (not "ABC123" or "ABC -123")
4. quantity MUST be integer > 0
5. If a field is unclear/unreadable, set it to null and lower confidence score
6. Return ONLY JSON, no markdown code blocks, no explanations
7. If the same part appears multiple times with different quantities, create separate items

Confidence scoring guide:
- 1.0 = Crystal clear, no doubt
- 0.9 = Very confident, minor ambiguity
- 0.7 = Somewhat confident, readable but unclear
- 0.5 = Low confidence, poor quality or ambiguous
- 0.3 = Very low confidence, guessing

Example valid response:
{
  "customer": {
    "company_name": "ACME Corporation s.r.o.",
    "contact_person": "Jan Novák",
    "email": "jan.novak@acme.cz",
    "phone": "+420 123 456 789",
    "ico": "12345678",
    "confidence": 0.95
  },
  "items": [
    {
      "article_number": "ABC-123",
      "name": "Hřídel ø50x200",
      "quantity": 100,
      "notes": "Materiál 1.4301",
      "confidence": 1.0
    },
    {
      "article_number": "ABC-123",
      "name": "Hřídel ø50x200",
      "quantity": 500,
      "notes": null,
      "confidence": 1.0
    }
  ],
  "valid_until": "2026-03-01",
  "notes": "Termín dodání: Q2 2026"
}
"""


class QuoteRequestParser:
    """Claude-based PDF parser for quote requests"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize parser with Anthropic API key.

        Args:
            api_key: Anthropic API key
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        self.model = model

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            logger.info(f"Initialized QuoteRequestParser with model {model}")
        except ImportError:
            logger.error("anthropic package not installed - run: pip install anthropic")
            raise HTTPException(
                status_code=500,
                detail="AI parser not available - missing anthropic package"
            )

    async def parse_pdf(self, pdf_path: Path) -> QuoteRequestExtraction:
        """
        Parse quote request PDF and extract structured data.

        Args:
            pdf_path: Path to PDF file

        Returns:
            QuoteRequestExtraction with customer + items

        Raises:
            HTTPException 400: Invalid PDF or parsing failed
            HTTPException 500: API error
        """
        if not pdf_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"PDF file not found: {pdf_path}"
            )

        # Read PDF as base64
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            logger.debug(f"Read PDF file: {pdf_path} ({len(pdf_bytes)} bytes)")
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read PDF file: {str(e)}"
            )

        # Call Claude Vision API
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                timeout=30.0,  # 30 seconds timeout
                messages=[
                    {
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
                                "text": QUOTE_REQUEST_PROMPT,
                            },
                        ],
                    }
                ],
            )

            # Extract text response
            response_text = message.content[0].text
            logger.debug(f"Claude response: {response_text[:500]}...")

        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"AI parsing failed: {str(e)}"
            )

        # Parse JSON response
        try:
            # Claude sometimes wraps JSON in markdown code blocks - strip them
            if response_text.startswith("```"):
                # Extract JSON from ```json ... ```
                lines = response_text.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            data = json.loads(response_text)

            # Validate with Pydantic
            extraction = QuoteRequestExtraction.model_validate(data)

            logger.info(
                f"Successfully parsed quote request: "
                f"customer={extraction.customer.company_name}, "
                f"items={len(extraction.items)}"
            )

            return extraction

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Claude: {e}", exc_info=True)
            logger.error(f"Response text: {response_text}")
            raise HTTPException(
                status_code=500,
                detail=f"AI returned invalid JSON: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to validate extraction: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response: {str(e)}"
            )


# Factory function
def get_quote_parser(api_key: Optional[str] = None) -> QuoteRequestParser:
    """
    Factory function to create QuoteRequestParser.

    Args:
        api_key: Anthropic API key (if None, reads from settings)

    Returns:
        QuoteRequestParser instance

    Raises:
        HTTPException 500: If API key not configured
    """
    if api_key is None:
        from app.config import settings
        api_key = getattr(settings, "ANTHROPIC_API_KEY", None)

        if not api_key:
            logger.error("ANTHROPIC_API_KEY not configured in .env")
            raise HTTPException(
                status_code=500,
                detail="AI parser not configured - missing ANTHROPIC_API_KEY in .env"
            )

    return QuoteRequestParser(api_key=api_key)
