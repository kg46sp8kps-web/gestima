# ADR-043: TimeVision ↔ Technology Module [ACCEPTED]
> Archive: docs/ADR/archive/043-timevision-technology-integration.md — Claude může požádat o přečtení

## Rozhodnutí
TimeVision AI odhad je přístupný přímo v Technology modulu — technolog může čas VOLNĚ editovat, kalibrace je explicitní (ne auto-sync).

## Pattern
- `frontend/src/components/tiling/modules/` — Technology modul s AI ribbon
- `app/routers/time_vision_router.py` — integration endpointy

## Nesmíš
- zamykat AI-odhadnuté časy (technolog musí moct vždy editovat)
- auto-sync kalibraci zpět na estimaci
- skrývat AI zdroj odhadu před uživatelem
