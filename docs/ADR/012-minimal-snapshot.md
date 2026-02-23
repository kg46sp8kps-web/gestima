# ADR-012: Minimal Snapshot Pattern [ACCEPTED]
> Archive: docs/ADR/archive/012-minimal-snapshot.md — Claude může požádat o přečtení

## Rozhodnutí
Zmrazení Batche ukládá pouze finální ceny do JSON pole `snapshot_data` — ne kopii celé struktury dílu.

## Pattern
- `app/models/batch.py` — `snapshot_data` (JSON field)
- `app/services/batch_service.py` — freeze logic zapisuje do snapshot_data

## Nesmíš
- Referencovat aktuální sazby z historického (frozen) batche
- Ukládat full-copy snapshot celého dílu + operací
