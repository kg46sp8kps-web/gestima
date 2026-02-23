# ADR-014: Material Price Tiers [ACCEPTED]
> Archive: docs/ADR/archive/014-material-price-tiers.md — Claude může požádat o přečtení

## Rozhodnutí
Ceny materiálů jsou tier-based podle hmotnosti dávky — `MAX(tier.min_weight) WHERE min_weight <= batch.total_weight_kg`.

## Pattern
- `app/models/material.py` — `MaterialPriceCategory`, `MaterialPriceTier`
- Výpočet ceny VÝHRADNĚ na backendu v `app/services/`

## Nesmíš
- Používat flat `price_per_kg` na MaterialItem
- Počítat cenu materiálu na frontendu
