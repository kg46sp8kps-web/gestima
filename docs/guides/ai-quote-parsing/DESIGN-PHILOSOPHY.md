# AI Quote Parsing — Design Philosophy v2.0

**Date:** 2026-02-02 | **Status:** Implemented

---

## Core Problem

Original prompt was fragile: hardcoded company names, language-specific keywords, specific format examples.
**Solution:** Teach AI document *semantics*, not surface-level syntax.

---

## Key Architectural Decisions

### 1. Semantic over Syntactic
Universal B2B invariant: every document has **Sender** (supplier), **Recipient** (customer), **Transaction**.
These roles are culturally independent — layout and business logic encode them, not keywords.

### 2. Spatial Reasoning — Document Zones

| Zone | Y position | Content | Action |
|------|-----------|---------|--------|
| Header | top 15% | Logo, supplier address | IGNORE for customer |
| Body | middle 40–70% | Ship-to box, item table | EXTRACT customer |
| Footer | bottom 15% | Supplier legal / VAT | IGNORE for customer |

Shipping/delivery address = always customer (business logic invariant, language-agnostic).

### 3. Pattern over Instance

Extract alphanumeric codes near document title, not hardcoded prefixes.
Common patterns: `[PREFIX]-[YEAR]-[NUMBER]`, `[PREFIX][NUMBER]`.
Works for: `P17992`, `ANF-042`, `123/2026`, `2026-0088`.

### 4. Explicit Anti-Patterns (6 critical)

LLMs make *predictable* mistakes. Dedicated "NEVER do X" section cuts systematic errors:
1. Supplier as customer (header/footer confusion)
2. Merging duplicate line items (loses granularity)
3. Inventing data (must use confidence scoring instead)
4. Hardcoded names (prevents overfitting to examples)
5. Ignoring shipping address (highest-confidence source)
6. Markdown output (breaks JSON parsing)

### 5. Confidence Calibration

Uncalibrated confidence is useless. Explicit rubric: text quality × ambiguity × missing fields.
Low confidence must correlate with actual extraction errors (target r > 0.7).

---

## Prompt Strategy

- **Negative examples** are as important as positive
- **3 diverse language examples** (EN, ZH, DE) > 10 Czech examples
- **1,800 tokens** universal prompt > 5 language-specific prompts at 800 tokens each
- Token cost increase (+100%) is negligible vs. maintenance savings (~$4,800/year)

---

## Table Parsing

Column position inference (language-agnostic):
- Leftmost (0–30%): short codes → part identifiers
- Middle (30–70%): longer text → descriptions
- Rightmost (70–100%): numbers only → quantities

RTL languages: flip x-coordinates. Logic stays identical.

---

## Evolution Roadmap

| Level | Feature | Status |
|-------|---------|--------|
| 1 | Semantic prompt + spatial reasoning | Done |
| 2 | Bounding box grounding (UI highlighting) | Next |
| 3 | CV table structure validation | Future |
| 4 | Active learning / per-customer adaptation | Long-term |

---

**Implementation:** `app/services/quote_parse_service.py`
**Prompt:** `app/prompts/quote_parse_prompt.txt`
