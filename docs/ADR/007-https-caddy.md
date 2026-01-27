# ADR-007: HTTPS s Caddy reverse proxy

## Status
**Accepted** (2026-01-23)

## Kontext
P0 requirement: Aplikace musí běžet přes HTTPS v produkci pro:
- Bezpečný přenos credentials (login)
- Secure cookies (HttpOnly + Secure flag)
- Ochrana dat v přenosu

## Rozhodnutí
**Caddy** jako reverse proxy před FastAPI aplikací.

### Důvody:
1. **Automatické HTTPS** - Let's Encrypt certifikáty bez konfigurace
2. **Zero-downtime renewal** - automatická obnova certifikátů
3. **Minimální konfigurace** - jednoduchý Caddyfile
4. **Production-ready** - používáno v produkci mnoha projekty

### Alternativy (zamítnuté):
| Možnost | Důvod zamítnutí |
|---------|-----------------|
| Nginx + certbot | Více konfigurace, manuální renewal |
| Uvicorn SSL | Nedoporučeno pro produkci, komplikovaná správa certů |
| Traefik | Overkill pro single-server SQLite app |

## Implementace

### 1. Instalace Caddy
```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# macOS
brew install caddy
```

### 2. Caddyfile
```
# /etc/caddy/Caddyfile

gestima.example.com {
    reverse_proxy localhost:8000

    # Logging
    log {
        output file /var/log/caddy/gestima.log
        format json
    }

    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}
```

### 3. Systemd service pro FastAPI
```ini
# /etc/systemd/system/gestima.service

[Unit]
Description=Gestima FastAPI Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/gestima
Environment="PATH=/opt/gestima/venv/bin"
ExecStart=/opt/gestima/venv/bin/uvicorn app.gestima_app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. Spuštění
```bash
# Nastartovat služby
sudo systemctl enable caddy
sudo systemctl start caddy
sudo systemctl enable gestima
sudo systemctl start gestima

# Ověřit
curl https://gestima.example.com/health
```

### 5. Produkční .env
```bash
DEBUG=false
SECRET_KEY=<vygenerovaný-klíč>
SECURE_COOKIE=true
```

## Architektura
```
Internet → Caddy (443/HTTPS) → FastAPI (127.0.0.1:8000)
                ↓
         Auto TLS cert
         (Let's Encrypt)
```

## Cookie bezpečnost
- `SECURE_COOKIE=true` v .env
- Cookie flag `secure=True` → prohlížeč posílá cookie POUZE přes HTTPS
- Kombinace s `httponly=True` + `samesite=strict` = plná ochrana

## Důsledky
- ✅ Automatické HTTPS bez manuální správy certifikátů
- ✅ Produkční deployment je jednoduchý
- ⚠️ Vyžaduje veřejnou doménu pro Let's Encrypt (nebo vlastní cert pro interní)
- ⚠️ Caddy musí být nainstalován na serveru

## Checklist pro deployment
- [ ] Nainstalovat Caddy
- [ ] Nakonfigurovat DNS (A záznam na server IP)
- [ ] Vytvořit Caddyfile s doménou
- [ ] Nastavit `SECURE_COOKIE=true` v .env
- [ ] Nastavit `DEBUG=false` v .env
- [ ] Vygenerovat silný `SECRET_KEY`
- [ ] Spustit Caddy + Gestima služby
- [ ] Ověřit HTTPS funguje
