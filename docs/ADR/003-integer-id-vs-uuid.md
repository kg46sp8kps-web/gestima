# ADR-003: Integer ID vs UUID [ACCEPTED]
> Archive: docs/ADR/archive/003-integer-id-vs-uuid.md — Claude může požádat o přečtení

## Rozhodnutí
Primární klíče jsou Integer (auto-increment), ne UUID — jednodušší dotazy, FK joins, snadná migrace.

## Pattern
- Všechny modely v `app/models/` — `id = Column(Integer, primary_key=True)`

## Nesmíš
- Používat UUID primary keys
- Používat string IDs jako PK
