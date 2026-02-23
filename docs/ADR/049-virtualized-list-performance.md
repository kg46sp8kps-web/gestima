# ADR-049: Virtualized List Performance [ACCEPTED — MANDATORY]
> Archive: docs/ADR/archive/049-virtualized-list-performance.md — Claude může požádat o přečtení

## Rozhodnutí
List moduly s potenciálem >100 položek MUSÍ používat virtualizovaný scroll + server-side pagination.

## Pattern
- Vue Virtual Scroller nebo custom virtual list v list komponentách
- Pagination `skip`+`limit` na API endpointech, max 100 na stránku
- Cache pro re-otevření modulu (neznovu-fetchuj při každém otevření)

## Nesmíš
- DataTable bez limitu na velký dataset
- `limit=9999` jako workaround pro pagination
- synchronní unmount >500 DOM nodů
