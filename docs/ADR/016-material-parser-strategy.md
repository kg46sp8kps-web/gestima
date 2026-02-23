# ADR-016: Material Parser Strategy — 3-Phase [PARTIAL — fáze 1/3 hotová]
> Archive: docs/ADR/archive/016-material-parser-strategy.md — Claude může požádat o přečtení

## Rozhodnutí
3-fázový material search: Regex (DONE) → Fuzzy (PLANNED) → AI (PLANNED).

## Pattern
- `app/services/material_parser.py` — regex parser pro "D20 C45 100mm", "t2 S235" formáty
- Fáze 2-3 zatím neimplementovány

## Nesmíš
- Přeskočit regex a jít rovnou na AI (zbytečné náklady na jednoduché queries)
- Implementovat fáze 2-3 bez dokončení a testování fáze 1
