# ADR-007: HTTPS s Caddy reverse proxy [ACCEPTED]
> Archive: docs/ADR/archive/007-https-caddy.md — Claude může požádat o přečtení

## Rozhodnutí
V produkci Caddy jako reverse proxy před FastAPI — automatické HTTPS, HttpOnly+Secure cookies.

## Pattern
- `Caddyfile` — HTTPS terminace (deployment config)
- Dev běží bez HTTPS na localhost (FastAPI přímo)

## Nesmíš
- Vystavit FastAPI přímo na port 80/443 v produkci
- Používat self-signed certs
