# ADR-015: Material Norm Auto-Mapping [ACCEPTED]
> Archive: docs/ADR/archive/015-material-norm-mapping.md — Claude může požádat o přečtení

## Rozhodnutí
MaterialNorm tabulka automaticky mapuje normy (W.Nr, EN ISO, ČSN, AISI) na MaterialGroup — case-insensitive search across 4 sloupců.

## Pattern
- `app/models/material_norm.py` — `MaterialNorm` (4 norm columns + material_group_id FK)
- `app/services/` — norm lookup při importu i při zadávání uživatelem

## Nesmíš
- Mapovat normy hardcoded dict v kódu
- Používat case-sensitive vyhledávání norem
