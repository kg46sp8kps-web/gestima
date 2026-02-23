# ADR-006: Role Hierarchy Pattern [ACCEPTED]
> Archive: docs/ADR/archive/006-role-hierarchy.md — Claude může požádat o přečtení

## Rozhodnutí
Role hierarchy ADMIN > OPERATOR > VIEWER — `require_role([OPERATOR])` automaticky vpustí i ADMIN.

## Pattern
- `app/dependencies.py` — `require_role()` s hierarchickým porovnáním (ne strict equal)

## Nesmíš
- Používat `role == ADMIN` strict check místo hierarchy
- Duplikovat role listy na každém endpointu
