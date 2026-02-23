# ADR-011: Material Hierarchy — Two-Tier Model [ACCEPTED]
> Archive: docs/ADR/archive/011-material-hierarchy.md — Claude může požádat o přečtení

## Rozhodnutí
Dvoustupňová hierarchie: MaterialGroup (typ + hustota + řezné podmínky) → MaterialItem (konkrétní polotovar s rozměry).

## Pattern
- `app/models/material.py` — `MaterialGroup`, `MaterialItem`
- `app/models/material_norm.py` — auto-mapování norem (W.Nr/EN ISO/ČSN/AISI) na MaterialGroup

## Nesmíš
- Ukládat hustotu na MaterialItem (patří na MaterialGroup)
- Přeskakovat MaterialGroup vrstvu
- Používat flat seznam materiálů bez hierarchie
