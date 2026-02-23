# ADR-018: Dev/Prod Deployment Strategy [ACCEPTED]
> Archive: docs/ADR/archive/018-deployment-strategy.md — Claude může požádat o přečtení

## Rozhodnutí
Dev = lokální (`gestima.py dev`), prod = Raspberry Pi za Caddy, SQLite bez síťového přístupu — vývojář pracuje lokálně bez VPN.

## Pattern
- `gestima.py` — dev server manager (backend + frontend watch)
- `Caddyfile` — prod config
- `.env` — environment switch (DEV/PROD)

## Nesmíš
- Sdílet SQLite přes síť
- Spouštět dev server na produkčním serveru
