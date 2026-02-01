"""GESTIMA - Quote Request Parser (OpenAI Vision)

Parses quote request PDFs using OpenAI GPT-4 Vision API.

Features:
- PDF → images → structured JSON extraction
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
)

logger = logging.getLogger(__name__)


# OpenAI prompt for quote request extraction
QUOTE_REQUEST_PROMPT = """
You are analyzing a B2B QUOTE REQUEST document (RFQ - Request for Quotation).

Your task: Extract structured data using SEMANTIC UNDERSTANDING of document roles and visual layout.

Return ONLY valid JSON (no markdown, no explanations):

{
  "customer": {
    "company_name": "string (REQUIRED - full legal name including business entity type)",
    "contact_person": "string | null",
    "email": "string | null",
    "phone": "string | null",
    "ico": "string | null (business registration ID - extract EXACTLY as shown)",
    "confidence": 0.0-1.0
  },
  "items": [
    {
      "article_number": "string (REQUIRED - part identifier - PRESERVE EXACTLY: all dashes, dots, spaces, case)",
      "name": "string (REQUIRED - part description/title)",
      "quantity": integer (REQUIRED - must be positive integer)",
      "notes": "string | null (technical specs, material codes, special requirements)",
      "confidence": 0.0-1.0
    }
  ],
  "valid_until": "YYYY-MM-DD | null (quote validity deadline)",
  "notes": "string | null (RFQ reference number, delivery terms, general remarks)"
}

═══════════════════════════════════════════════════════════════════════════════
RULE 1: ROLE-BASED ENTITY IDENTIFICATION (UNIVERSAL - ANY LANGUAGE)
═══════════════════════════════════════════════════════════════════════════════

CRITICAL CONCEPT: Understand WHO creates vs WHO requests the quote.

CUSTOMER (who you MUST extract):
→ The entity REQUESTING the quote
→ The entity who will RECEIVE goods/services
→ The BUYER in this transaction

SUPPLIER (who you MUST IGNORE):
→ The entity CREATING this document
→ The entity who will PROVIDE goods/services
→ The SELLER in this transaction

IDENTIFICATION STRATEGIES (use ALL clues together):

A) SPATIAL/VISUAL CLUES (strongest signals):
   ┌─────────────────────────────────────────────────────────────┐
   │ HEADER ZONE (top 15% of page)                               │
   │ - Company logos, letterhead, "from" sections                │
   │ - Contact info in headers/footers                           │
   │ → THIS IS THE SUPPLIER - IGNORE FOR CUSTOMER EXTRACTION     │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │ BODY ZONE (middle 40-70% of page)                           │
   │ - Shipping/delivery addresses (ANY language)                │
   │ - "To:", "Bill to:", "Ship to:" sections                    │
   │ - Boxed/highlighted recipient information                   │
   │ - Contact blocks in main document area                      │
   │ → THIS IS THE CUSTOMER - EXTRACT THIS                       │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │ FOOTER ZONE (bottom 15% of page)                            │
   │ - Bank details, registration numbers, disclaimers           │
   │ - Repeated company info                                     │
   │ → THIS IS THE SUPPLIER - IGNORE FOR CUSTOMER EXTRACTION     │
   └─────────────────────────────────────────────────────────────┘

B) SEMANTIC ROLE MARKERS (language-agnostic patterns):

   CUSTOMER indicators (extract if near these patterns):
   - Delivery/shipping address (ANY language: "Ship", "Deliver", "送货", "納品", "Lieferung", "Livraison")
   - Recipient/buyer labels (ANY: "To:", "Customer:", "Buyer:", "客户", "顧客", "Kunde", "Cliente")
   - Billing/invoicing address for PAYEE
   - Boxed sections titled with recipient semantics

   SUPPLIER indicators (IGNORE if near these patterns):
   - Sender/from labels ("From:", "Sender:", "发件人", "送信者", "Von:", "De:")
   - Document creator watermarks
   - Company branding/logo areas
   - Footer contact blocks

C) BUSINESS LOGIC CLUES:

   - If multiple company names exist → SMALLER/SECONDARY one is usually customer
   - If one company appears 3+ times → It's the SUPPLIER (ignore it)
   - Shipping address ≠ Supplier address → Shipping is CUSTOMER
   - "Attention:", "ATTN:", "致:" near name → Usually CUSTOMER contact

═══════════════════════════════════════════════════════════════════════════════
RULE 2: BUSINESS ID EXTRACTION (MULTI-JURISDICTION)
═══════════════════════════════════════════════════════════════════════════════

Business registration IDs appear in various forms worldwide:

PATTERNS TO RECOGNIZE:
- European VAT: "CZ12345678", "DE123456789", "FR12345678901"
- Czech IČO: 8-digit number, may have "CZ" prefix
- US EIN: "12-3456789" (Tax ID)
- UK: "GB123456789" or "Company No. 12345678"
- Asian: 統一編號 (Taiwan 8-digit), 法人番号 (Japan 13-digit), 社会信用代码 (China 18-char)

