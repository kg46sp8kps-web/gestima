# GESTIMA — Deployment na Linux server

**Server:** Ubuntu 22.04, `192.168.1.135`, uživatel `gestima`
**Doména:** `https://gestima.cz` (Let's Encrypt přes Cloudflare DNS)
**DB:** `/home/gestima/gestima-test.db` (56 MB, 18 000+ dílů)
**Systemd service:** `gestima.service` (WorkingDirectory `/home/gestima`)

---

## Nasazení nového buildu (rutinní update)

### 1. Build frontendu na Macu
```bash
cd /Users/lofas/Documents/__App_Claude/Gestima
npm run build -C frontend
```

### 2. Přenos na server
Spusť jako **jeden řádek** z adresáře projektu:
```bash
cd /Users/lofas/Documents/__App_Claude/Gestima && tar czf - --exclude=node_modules --exclude=venv --exclude=venv-test --exclude=.git --exclude=__pycache__ --exclude='*.pyc' --exclude='*.bak' --exclude=logs . | ssh gestima@192.168.1.135 "cd /home/gestima && tar xzf -"
```

### 3. Restart na serveru
```bash
sudo systemctl restart gestima
sudo systemctl status gestima
```

Hotovo. Ověř na `https://gestima.cz`.

---

## Přenos produkční DB z Macu na server

```bash
# Na Macu (nový terminál, ne SSH)
scp /Users/lofas/Documents/__App_Claude/Gestima/gestima-test.db gestima@192.168.1.135:/home/gestima/gestima-test.db

# Na serveru
sudo systemctl restart gestima
```

---

## Přihlašovací údaje

| Uživatel | Heslo | Role |
|----------|-------|------|
| `demo` | `admin123` | ADMIN |
| `Ladislav` | — | ADMIN |

---

## Struktura na serveru

```
/home/gestima/
├── app/                  # Backend (FastAPI)
├── frontend/dist/        # Built frontend (Vue)
├── alembic/              # DB migrace
├── gestima.py            # CLI runner
├── gestima-test.db       # Produkční DB ← pozor na název
├── .env                  # Konfigurace (SECURE_COOKIE=true, DATABASE_URL)
├── venv/                 # Python virtualenv
└── backups/              # Automatické zálohy
    ├── hourly/
    └── daily/
```

**Pozor:** DB se jmenuje `gestima-test.db` (historický název). `.env` obsahuje:
```
DATABASE_URL=sqlite+aiosqlite:///gestima-test.db
SECURE_COOKIE=true
```

---

## Caddy (HTTPS)

**Caddyfile:** `/etc/caddy/Caddyfile`
```
gestima.cz {
    tls {
        dns cloudflare <API_TOKEN>
    }
    reverse_proxy localhost:8000
}
```

**Certifikát:** Let's Encrypt, automatické obnovení přes Cloudflare DNS-01 challenge.
**Cloudflare:** DNS spravuje gestima.cz → A record `192.168.1.135`

Caddy restart (jen při změně Caddyfile):
```bash
sudo systemctl restart caddy
```

---

## Logy

```bash
journalctl -u gestima -f        # Gestima logy
journalctl -u caddy -f          # Caddy / certifikát logy
```

---

## Troubleshooting

| Problém | Řešení |
|---------|--------|
| Stará verze v prohlížeči | Server je správně — vymaz cache prohlížeče |
| Login nefunguje | Přistupuj přes `https://` ne `http://` (SECURE_COOKIE=true) |
| Certifikát expiroval | `sudo systemctl restart caddy` |
| DB locked | `sudo systemctl restart gestima` |
| Port 8000 nedostupný | `sudo systemctl start gestima` |
