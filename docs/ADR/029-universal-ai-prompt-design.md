# ADR-029: Universal AI Prompt Design [ACCEPTED]
> Archive: docs/ADR/archive/029-universal-ai-prompt-design.md — Claude může požádat o přečtení

## Rozhodnutí
Prompt pro parsování poptávek je language/country/format agnostic — funguje pro CZ, DE, EN i jiné B2B formáty.

## Pattern
- `app/services/quote_request_parser.py` — universal prompt bez hardcoded company/language/labels

## Nesmíš
- hardcodeovat češtinu nebo jiný konkrétní jazyk do promptu
- hardcodeovat název firmy (KOVO RYBKA nebo jiný) do promptu
- hardcodeovat konkrétní formáty dokumentů do promptu
