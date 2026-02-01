# ADR-028: AI Quote Request Parsing with Claude Vision

**Status:** ✅ Implemented
**Date:** 2026-02-01
**Author:** Development Team
**Version:** 1.13.0

---

## Context

Customers send quote requests (poptávky) as PDF documents containing:
- Customer information (company, contact, email, phone, ICO)
- List of parts with quantities (can have multiple rows for same part)
- Delivery deadline

Manual entry of this data is time-consuming and error-prone. We need an AI-powered solution to:
1. Extract structured data from PDF quote requests
2. Match existing customers (Partners) and parts
3. Auto-create Quote with items pre-filled
4. Maintain human verification step (no blind automation)

---

## Decision

Implement **AI-powered quote request parsing** using **Claude 3.5 Sonnet Vision API** with the following architecture:

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (Future - not yet implemented)                      │
│ - QuoteNewFromRequestView.vue                                │
│ - Upload PDF → Review extracted data → Create Quote          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend API (Implemented)                                    │
│                                                               │
│ POST /api/quotes/parse-request                               │
│ - Upload PDF (max 10MB)                                      │
│ - Claude Vision extracts: customer + items[]                 │
│ - Match existing Parts (by article_number)                   │
│ - Match existing Partner (by name + ICO/email)               │
│ - Match Batches (exact → nearest lower → missing)            │
│ - Returns: QuoteRequestReview (for user verification)        │
│                                                               │
│ POST /api/quotes/from-request                                │
│ - Create/match Partner                                       │
│ - Create missing Parts (article_number + name only)          │
│ - Create Quote (DRAFT status)                                │
│ - Create QuoteItems (with pricing from matched batches)      │
│ - Returns: Created Quote                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Services Layer                                               │
│                                                               │
│ QuoteRequestParser (app/services/quote_request_parser.py)    │
│ - Claude API integration                                     │
│ - PDF → base64 → structured JSON                             │
│ - Prompt engineering for Czech B2B quotes                    │
│ - Error handling + confidence scoring                        │
│                                                               │
│ QuoteService (app/services/quote_service.py)                 │
│ - find_best_batch() - exact/lower/missing matching           │
│ - match_part_by_article_number() - Part matching             │
│ - match_item() - Combined part + batch matching              │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### 1. AI Provider: Claude 3.5 Sonnet

**Why Claude over OpenAI Vision?**
- ✅ **3× cheaper** ($3/MTok vs $10/MTok for vision input)
- ✅ **Better structured output** (native JSON schema support)
- ✅ **Better table extraction** (critical for Czech quote forms)
- ✅ **Native PDF support** (no conversion to images needed)
- ✅ **200K context** (can handle large multi-page PDFs)
- ✅ **Easy to switch** later if needed (abstraction in place)

**Cost estimate:**
- 10-page PDF ≈ 20K tokens input + 1K tokens output
- Cost: ~$0.08 per parse
- With 10/hour rate limit: max ~$20/month at full usage

### 2. Key Technical Decisions

#### A. article_number as UNIQUE constraint

**Decision:** Added UNIQUE constraint on `Part.article_number`

**Rationale:**
- AI matching requires reliable unique identifier
- Part.part_number (10XXXXXX) is internal, article_number is external
- Prevents duplicates during AI auto-creation
- Aligns with business logic (one article_number = one part)

**Migration:** `i1j2k3l4m5n6_add_article_number_unique_constraint.py`

**Impact:**
- ✅ Reliable Part matching in AI workflow
- ✅ Prevents duplicate part creation
- ⚠️ Breaks if existing DB has duplicate article_numbers (clean up first)

#### B. Batch Matching Strategy: Exact → Nearest Lower → Missing

**Decision:** When matching quantity to batch, use this hierarchy:

1. **EXACT MATCH** (preferred)
   - `batch.quantity == requested_quantity`
   - Status: `"exact"`, confidence: 100%

2. **NEAREST LOWER** (fallback)
   - `batch.quantity < requested_quantity`
   - Use: `max(lower_batches)`
   - Status: `"lower"`, warning: ⚠️ "Použita dávka 10ks místo 50ks"

3. **MISSING** (no match)
   - No frozen batch exists
   - Status: `"missing"`, error: 🔴 "Díl nemá zmrazenou kalkulaci"

**Rationale:**
- User preference: NEVER use higher batch (price would be wrong)
- Lower batch = conservative estimate (higher unit price → safer quote)
- Missing = explicit warning, user must price manually

**Example:**
```python
Part ABC-123 has frozen batches: 1ks, 10ks, 100ks, 500ks
PDF requests:
- 100 ks → ✅ Exact (100ks batch)
- 50 ks  → ⚠️ Lower (10ks batch, warning)
- 5 ks   → 🔴 Missing (no batch ≤5, error)
```

#### C. Customer Matching: Multi-Strategy

**Decision:** Match Partner using priority cascade:

1. **company_name + ICO** (best, 100% confidence)
2. **company_name + email** (high, 95% confidence)
3. **company_name only** (fallback, 80% confidence)