EXTRACTION RULES:
1. Look ONLY in customer section (not supplier header/footer)
2. Extract EXACTLY as shown (preserve all formatting: dashes, spaces, prefixes)
3. Common labels (ANY language): "IČO", "VAT", "TIN", "Tax ID", "Reg. No.", "統一編號", "登録番号"
4. Store in "ico" field regardless of country (field name is legacy, accepts any business ID)

═══════════════════════════════════════════════════════════════════════════════
RULE 3: RFQ/DOCUMENT REFERENCE NUMBER
═══════════════════════════════════════════════════════════════════════════════

VISUAL CUES:
- Typically near document title (top 20% of page)
- Often bold, larger font, or in a labeled box
- Appears ONCE per document (not repeated in footer)

PATTERN MATCHING (language-agnostic):
- Alphanumeric codes with common prefixes:
  * "RFQ", "P", "Q", "REQ", "PO" (English)
  * "Poptávka", "PP", "POP" (Czech)
  * "報價", "見積" (Asian)
  * Any: "No.", "Nr.", "番号", "#"

- Common formats:
  * "RFQ-2026-001", "P17992", "REQ#12345"
  * "Poptávka č. 123/2026"
  * "見積番号: 2026-0123"

EXTRACTION:
1. Find reference number using visual proximity to title
2. Extract identifier only (strip labels: "RFQ: P17992" → extract "P17992")
3. Store in "notes" field as: "RFQ: [extracted_number]"
4. If other notes exist, prepend: "RFQ: [number] | [other notes]"

═══════════════════════════════════════════════════════════════════════════════
RULE 4: ITEMS TABLE EXTRACTION (STRUCTURE-BASED)
═══════════════════════════════════════════════════════════════════════════════

TABLE IDENTIFICATION (visual patterns):
- Grid structure with visible/implicit borders
- Header row: Bold text or background color
- Repeated row pattern (3+ rows with similar structure)
- Typically occupies 30-60% of page vertically

COLUMN SEMANTICS (position-based, language-agnostic):

LEFT COLUMNS (leftmost 30%):
→ Part identifiers: Drawing numbers, SKUs, article codes, model numbers
→ Labels (ignore): "No.", "Item", "Pos.", "番号", "項目"
→ Extract to: "article_number"

MIDDLE COLUMNS (center 40%):
→ Descriptions: Part names, specifications, titles
→ May span multiple lines
→ Extract to: "name"

RIGHT COLUMNS (rightmost 30%):
→ Quantities: Numeric values with unit labels
→ Labels (ignore): "Qty", "Ks", "Pcs", "個", "数量", "Stk"
→ Extract to: "quantity"

OPTIONAL COLUMNS:
→ Material codes, finish specs, technical notes → Extract to: "notes"

EXTRACTION RULES:

1. **Article Number Preservation**:
   - Copy EXACTLY character-by-character
   - Preserve: dashes (-), dots (.), slashes (/), spaces, case
   - Examples: "965-621344", "ABC.123.XY", "Part 10/2026"

2. **Row-by-Row Processing**:
   - Each table ROW = one JSON item
   - If same article_number appears in multiple rows → Create SEPARATE items
   - DO NOT merge/deduplicate rows
   - DO NOT sum quantities across rows

3. **Quantity Parsing**:
   - Extract as positive integer only
   - Ignore unit labels ("100 pcs" → 100)
   - Multipliers: "3x 100" → 100 (quantity per line item, not total)
   - Ranges: "50-100" → use first number (50) + note the range

4. **Multi-line Items**:
   - If description spans 2+ rows → Concatenate into single "name"
   - Technical specs below name → Move to "notes"

═══════════════════════════════════════════════════════════════════════════════
RULE 5: DATE EXTRACTION (INTERNATIONAL FORMATS)
═══════════════════════════════════════════════════════════════════════════════

SEMANTIC SEARCH:
- Labels (ANY language): "Valid until", "Expiry", "Deadline", "Platnost do", "有効期限", "截止日期"
- Position: Usually top-right or bottom of document

FORMATS TO RECOGNIZE:
- ISO 8601: "2026-03-15"
- European: "15.03.2026", "15/03/2026"
- US: "03/15/2026", "March 15, 2026"
- Asian: "2026年3月15日", "2026/03/15"

OUTPUT: Always convert to ISO 8601 (YYYY-MM-DD)

═══════════════════════════════════════════════════════════════════════════════
RULE 6: CONFIDENCE SCORING
═══════════════════════════════════════════════════════════════════════════════

Set confidence per field based on:

0.95-1.00: Crystal clear, no ambiguity
- Printed text, high contrast, standard fonts
- Unambiguous layout (single clear customer section)

0.80-0.94: Readable but minor ambiguity
- Slightly blurry text but still readable
- Two possible customer candidates (used semantic rules to choose)

