# ADR-033: Surface Treatment on MaterialItem [ACCEPTED]
> Archive: docs/ADR/archive/033-surface-treatment-integration.md — Claude může požádat o přečtení

## Rozhodnutí
Surface treatment (P=lisovaný, T=tažená, V=válená...) je fyzická vlastnost MaterialItem — nikoli typ materiálu ani cenová kategorie.

## Pattern
- `app/models/material.py` — `surface_treatment` field na MaterialItem
- `app/services/infor_material_importer.py` — prefix P/T/V parsován z Infor kódu

## Nesmíš
- mapovat surface treatment na MaterialGroup
- zahrnout surface treatment do ceny nebo cenového tieru
- ignorovat prefix při parsování Infor kódů
