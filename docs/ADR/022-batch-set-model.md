# ADR-022: BatchSet Model [ACCEPTED]
> Archive: docs/ADR/archive/022-batch-set-model.md — Claude může požádat o přečtení

## Rozhodnutí
Batche lze seskupit do BatchSet pro hromadné zmrazení cen celé pricing family.

## Pattern
- `app/models/batch_set.py` — BatchSet
- `app/routers/batch_sets_router.py`
- `frontend/src/components/tiling/modules/` — BatchSet UI modul

## Nesmíš
- Manuálně zmrazovat každý batch zvlášť pro příbuzné varianty
- Vytvořit BatchSet bez vlastního čísla (35XXXXXX)
