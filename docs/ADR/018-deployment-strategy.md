# ADR-018: Dev/Prod Deployment Strategy

## Status
**Accepted** (2026-01-27)

## Kontext

GESTIMA běží v malém nasazení (3-5 uživatelů, firemní síť), ale vývojář pracuje vzdáleně (z domova) bez VPN přístupu. Potřebujeme deployment strategii která:

1. **Umožňuje vývoj bez přístupu k produkci** - developer pracuje lokálně
2. **Chrání produkční data** - experimenty nesmí ovlivnit ostrý provoz
3. **Respektuje SQLite limity** - single-writer, žádné network shares
4. **Funguje pro malý tým** - KISS principle, žádný overkill

**Scénář:**
- **Produkce:** Windows PC v firemní síti (192.168.1.x), 3 users, ostrá data
- **Vývoj:** Developer laptop doma, žádný přímý přístup k produkci
- **Deployment:** Git repo (GitHub/GitLab), manuální deploy při fyzickém přístupu
- **Testování:** Občasné testování na reálných datech přes backup/restore

## Rozhodnutí

**Strategie: Dev/Prod Database Separation s Git-based deployment**

### Architektura:

```
┌──────────────────────────────────────────────────────────────┐
│                         DEV ENVIRONMENT                       │
│  Developer Laptop (localhost:8000)                           │
│  ├── gestima.db (demo data, throwaway)                       │
│  ├── Git working tree (feature branches)                     │
│  └── Local testing (pytest, manual QA)                       │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ git push origin feature/xyz
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                         GIT REMOTE                            │
│  GitHub/GitLab Private Repo                                  │
│  ├── main branch (stable releases)                           │
│  └── feature branches (in-development)                       │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ git pull origin main
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                        PROD ENVIRONMENT                       │
│  Firma-PC (192.168.1.50:8000)                                │
│  ├── gestima.db (production data, BACKUP DAILY!)             │
│  ├── Git working tree (main branch, stable)                  │
│  ├── Auto-start via Task Scheduler                           │
│  └── Backups → backups/ folder + external drive              │
└──────────────────────────────────────────────────────────────┘
```

### Klíčové principy:

1. **Separate Databases** - ŽÁDNÉ sdílení `.db` souboru mezi instancemi
2. **Git as deployment tool** - Code sync přes Git, data sync přes backup/restore
3. **Backup-driven testing** - Test na real data = restore backup do dev
4. **Manual deployment** - Deploy jen při fyzickém přístupu (nebo Remote Desktop)

## Důvody

### Proč separate DB?

| Problém | Řešení separate DB |
|---------|-------------------|
| **SQLite single-writer** | Dev i Prod můžou psát současně (jiné soubory) |
| **Network share korupce** | SQLite WAL mode vyžaduje local filesystem |
| **Bezpečnost dat** | Dev experimenty neovlivní produkci |
| **Rychlost** | Žádná network latency v dev módu |
| **Rollback** | Prod backup restore za 30s |

### Proč Git deployment?

| Důvod | Benefit |
|-------|---------|
| **Version control** | Historie všech změn, rollback na starší verzi |
| **Code review** | Feature branches → review → merge |
| **Offline development** | Vyvíjej bez síťového připojení |
| **Standard workflow** | Industry best practice |

### Proč backup/restore pro testování?

| Důvod | Benefit |
|-------|---------|
| **Real data testing** | Otestuj na aktuálních ostřích datech |
| **Throwaway environment** | Rozbij dev DB, restore znovu |
| **Privacy** | Backup může být anonymizován (future) |

## Alternativy (zamítnuté)

### 1. PostgreSQL + Remote Access
**Trade-offs:**
- ✅ Concurrent writes, remote přístup přes SSH tunnel
- ❌ Effort: 1 týden migrace + PostgreSQL server setup
- ❌ Overhead: Správa DB serveru pro 3 users = overkill
- ❌ Dependency: PostgreSQL musí běžet 24/7

