# ADR-028: AI Quote Request Parsing (Claude Vision)

**Status:** Implementovano (Backend + Frontend)
**Date:** 2026-02-01 (aktualizovano 2026-02-02)

---

## Context

Zakaznici posilaji poptavky jako PDF. Rucni prepisovani je pomale (5-10 min/poptavka) a chybove. Potrebujeme AI extrakci strukturovanych dat s lidskou verifikaci pred ulozenim.

---

## Decision

Implementovat AI parsing poptavek pres **Claude Sonnet 4.5** s primym PDF uploaem (bez konverze na obrazky).

### Architektura

```
POST /api/quotes/parse-request   — PDF → QuoteRequestReview (pro overeni uzivatelem)
POST /api/quotes/from-request    — overena data → vytvori Quote v DB
```

Sluzby:
- `app/services/quote_request_parser.py` — Claude API, PDF → strukturovany JSON
- `app/services/quote_service.py` — `find_best_batch()`, `match_part_by_article_number()`

### Klicova rozhodnuti

**A. Claude Sonnet 4.5** (ne OpenAI GPT-4V)
- 3x levnejsi, nativni PDF support, presnejsi na tabulky, 200K kontext

**B. Batch matching strategie: Exact -> Nearest Lower -> Missing**
- EXACT: `batch.quantity == pozadovane_mnozstvi` — status `"exact"`
- LOWER: `max(batch.quantity < pozadovane)` — status `"lower"`, warning uzivateli
- MISSING: zadny frozen batch — status `"missing"`, nutno ocenit rucne
- Nikdy nepouz. vyssi batch (cena by byla nespravne nizka)

**C. `article_number` UNIQUE constraint na Part**
- Migrace: `i1j2k3l4m5n6_add_article_number_unique_constraint.py`
- Umoznuje spolehlivy matching pri AI auto-vytvoreni Part

**D. `customer_request_number` pole na Quote**
- Oddelene od `notes`, indexovane, volitelne
- AI extrahuje: "RFQ: P17992" → `"P17992"`
- Migrace: `j2k3l4m5n6o7_add_customer_request_number_to_quote.py`

**E. Vsechna pole QuoteCreate jsou Optional**
- Uzivatel chtel nulove povinne pole — quote_number (50XXXXXX) staci jako identifikator

**F. Bezpecnost**
- Max 10 MB, PDF magic-bytes check, rate limit 10 req/hod/uzivatel, timeout 30s
- API klic pouze v `.env`, nikdy v kodu

### Schemas (`app/schemas/quote_request.py`)

```
CustomerExtraction  → CustomerMatch  → QuoteFromRequestCreate
ItemExtraction      → PartMatch (part + BatchMatch)
QuoteRequestExtraction → QuoteRequestReview (summary + warnings)
```

---

## Key Files

- `app/services/quote_request_parser.py` — Claude integrace, prompt
- `app/services/quote_service.py` — batch matching, part matching
- `app/schemas/quote_request.py` — Pydantic schemas
- `app/routers/quotes_router.py` — parse-request, from-request endpointy
- `frontend/src/components/modules/QuoteFromRequestPanel.vue` — UI

---

## Consequences

- Quote entry 5-10 min -> 1-2 min (80% uspory)
- ~$0.08/poptavka, max ~$20/mesic pri plnem vyuziti
- Riziko AI halucinaci mitiguje povinny review krok pred ulozenim
- Zavislost na Anthropic API dostupnosti
- Kvalita zavisi na kvalite skenu/PDF

---

## References

- ADR-022: BatchSets (frozen pricing)
- ADR-029: Universal AI Prompt Design (generalizace promptu)
