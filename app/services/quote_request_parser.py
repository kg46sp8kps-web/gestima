"""GESTIMA - Quote Request Parser (Claude AI)

Parses quote request PDFs using Claude AI Sonnet 4.5 Vision API.

Features:
- Direct PDF upload → structured JSON extraction
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


# Claude AI prompt for quote request extraction
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
      "drawing_number": "string | null (drawing/výkres number if present - SEPARATE from article_number)",
      "name": "string (REQUIRED - part description/title)",
      "quantity": integer (REQUIRED - must be positive integer)",
      "notes": "string | null (technical specs, material codes, special requirements)",
      "confidence": 0.0-1.0
    }
  ],
  "customer_request_number": "string | null (RFQ/Poptávka number from customer - extract ONLY the identifier)",
  "valid_until": "YYYY-MM-DD | null (quote validity deadline)",
  "notes": "string | null (delivery terms, general remarks - NOT RFQ number)"
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

A) PRIORITY SEARCH ORDER (apply from top to bottom, stop at first match):

   **PRIORITY 1: Explicit "Buyer" / "Customer" labels** (HIGHEST)
   - Look for fields explicitly labeled: "Buyer:", "Customer:", "Client:", "Requestor:"
   - Common in RFQ documents where entity REQUESTING the quote is clearly marked
   - Email domains near "Buyer:" field indicate customer organization
   - Extract company from same section as buyer email/contact
   → IF FOUND: This is the CUSTOMER (ignore all other sections)

   **PRIORITY 2: Sender/From in RFQ context** (HIGH)
   - If document title is "Request for Quotation" / "RFQ" / "Poptávka"
   - AND sender/from company is NOT in shipping address
   - Then sender is the CUSTOMER (they are requesting the quote)
   → The entity SENDING the RFQ is the BUYER

   **PRIORITY 3: Shipping address** (MEDIUM)
   - "Shipping address:", "Ship to:", "Delivery address:", "Dodací adresa:"
   - WARNING: In RFQ documents, shipping address may be the SUPPLIER (receiving party)
   - Cross-check: If shipping address matches header/footer company → It's the SUPPLIER (ignore)
   - Only use if NOT matching document creator
   → Use with caution in RFQ context

   **PRIORITY 4: Spatial zones** (FALLBACK)
   ┌─────────────────────────────────────────────────────────────┐
   │ HEADER ZONE (top 15% of page)                               │
   │ - Company logos, letterhead                                 │
   │ → Usually SUPPLIER (but check RFQ context)                  │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │ BODY ZONE (middle 40-70% of page)                           │
   │ - Main content, contact blocks                              │
   │ → Context-dependent                                         │
   └─────────────────────────────────────────────────────────────┘

B) SEMANTIC ROLE MARKERS (use for validation):

   CUSTOMER indicators:
   - "Buyer:", "Client:", "Requestor:" (STRONGEST)
   - Email contact in document body (not header/footer)
   - "Bill to:" address (who pays)
   - Company associated with RFQ sender in RFQ documents

   SUPPLIER indicators (IGNORE):
   - Company in logo/header/footer
   - "Shipping address:" IF it matches header company
   - Watermarks, bank details in footer
   - Tax IDs in document footer

C) BUSINESS LOGIC VALIDATION:

   **For RFQ (Request for Quotation) documents:**
   - Entity labeled "Buyer:" = CUSTOMER (they want the quote)
   - Entity in header/footer = SUPPLIER (they create the quote)
   - Shipping address in RFQ often = SUPPLIER (where to ship FROM, not TO)
   - Double-check: Buyer email domain should match customer company

   **For regular quote requests:**
   - "Attention:", "ATTN:", "致:" near name → Usually CUSTOMER contact
   - Company in logo repeated 3+ times → SUPPLIER (ignore)
   - Billing/invoicing address → CUSTOMER (who pays)

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
3. Store ONLY the identifier in "customer_request_number" field (NOT in notes)
4. Do NOT include "RFQ:" prefix in customer_request_number - just the number/code itself
5. Store other remarks (delivery terms, payment terms, etc.) separately in "notes" field

═══════════════════════════════════════════════════════════════════════════════
RULE 4: ITEMS TABLE EXTRACTION (STRUCTURE-BASED)
═══════════════════════════════════════════════════════════════════════════════

TABLE IDENTIFICATION (visual patterns):
- Grid structure with visible/implicit borders
- Header row: Bold text or background color
- Repeated row pattern (3+ rows with similar structure)
- Typically occupies 30-60% of page vertically

COLUMN SEMANTICS (position-based, language-agnostic):

COLUMN SEMANTICS (position-based, language-agnostic):

LEFT COLUMNS (leftmost 30%):
→ Part identifiers, descriptions
→ May include SKUs in brackets: [byn-10101251]
→ May include part names: "Halter", "Bolzen"

MIDDLE COLUMNS (center 40%):
→ Additional specifications, scaled prices
→ Technical details

RIGHT COLUMNS (rightmost 30%):
→ Quantities with units
→ Labels (ignore): "Qty", "Ks", "Pcs", "Units", "個", "数量"

CRITICAL: ARTICLE NUMBER + DRAWING NUMBER EXTRACTION

**PRIORITY 1: Article Number / Part Number / SKU** (HIGHEST - PRIMARY IDENTIFIER)
- Labels: "Article:", "Article No.:", "Part No.:", "SKU:", "Artikl:", "Díl č.:", "部品番号:", "零件号:"
- Format: [byn-10101251], ABC-123, Part-XYZ, 10101251
- Position: Usually in LEFT columns or first column of table
- Often in brackets, dashes, or standalone codes
- Action: Extract as "article_number" → This is the PRIMARY identifier

**PRIORITY 2: Drawing Number** (SEPARATE FIELD - always extract if present)
- Labels: "Drawing:", "Drawing No.:", "Výkres:", "図面:", "图纸:"
- Format: "Drawing: 90057637-00", "Výkres č. 123456"
- Position: Usually BELOW part description in same row OR in separate column
- Action: Extract as SEPARATE "drawing_number" field (do NOT merge with article_number)
- If found: Extract to "drawing_number" field
- If not found: Leave "drawing_number" as null

**EXTRACTION RULES:**

1. **Article Number (Artikl / Part Number) - CRITICAL PRIMARY IDENTIFIER**:
   - FIRST: Look for "Article:", "Part No.:", "SKU:", "Artikl:" labels
   - SECOND: Look for alphanumeric codes in brackets or with dashes ([byn-10101251], ABC-123)
   - THIRD (FALLBACK): If Article/Part/SKU NOT found → Use "Drawing:" number AND add warning to notes
   - Copy EXACTLY character-by-character: preserve dashes, dots, spaces, case, brackets
   - Examples: "[byn-10101251]", "965-621344", "ABC.123.XY", "10101251"
   - If using Drawing Number fallback: Add warning to notes field

2. **Drawing Number - SEPARATE FIELD (always extract if present)**:
   - Extract to "drawing_number" field (SEPARATE from article_number)
   - Copy EXACTLY as written: "90057637-00", "ABC-123-REV-A"
   - If both Article Number AND Drawing Number are present → Extract BOTH to separate fields
   - If only Drawing Number found → Use it for article_number AND drawing_number with warning

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

EXAMPLE 1 - RFQ with Article Numbers (PRIMARY):
{
  "customer": {
    "company_name": "GELSO AG",
    "contact_person": "Roko Paskov",
    "email": "roko.paskov@gelso.ch",
    "phone": "+41 44 840 33 40",
    "ico": "CHE-108.413.346",
    "confidence": 0.95
  },
  "items": [
    {"article_number": "byn-10101251", "name": "Halter", "quantity": 1, "notes": "Drawing: 90057637-00 | Scaled prices: 1/5/10/20", "confidence": 0.98},
    {"article_number": "byn-10101263-01", "name": "Halter", "quantity": 1, "notes": "Drawing: 90057543-01 | Scaled prices: 1/5/10/20", "confidence": 0.98}
  ],
  "customer_request_number": "P20971",
  "valid_until": "2025-12-22",
  "notes": "Incoterm: FCA | Payment: 10 days net"
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
  "customer_request_number": "报价单-2026-0088",
  "valid_until": "2026-05-15",
  "notes": null
}

EXAMPLE 3 - German Format (Article Number primary):
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
  "customer_request_number": "ANF-2026-042",
  "valid_until": "2026-03-15",
  "notes": "Liefertermin: 4 Wochen"
}

EXAMPLE 4 - Drawing Number Fallback (with warning):
{
  "customer": {
    "company_name": "TechParts Ltd",
    "contact_person": "John Smith",
    "email": "j.smith@techparts.com",
    "phone": "+44 20 1234 5678",
    "ico": "GB123456789",
    "confidence": 0.92
  },
  "items": [
    {"article_number": "DWG-2026-001", "name": "Mounting Bracket", "quantity": 50, "notes": "⚠️ Parsed from Drawing Number (Article Number not found)", "confidence": 0.85}
  ],
  "customer_request_number": "RFQ-UK-2026-99",
  "valid_until": "2026-04-01",
  "notes": null
}

═══════════════════════════════════════════════════════════════════════════════
BEGIN EXTRACTION
═══════════════════════════════════════════════════════════════════════════════

Analyze the provided document using the semantic rules above. Return ONLY the JSON object.
"""


class QuoteRequestParser:
    """Claude AI Vision-based PDF parser"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.model = model
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            logger.info(f"Initialized parser with Claude {model}")
        except ImportError:
            raise HTTPException(500, "Missing anthropic package")

    def _load_pdf(self, pdf_path: Path) -> str:
        """Load PDF as base64 for direct upload to Claude"""
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            return base64.b64encode(pdf_bytes).decode('utf-8')

    async def parse_pdf(self, pdf_path: Path) -> QuoteRequestExtraction:
        if not pdf_path.exists():
            raise HTTPException(400, f"PDF not found: {pdf_path}")

        # Load PDF for direct upload to Claude
        pdf_base64 = self._load_pdf(pdf_path)
        logger.debug(f"Loaded PDF ({len(pdf_base64)} bytes base64) for direct upload")

        # Build messages for Claude with direct PDF upload
        content = [
            {"type": "text", "text": QUOTE_REQUEST_PROMPT},
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_base64
                }
            }
        ]

        # Call Claude AI
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": content}]
            )
            response_text = response.content[0].text
        except Exception as e:
            logger.error(f"Claude API failed: {e}")
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
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise HTTPException(500, "ANTHROPIC_API_KEY not configured")
    return QuoteRequestParser(api_key=api_key)
