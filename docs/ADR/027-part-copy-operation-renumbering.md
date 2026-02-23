# ADR-027: Part Copy — Operation Renumbering [ACCEPTED]
> Archive: docs/ADR/archive/027-part-copy-operation-renumbering.md — Claude může požádat o přečtení

## Rozhodnutí
Při kopírování dílu se operace renumerují čistě (10, 20, 30...), původní seq čísla se nezachovávají.

## Pattern
- `app/services/part_service.py` — copy method s sequence renumbering

## Nesmíš
- zachovávat původní seq čísla při kopii dílu
- vytvářet gaps v sekvenci (10, 20, 50...)
- přenášet nečistou sekvenci z originálu do kopie