0.50-0.79: Partially unclear or inferred
- Poor scan quality, handwritten sections
- Had to use spatial inference (no explicit labels)

0.00-0.49: Guessing or very uncertain
- Multiple equally valid interpretations
- Critical data missing or illegible

═══════════════════════════════════════════════════════════════════════════════
RULE 7: ANTI-PATTERNS (CRITICAL MISTAKES TO AVOID)
═══════════════════════════════════════════════════════════════════════════════

❌ NEVER extract supplier name as customer
   (Company in logo/header is NOT the customer)

❌ NEVER merge duplicate article numbers
   (Each table row is a separate line item)

❌ NEVER invent or auto-correct data
   (Extract exactly what you see, use confidence scores)

❌ NEVER use hardcoded company names for identification
   (Use spatial/semantic patterns instead)

❌ NEVER ignore shipping/delivery addresses
   (Highest priority source for customer data)

❌ NEVER include markdown in output
   (Return raw JSON only, no ```json blocks)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE OUTPUTS (showing variety of formats)
═══════════════════════════════════════════════════════════════════════════════

EXAMPLE 1 - English Format (International):
{
  "customer": {
    "company_name": "Global Manufacturing Ltd.",
    "contact_person": "John Smith",
    "email": "j.smith@globalmanuf.com",
    "phone": "+44 20 1234 5678",
    "ico": "GB123456789",
    "confidence": 0.95
  },
  "items": [
    {"article_number": "GM-2026-001", "name": "Steel Bracket Type A", "quantity": 500, "notes": "Material: S235JR", "confidence": 0.98}
  ],
  "valid_until": "2026-04-30",
  "notes": "RFQ: REQ-2026-0042"
}

EXAMPLE 2 - Asian Format (Chinese):
{
  "customer": {
    "company_name": "深圳科技有限公司",
    "contact_person": "张伟",
    "email": "zhang.wei@shenzhentech.cn",
    "phone": "+86 755 1234 5678",
    "ico": "91440300123456789X",
    "confidence": 0.92
  },
  "items": [
    {"article_number": "SZ-A-001", "name": "铝合金外壳", "quantity": 1000, "notes": null, "confidence": 0.95}
  ],
  "valid_until": "2026-05-15",
  "notes": "RFQ: 报价单-2026-0088"
}

EXAMPLE 3 - German Format:
{
  "customer": {
    "company_name": "Maschinenbau Schmidt GmbH",
    "contact_person": "Hans Müller",
    "email": "mueller@schmidt-gmbh.de",
    "phone": "+49 89 1234567",
    "ico": "DE123456789",
    "confidence": 0.97
  },
  "items": [
    {"article_number": "965-621344", "name": "Bolzen", "quantity": 100, "notes": null, "confidence": 0.98},
    {"article_number": "123-456789", "name": "Welle", "quantity": 200, "notes": "Werkstoff: 16MnCr5", "confidence": 0.95}
  ],
  "valid_until": "2026-03-15",
  "notes": "RFQ: ANF-2026-042 | Liefertermin: 4 Wochen"
}

═══════════════════════════════════════════════════════════════════════════════
BEGIN EXTRACTION
═══════════════════════════════════════════════════════════════════════════════

Analyze the provided document using the semantic rules above. Return ONLY the JSON object.
"""


class QuoteRequestParser:
    """OpenAI Vision-based PDF parser"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized parser with {model}")
        except ImportError:
            raise HTTPException(500, "Missing openai package")

    def _pdf_to_images(self, pdf_path: Path) -> list[str]:
        """Convert PDF to base64 PNG images"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise HTTPException(500, "Missing pymupdf package")

        doc = fitz.open(pdf_path)
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(img_base64)

        doc.close()
        return images

    async def parse_pdf(self, pdf_path: Path) -> QuoteRequestExtraction:
        if not pdf_path.exists():
            raise HTTPException(400, f"PDF not found: {pdf_path}")

        # Convert PDF to images
        images = self._pdf_to_images(pdf_path)
        logger.debug(f"Converted PDF to {len(images)} images")

        # Build messages
        content = [{"type": "text", "text": QUOTE_REQUEST_PROMPT}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img}",
                    "detail": "high"
                }
            })

        # Call OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
                timeout=60.0
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API failed: {e}")
            raise HTTPException(500, f"AI parsing failed: {e}")

        # Parse JSON
        try:
            # Strip markdown
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            data = json.loads(response_text)
            extraction = QuoteRequestExtraction.model_validate(data)
            logger.info(f"Parsed: {extraction.customer.company_name}, {len(extraction.items)} items")
            return extraction

        except Exception as e:
            logger.error(f"Parse failed: {e}")
            raise HTTPException(500, f"Failed to parse: {e}")


def get_quote_parser(api_key: Optional[str] = None) -> QuoteRequestParser:
    if api_key is None:
        from app.config import settings
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise HTTPException(500, "OPENAI_API_KEY not configured")
    return QuoteRequestParser(api_key=api_key)
