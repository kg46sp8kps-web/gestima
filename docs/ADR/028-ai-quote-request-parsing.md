# ADR-028: AI Quote Request Parsing [ACCEPTED]
> Archive: docs/ADR/archive/028-ai-quote-request-parsing.md — Claude může požádat o přečtení

## Rozhodnutí
Claude Vision API extrahuje strukturovaná data z PDF poptávky — uživatel MUSÍ data verifikovat před uložením.

## Pattern
- `app/services/quote_request_parser.py` — Claude API call + structured extraction
- Frontend — verifikační dialog před uložením dat

## Nesmíš
- auto-ukládat AI výsledky bez human review
- parsovat PDF text bez Vision (PDF = obrázek)
- přeskočit verifikační krok pro "jednoduché" poptávky
