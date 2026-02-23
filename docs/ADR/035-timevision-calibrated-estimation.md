# ADR-035: TimeVision Calibrated Estimation [ACCEPTED]
> Archive: docs/ADR/archive/035-timevision-calibrated-estimation.md — Claude může požádat o přečtení

## Rozhodnutí
AI odhady se kalibrují dvojicí (human_estimate + actual_time) pro korekční faktor per-material/per-operation-type.

## Pattern
- `app/routers/time_vision_router.py` — calibration endpointy
- `app/services/ft_debug_service.py` — debug + calibration data

## Nesmíš
- brát AI odhad jako finální bez kalibrace
- kalibrovat globálně (ignorovat material/type rozdíly)
- přeskočit kalibraci pro "přesné" odhady
