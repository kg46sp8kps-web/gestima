# ADR-017: 8-Digit Entity Numbering [ACCEPTED]
> Archive: docs/ADR/archive/017-8digit-entity-numbering.md — Claude může požádat o přečtení

## Rozhodnutí
User-facing IDs jsou 8-místné s 2-místným prefixem [PP][XXXXXX]: Parts=10, Materials=20, Batches=30, BatchSets=35, Quotes=50, Partners=70, WorkCenters=80.

## Pattern
- `app/services/number_generator.py` — generování při create

## Nesmíš
- Používat auto-increment INT jako user-facing číslo
- Používat jiný prefix nebo formát
- Duplikovat číslo v rámci stejného prefixu
