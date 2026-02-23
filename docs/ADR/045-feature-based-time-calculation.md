# ADR-045: Feature-Based Deterministic Time Calculation [ACCEPTED]
> Archive: docs/ADR/archive/045-feature-based-time-calculation.md — Claude může požádat o přečtení

## Rozhodnutí
Deterministický výpočet strojních časů z CNC prvků (features: díry, průměry, závity) místo AI black-box odhadu.

## Pattern
- `app/services/feature_calculator.py` — per-feature time rules
- `app/models/` — Feature model (typ, počet, detail)

## Nesmíš
- používat AI pro výpočty kde existují deterministická pravidla
- počítat jeden globální čas bez feature breakdown
- ignorovat typ a počet features při kalkulaci
