# GESTIMA - Deployment Guide

**Verze:** 2.0 (2026-02-17)

---

## Dev Environment

```bash
git clone git@github.com:your-org/gestima.git && cd gestima
python gestima.py setup          # venv + dependencies
python gestima.py seed-demo      # DB schema + demo data + admin user
python gestima.py dev            # Backend + Vite dev (:5173)
```

Login: `demo` / `demo123`

---

## Production Setup (Windows PC)

### Prerequisites
- Python 3.9+, Git, statick IP (e.g. 192.168.1.50), firewall rule pro port 8000

### Setup
```powershell
cd C:\
git clone git@github.com:your-org/gestima.git && cd gestima
python gestima.py setup

# .env soubor
notepad .env
# DEBUG=false
# SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
# SECURE_COOKIE=false
# DATABASE_URL=sqlite+aiosqlite:///gestima.db

# Seed + admin
python gestima.py seed-demo
python gestima.py create-admin

# Build frontend + run
cd frontend && npm run build && cd ..
python gestima.py run
```

### Firewall
```powershell
New-NetFirewallRule -DisplayName "GESTIMA" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Autostart (Task Scheduler)
1. Create Basic Task: Name `GESTIMA`, Trigger `At startup`
2. Action: `Start a program` → `C:\Gestima\start_gestima.bat`, Start in `C:\Gestima`
3. Properties: Run whether logged on or not, highest privileges, NOT only on AC power

### Daily Backup (Task Scheduler)
- Name: `GESTIMA Backup`, Trigger: Daily 2:00 AM
- Action: `C:\Gestima\backup_gestima.bat`

---

## Server Control

| Akce | Prikaz |
|------|--------|
| Bezi? | `lsof -ti:8000` nebo `curl http://localhost:8000/health` |
| Start | `python gestima.py run > /tmp/gestima.log 2>&1 &` |
| Stop | `pkill -f "gestima.py run" && pkill -f "uvicorn"` |
| Restart | Stop + `sleep 2` + Start |
| Logy | `tail -f /tmp/gestima.log` |
| Deploy update | `git pull origin main && npm run build --prefix frontend && pkill -f uvicorn && sleep 2 && python gestima.py run` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused` | Server nebezi → start |
| `Address already in use` | `kill -9 $(lsof -ti:8000)` pak start |
| `Database is locked` | `pkill -f gestima && rm -f gestima.db-shm gestima.db-wal` pak start |
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Users se nepripoji | Check firewall rule + IP: `ipconfig` / `ifconfig` |
| App pada po restartu PC | Task Scheduler: "Run whether user is logged on or not" = YES |
| Backup selhal | Check disk space (`Get-PSDrive C`), external drive connected? |

---

## Backup & Restore

```bash
python gestima.py backup                    # Create backup
python gestima.py restore <backup_file>     # Restore from backup
```

Retention: local 30 dni, external drive 1 rok. 3-2-1 rule (3 copies, 2 media, 1 offsite).

---

## Reference

- [ADR-018](../ADR/018-deployment-strategy.md) — Deployment strategy
- [ADR-007](../ADR/007-https-caddy.md) — HTTPS via Caddy
- `scripts/windows/` — Windows batch scripts (start, backup, firewall)
