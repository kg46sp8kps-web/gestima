# Gestima — Operační kontext pro AI

## NESMÍŠ

- Používat smazané/archivované services (viz app/services/archive/)
- Dělat DELETE ALL + INSERT v seed scriptech (rozbije FK)
- Přidávat sem historické záznamy — tento soubor MUSÍ zůstat pod 50 řádků

## MUSÍŠ

- Pro vývoj: `python gestima.py dev` (backend --reload + vite dev, oba auto-refresh)
- Pro produkci: `npm run build` → `python gestima.py run` (bez --reload)
- Seed scripty: UPSERT pattern (UPDATE existing + INSERT new), inline data, idempotentní

## STAV

- v1.29.0 (2026-02-13)
- Fine-tuned model AKTIVNÍ: `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH`
- Kompaktní prompt pro FT model (bez referenčních tabulek), plný prompt pro base
- ai_provider: `openai_ft` (fine-tuned) nebo `openai` (base)
- Claude pipeline KOMPLETNĚ ODSTRANĚN (archivováno v app/services/archive/)
- Anthropic SDK/API key ODSTRANĚN z projektu
- Conda/pythonocc/OCCT KOMPLETNĚ ODSTRANĚNY (step_raw_extractor, step_parser smazány)

## MATERIÁLOVÝ IMPORT

- Infor item → W.Nr extraction → MaterialNorm → MaterialGroup → Shape → PriceCategory
- PriceCategory matching přes `shape` sloupec (ne keyword matching)
- Chybějící PriceCategory = ERROR (import blokován, ne tichý fallback)
- Seed data: 9 groups, 82 norms, 43 categories (se shape), 129 tiers, 288 cutting conditions

## TECH DEBT

- 4 komponenty > 300 LOC
- 17 pre-existing TS errors
- A/B test base vs fine-tuned zatím neproveden
