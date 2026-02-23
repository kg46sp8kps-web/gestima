# ADR-047: Fine-Tuning v2 — Technology Builder [PLANNED]
> Archive: docs/ADR/archive/047-ft-v2-technology-builder.md — Claude může požádat o přečtení

## Rozhodnutí
Fine-tuned model (FT v2) se naučí z výkresu generovat kompletní technologický postup (operace, stroje, časy, manning, setup).

## Pattern (planned)
- Tréninková data z Infor importu (ADR-046) + kalibračních dat (ADR-035)
- FT v2 service bude v `app/services/`

## Nesmíš
- spustit FT trénink bez dostatečných kalibračních dat
- ignorovat ADR-035 kalibraci při tvorbě tréninkových dat
- přeskočit validaci výstupu FT v2 modelu
