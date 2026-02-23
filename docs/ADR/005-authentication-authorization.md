# ADR-005: Authentication & Authorization [ACCEPTED]
> Archive: docs/ADR/archive/005-authentication-authorization.md — Claude může požádat o přečtení

## Rozhodnutí
JWT auth přes FastAPI Depends — každý endpoint MUSÍ mít auth dependency.

## Pattern
- `app/dependencies.py` — `get_current_user` (read)
- `app/dependencies.py` — `require_role([ADMIN, OPERATOR])` (write)
- `app/dependencies.py` — `require_role([ADMIN])` (admin-only)

## Nesmíš
- Vytvořit endpoint bez auth dependency
- Dělat role check v business logice místo v dependency
