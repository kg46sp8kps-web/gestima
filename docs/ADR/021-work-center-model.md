# ADR-021: WorkCenter Model [ACCEPTED]
> Archive: docs/ADR/archive/021-work-center-model.md — Claude může požádat o přečtení

## Rozhodnutí
WorkCenter entita s hodinovými sazbami, 8-digit číslování (80XXXXXX), soft delete.

## Pattern
- `app/models/work_center.py` — WorkCenter
- `app/routers/work_centers_router.py`

## Nesmíš
- Hardcodeovat work center IDs v kódu
- Ukládat sazby přímo na Operation (musí být přes WorkCenter FK)