**Rationale:**
- Handles edge cases: "Gelso AG" (Germany) vs "Gelso DE" (different ICO/email)
- Most customers are unique by name, but ICO/email provides safety
- User typically has unique customers, but system is robust

**Fallback:** Create new Partner if no match (user verifies in UI)

#### D. Security & Cost Controls

**Implemented protections:**

1. **File size limit:** 10 MB max (HTTP 413 if larger)
2. **Rate limiting:** 10 requests/hour per user (`@limiter.limit`)
3. **Timeout:** 30 seconds on Claude API call
4. **File type validation:** PDF only (magic bytes check)
5. **API key protection:** Never committed, stored in `.env`

**Cost control strategy:**
- Rate limit prevents spam/abuse
- Max cost: ~$0.80/hour per user at full usage
- No caching yet (future enhancement)

---

## Data Flow

### Parse Request Flow

```
1. User uploads PDF (max 10MB)
   ↓
2. Validate file (type, size)
   ↓
3. Save to temp storage (UUID filename)
   ↓
4. Call Claude Vision API (timeout: 30s)
   - PDF → base64
   - Structured prompt (Czech B2B quote format)
   - Response: JSON with customer + items[]
   ↓
5. Parse & validate JSON (Pydantic schemas)
   ↓
6. Match customer → Partner (3-strategy cascade)
   ↓
7. For each item:
   - Match article_number → Part
   - If Part exists: find_best_batch()
   - Calculate pricing (unit_price × quantity)
   ↓
8. Build QuoteRequestReview
   - customer: CustomerMatch
   - items: PartMatch[] (with batch info)
   - summary: totals, warnings, confidence
   ↓
9. Return JSON to frontend (for user review)
   ↓
10. Cleanup temp file
```

### Create Quote Flow

```
1. User reviews extracted data (frontend - not yet implemented)
   - Edits fields as needed
   - Confirms customer match or creates new
   ↓
2. POST /api/quotes/from-request
   ↓
3. Create/match Partner
   - If partner_id null: create new Partner (70XXXXXX)
   ↓
4. Create missing Parts
   - If part_id null: create new Part (10XXXXXX)
   - Fields: article_number, name, revision="A", status="draft"
   ↓
5. Create Quote (50XXXXXX)
   - Status: DRAFT
   - Fields: partner_id, title, valid_until, notes
   ↓
6. Create QuoteItems
   - For each item: part_id, quantity, unit_price (from batch match)
   - Denormalize: part_number, part_name
   ↓
7. Recalculate quote totals
   - subtotal, discount, tax, total
   ↓
8. Commit transaction
   ↓
9. Return created Quote
```

---

## Schema Design

### Pydantic Schemas (app/schemas/quote_request.py)

```python
# AI Extraction (from Claude)
CustomerExtraction
  - company_name, contact_person, email, phone, ico
  - confidence: float (0.0-1.0)

ItemExtraction
  - article_number, name, quantity, notes
  - confidence: float

QuoteRequestExtraction
  - customer: CustomerExtraction
  - items: ItemExtraction[]
  - valid_until, notes

# Matching Results (after DB lookup)
CustomerMatch
  - company_name, contact_person, email, phone, ico
  - partner_id, partner_number, partner_exists
  - match_confidence: float

BatchMatch
  - batch_id, batch_quantity
  - status: "exact" | "lower" | "missing"
  - unit_price, line_total
  - warnings: string[]

PartMatch
  - part_id, part_number, part_exists
  - article_number, name, quantity, notes
  - batch_match: BatchMatch

QuoteRequestReview (final output)
  - customer: CustomerMatch
  - items: PartMatch[]
  - valid_until, notes
  - summary: total_items, unique_parts, matched_parts, new_parts, missing_batches

# Quote Creation Input
QuoteFromRequestCreate
  - partner_id (or partner_data for new)
  - items: [{part_id, article_number, name, quantity, notes}]
  - title, valid_until, notes, discount_percent, tax_percent
```

---

## Alternatives Considered

### 1. OpenAI Vision vs Claude