**Verdict:** YAGNI (You Aren't Gonna Need It) - SQLite stačí pro <10 users

### 2. SQLite na Network Share
**Trade-offs:**
- ✅ Jedno "centrální" místo
- ❌ WAL mode NEFUNGUJE na network share
- ❌ DB korupce zaručena (documented SQLite limitation)
- ❌ Locking issues

**Verdict:** **NIKDY NEPOUŽÍVAT** - dokumentovaný anti-pattern

### 3. DB Sync (Dropbox/rsync/robocopy)
**Trade-offs:**
- ✅ Automatická synchronizace
- ❌ Konfliktní zápisy (dev i prod píšou současně)
- ❌ Race conditions → data loss
- ❌ Sync delay → stale data

**Verdict:** Nebezpečné - konflikty jsou nevyhnutelné

### 4. VPN + Shared DB (jediná instance)
**Trade-offs:**
- ✅ Single source of truth
- ❌ SQLite single-writer = dev blokuje prod users
- ❌ Network latency v dev módu
- ❌ Vyžaduje VPN (ne vždy dostupné)

**Verdict:** SQLite není navržen pro remote access

## Implementace

### 1. Dev Environment Setup

```bash
# 1× setup na developer laptop
git clone https://github.com/your-org/gestima.git
cd gestima
python gestima.py setup

# Seed demo data
python -m app.seed_materials
python scripts/seed_machines.py
python scripts/seed_complete_part.py

# Create demo admin user
python gestima.py create-admin
# Username: demo
# Password: demo123
```

**Dev DB lokace:** `gestima.db` (local, throwaway)

### 2. Prod Environment Setup

```bash
# Na firma-PC (1× setup)
git clone https://github.com/your-org/gestima.git
cd C:\Gestima
python gestima.py setup

# Seed reference data (materials, machines)
python -m app.seed_materials
python scripts/seed_machines.py

# Create real admin users
python gestima.py create-admin  # 3× pro 3 users

# Setup autostart (Task Scheduler)
# Setup firewall rule
# Setup daily backup
```

**Prod DB lokace:** `C:\Gestima\gestima.db` (production, BACKUP!)

### 3. Development Workflow

```bash
# Denní vývoj (doma)
cd ~/gestima
git checkout -b feature/new-report
# ...vývoj...
pytest  # Testy
python gestima.py run  # Manuální test
git commit -m "feat: add new report"
git push origin feature/new-report

# Code review (GitHub Pull Request)
# Merge → main branch
```

### 4. Deployment Workflow

```bash
# V práci (fyzický přístup k firma-PC)
cd C:\Gestima
git pull origin main

# Restart aplikace (Task Scheduler)
schtasks /run /tn "GESTIMA"

# Nebo restart ručně
# Ctrl+C v konzoli + python gestima.py run
```

### 5. Testing s Production Data

```bash
# Občasné testování na real data (doma)

# 1. Zkopíruj backup z produkce (USB/network share)
cp /mnt/usb/backups/gestima_backup_20260127.db.gz .

# 2. Restore do dev
python gestima.py restore gestima_backup_20260127.db.gz

# 3. Test s reálnými daty
python gestima.py run

# 4. Po otestování - reset na demo data
python gestima.py seed-demo
```

### 6. Backup Strategy (Produkce)

```bash
# Automatický denní backup (Task Scheduler 2:00 AM)
python gestima.py backup

# Backupy se ukládají do:
C:\Gestima\backups\gestima_backup_YYYYMMDD_HHMMSS.db.gz

# Kopie na external drive (robocopy po backupu)
robocopy C:\Gestima\backups Z:\IT\GESTIMA_Backups /MIR
```

**Retention policy:**
- Local: 30 dnů (auto-cleanup starších backupů)
- External drive: 1 rok

### 7. Rollback Procedure

```bash
# Pokud deploy pokazí produkci

# 1. Restore poslední funkční backup
cd C:\Gestima
python gestima.py restore backups\gestima_backup_20260126_020000.db.gz

# 2. Rollback code (git)
git checkout <previous-commit-hash>

# 3. Restart
schtasks /run /tn "GESTIMA"
```

## Důsledky

### Pozitivní ✅

1. **Bezpečnost dat** - Dev experimenty neovlivní produkci
2. **SQLite compatible** - Respektuje single-writer limitation
3. **Offline development** - Vyvíjej bez síťového přístupu
4. **Fast dev cycle** - Zero network latency
5. **Standard workflow** - Git = industry best practice
6. **Easy rollback** - Backup restore za 30s
7. **KISS principle** - Žádný overhead (PostgreSQL, VPN, atd.)

### Negativní ❌

1. **Manuální deploy** - Git pull + restart vyžaduje fyzický/RDP přístup
2. **Deploy latency** - Deploy jen když jsi v práci (ne real-time)
3. **Testing na real data** - Restore backup (extra krok)
4. **Backup transport** - USB/network share pro kopii backupů

### Migrace v budoucnu

**Kdy přejít na PostgreSQL?**
- >10 concurrent users
- Real-time MES tracking vyžaduje vysokou concurrent write throughput
- Potřeba full-text search (PostgreSQL má lepší FTS)

**Kdy přidat CI/CD?**
- Automatický deploy přes SSH (pokud získáš VPN)
- Automated testing pipeline (GitHub Actions)

**Timeline:** PostgreSQL evaluation plánováno pro Q3 2026 (v4.0)

## Checklist pro nového developera

- [ ] Git nainstalován + SSH klíč nastavený
- [ ] GitHub/GitLab účet s přístupem k repo
- [ ] Python 3.9+ nainstalován
- [ ] Dev environment: `python gestima.py setup`
- [ ] Demo data: `python gestima.py seed-demo`
- [ ] První commit: `git commit -m "docs: update README"`
- [ ] Přečíst: [DEPLOYMENT.md](../DEPLOYMENT.md)

## Checklist pro produkční deployment

- [ ] Firma-PC má statickou IP (192.168.1.x)
- [ ] Windows Firewall pravidlo (port 8000)
- [ ] Git nainstalován + SSH klíč pro GitHub
- [ ] Prod environment: `python gestima.py setup`
- [ ] Reference data seeded (materials, machines)
- [ ] Admin users vytvořeni (3×)
- [ ] Task Scheduler autostart nakonfigurován
- [ ] Daily backup Task Scheduler job
- [ ] External drive pro backup kopie
- [ ] `.env` nastavený (`SECURE_COOKIE=false` pro HTTP)
- [ ] Health check: `curl http://192.168.1.50:8000/health`

## Reference

- [DEPLOYMENT.md](../DEPLOYMENT.md) - Kompletní deployment guide
- PostgreSQL migration plánována v4.0 (VISION.md — removed, available in git history)
- [ADR-007](007-https-caddy.md) - HTTPS pro public deployment
- SQLite Network Share Warning: https://sqlite.org/whentouse.html

---

**Version:** 1.0
**Date:** 2026-01-27
**Status:** ACCEPTED