**OpenAI GPT-4V:**
- ❌ 3× more expensive
- ❌ Requires PDF → image conversion
- ❌ Less accurate for tables
- ✅ Higher rate limits (but we don't need them)

**Decision:** Claude for cost + accuracy

### 2. Manual Entry vs AI

**Keeping manual entry:**
- ✅ Zero AI cost
- ❌ Slow (5-10 minutes per quote)
- ❌ Error-prone (typos in article numbers)

**Decision:** AI with human verification = best of both worlds

### 3. Full Automation vs Human-in-Loop

**Full automation (no verification):**
- ❌ Too risky (AI hallucination)
- ❌ User loses control

**Decision:** Human-in-loop = user reviews & edits before commit

### 4. Batch Matching: Lower vs Higher

**Using nearest HIGHER batch:**
- ❌ Wrong pricing (50ks quoted with 100ks batch price = too cheap!)
- ❌ User explicitly requested LOWER

**Decision:** Nearest LOWER = conservative, safer

---

## Consequences

### Positive

✅ **Faster quote entry** - 5-10 min → 1-2 min (80% time saved)
✅ **Fewer typos** - AI reads article numbers accurately
✅ **Batch matching** - Auto-finds correct pricing tier
✅ **Cost effective** - ~$0.08/quote vs manual labor cost
✅ **Scalable** - Can handle high quote volume
✅ **Extensible** - Easy to switch AI providers later

### Negative

⚠️ **AI hallucination risk** - Must verify all data (mitigated by UI review)
⚠️ **Ongoing cost** - $20/month at full usage (acceptable for value)
⚠️ **API dependency** - Requires Anthropic service availability
⚠️ **PDF quality dependent** - Poor scans = poor results

### Neutral

- Frontend not yet implemented (backend ready)
- No caching yet (future enhancement)
- Rate limit may need tuning based on usage patterns

---

## Migration Path

### Phase 1: Backend Implementation ✅ DONE
- [x] Claude parser service
- [x] Batch matching logic
- [x] API endpoints (parse-request, from-request)
- [x] Security controls (rate limit, file size, timeout)
- [x] article_number UNIQUE constraint

### Phase 2: Frontend Implementation ⏳ TODO
- [ ] QuoteNewFromRequestView.vue
- [ ] PDF upload component
- [ ] Review/edit extracted data UI
- [ ] Customer matching dropdown
- [ ] Items table (grouped by article_number)
- [ ] Batch status indicators (✅/⚠️/🔴)

### Phase 3: Enhancements 🔮 FUTURE
- [ ] Caching (by PDF hash, 1 hour TTL)
- [ ] Fuzzy customer matching (difflib/fuzzywuzzy)
- [ ] Multi-page table parsing improvements
- [ ] Drawing extraction from quote PDF
- [ ] Analytics dashboard (AI accuracy tracking)

---

## Monitoring & Metrics

### Success Metrics

**Target KPIs:**
- Quote entry time: <2 minutes (currently ~8 minutes manual)
- AI accuracy: >90% for article numbers (critical field)
- Customer match rate: >80% (existing customers)
- Part match rate: varies (depends on quote novelty)

**Tracking:**
- Log all AI extractions with confidence scores
- Track user edits (what did AI get wrong?)
- Monitor API costs (Anthropic usage)
- Rate limit hits (do we need to increase?)

### Error Handling

**API failures:**
- Claude timeout → HTTP 500, user sees error, can retry
- Invalid JSON → HTTP 500, logged for prompt improvement
- Rate limit exceeded → HTTP 429, user sees "Try again in X minutes"

**Data quality:**
- Low confidence fields → highlighted in UI (future)
- Missing required fields → blocked from submission
- Duplicate article_number → HTTP 409 (UNIQUE constraint)

---

## Security Considerations

### API Key Management

- ✅ Stored in `.env` (never committed)
- ✅ Loaded via pydantic-settings
- ✅ No default fallback (fails if missing)

### Rate Limiting

- ✅ 10 requests/hour per user (configurable: `AI_RATE_LIMIT`)
- ✅ Tracked by user_id (authenticated users only)
- ✅ Prevents abuse/cost explosion

### File Validation

- ✅ PDF magic bytes check (not just MIME type)
- ✅ 10 MB max file size
- ✅ Temp file cleanup (even on error)
- ✅ Path traversal prevention (UUID filenames)

### Data Privacy

- ⚠️ PDF sent to Anthropic (third-party)
- ⚠️ Ensure compliance with data processing agreements
- ⚠️ Customer PII (names, emails, ICO) in AI requests
- ✅ No storage of raw PDFs (deleted after parse)
- ✅ Audit log of AI extractions (who parsed what, when)

---

## Testing Strategy

### Unit Tests ⏳ TODO

- [ ] QuoteRequestParser.parse_pdf() with mock Claude responses
- [ ] find_best_batch() with various batch configurations
- [ ] match_part_by_article_number() edge cases
- [ ] Customer matching strategies

### Integration Tests ⏳ TODO

- [ ] Full flow: PDF upload → parse → create quote
- [ ] Rate limiting enforcement
- [ ] File size validation
- [ ] Timeout handling

### Manual Testing ✅ DONE (during development)

- [x] Code review
- [x] Logic analysis for gaps
- [x] Security review

---

## References

- **Claude API Docs:** https://docs.anthropic.com/claude/reference
- **Anthropic Pricing:** https://www.anthropic.com/pricing
- **Related ADRs:**
  - ADR-008: Optimistic Locking
  - ADR-022: BatchSets (Frozen Pricing)
  - VIS-002: Quotes Workflow & Snapshots

---

## Changelog

- **2026-02-01:** Initial implementation (v1.13.0)
  - Backend complete (parse-request, from-request endpoints)
  - Security controls (rate limit, file size, timeout)
  - article_number UNIQUE constraint
  - Frontend pending

---

**Status:** ✅ Backend Implemented, Frontend Pending
**Next Steps:** Frontend implementation (QuoteNewFromRequestView.vue)
