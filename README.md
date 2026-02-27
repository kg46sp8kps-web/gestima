# GESTIMA - CNC Cost Calculator

**Verze:** 1.5.0
**Datum:** 2026-01-27
**Status:** Production Ready

Webová aplikace pro výpočet nákladů a časů obrábění na CNC strojích.

## 🚀 Quick Start

### Dev Environment (laptop/desktop)

```bash
# 1. Clone repository
git clone git@github.com:your-org/gestima.git
cd gestima

# 2. Setup venv + dependencies
python3 gestima.py setup

# 3. Seed demo data (reset DB + demo parts + demo admin)
python3 gestima.py seed-demo

# 4. Run
python3 gestima.py run

# 5. Open browser
open http://localhost:8000

# Login: demo / demo123
```

### Production Deployment (Windows firma-PC)

**⚡ Quick Setup (30 min):** [PRODUCTION-SETUP.md](PRODUCTION-SETUP.md) 📘

```bash
# 1. Install Python + Git
# 2. Clone repo
git clone git@github.com:your-org/gestima.git
cd C:\Gestima

# 3. Setup
python gestima.py setup

# 4. Firewall
cd scripts\windows
.\setup_firewall.ps1

# 5. Seed + Create users
python -m app.seed_materials
python scripts\seed_machines.py
python gestima.py create-admin  # Default: admin / asdfghjkl

# 6. Autostart + Backup (Task Scheduler)
# See: PRODUCTION-SETUP.md steps 13-14
```

**Guides:**
- **[PRODUCTION-SETUP.md](PRODUCTION-SETUP.md)** - Windows production checklist (30 min) ⚡
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete guide (Git from zero, dev/prod workflows, troubleshooting) 📚

## 📋 Dokumentace

| Co hledáš? | Kde to je? |
|-----------|-----------|
| **Deployment Guide (Dev/Prod setup)** | [DEPLOYMENT.md](DEPLOYMENT.md) 🚀 |
| **Quick Start (5 min)** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **AI pravidla + workflow** | [AGENTS.md](AGENTS.md) ⭐ |
| **Kompletní specifikace** | [docs/GESTIMA_1.0_SPEC.md](docs/GESTIMA_1.0_SPEC.md) |
| **Historie změn** | [CHANGELOG.md](CHANGELOG.md) 📋 |
| **Architektonická rozhodnutí** | [docs/ADR/](docs/ADR/) |
| **Další kroky** | [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) |
| **Testovací strategie** | [docs/TESTING.md](docs/TESTING.md) |
| **Verzování** | [docs/VERSIONING.md](docs/VERSIONING.md) |
| **API dokumentace** | http://localhost:8000/docs |

## 🎯 Pracovní postup

### Vývoj
```bash
# Terminal 1
python3 gestima.py run

# Terminal 2
python3 gestima.py test-critical

# Browser
open http://localhost:8000
```

### Before Commit
```bash
python3 gestima.py test-critical
python3 gestima.py run  # Manual test
git add . && git commit -m "..."
```

## 📁 Struktura projektu

```
GESTIMA/
├── app/
│   ├── gestima_app.py          # FastAPI entry point
│   ├── config.py               # Konfigurace
│   ├── database.py             # SQLAlchemy async + AuditMixin
│   ├── models/                 # SQLAlchemy ORM (8 modelů)
│   ├── services/               # Business logika (5 modulů)
│   │   ├── time_calculator.py   # Výpočet času
│   │   ├── price_calculator.py  # Výpočet ceny
│   │   ├── cutting_conditions.py # Řezné podmínky
│   │   ├── feature_definitions.py # Typy operací
│   │   └── reference_loader.py  # Načítání Excelu
│   ├── routers/                # FastAPI API (6 routerů)
│   ├── templates/              # Jinja2 + HTMX
│   └── static/
│       ├── css/gestima.css
│       └── js/gestima.js
├── tests/                      # pytest (98 testů)
├── docs/
│   ├── ARCHITECTURE.md         # Quick start (5 min)
│   ├── GESTIMA_1.0_SPEC.md    # Kompletní specifikace
│   ├── TESTING.md              # Testovací strategie
│   ├── NEXT-STEPS.md           # Plánované úkoly
│   ├── VERSIONING.md           # Verzovací politika
│   ├── audit.md                # Auditní zpráva (original)
│   ├── audit-p2b.md            # Post-implementation audit
│   ├── ADR/                    # Architecture Decision Records
│   └── archive/                # Zastaralé dokumenty
├── AGENTS.md                   # ⭐ Aktivní AI pravidla (Codex)
├── ai/                         # AI role profily + workflow
│   ├── agents/                 # Orchestrator, backend, frontend, qa, auditor
│   └── workflow.md             # Standardní pracovní postup
├── CHANGELOG.md                # 📋 Historie změn
├── README.md                   # 📘 Tento soubor
├── gestima.py                  # CLI helper
├── requirements.txt
└── venv/                       # Virtual environment
```

## 🛠 CLI Helper

```bash
python3 gestima.py run              # Spusť aplikaci
python3 gestima.py test             # Všechny testy
python3 gestima.py test-critical    # Jen kritické
python3 gestima.py setup            # Setup venv
python3 gestima.py shell            # Python REPL
python3 gestima.py help             # Pomoc
```

## 📊 Technologie

- **Backend:** FastAPI 0.109+
- **ORM:** SQLAlchemy 2.0+ (async)
- **Validace:** Pydantic v2
- **DB:** SQLite + WAL mode
- **Frontend:** Jinja2 + HTMX 1.9 + Alpine.js 3.13
- **Styling:** TailwindCSS (CDN)
- **Tests:** pytest + pytest-asyncio

## 🧪 Testování

```bash
python3 gestima.py test-critical      # Jen kritické
python3 gestima.py test -k "pricing"  # Filtrovat
python3 gestima.py test --pdb         # Debug mode
```

**Status:** 14/14 critical tests ✅

## 🔗 Dokumentace

**Povinná četba PŘED implementací:**
1. [AGENTS.md](AGENTS.md) - Aktivní AI pravidla + komunikační kontrakt
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Quick start (5 min)
3. [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) - Plánované úkoly (P2 Fáze C)

**Audit & Quality:**
1. [docs/audit.md](docs/audit.md) - Původní auditní zpráva
2. [docs/audit-p2b.md](docs/audit-p2b.md) - Post-implementation audit P2B
3. [docs/VERSIONING.md](docs/VERSIONING.md) - Verzovací politika

## 📌 Aktuální stav (v1.1.0)

**Hotovo:**
- ✅ P0 (Blocker): Auth, HTTPS, Debug mode
- ✅ P1 (Kritické): Logging, Backups, CORS, Rate limiting
- ✅ P2 Fáze A: Material Hierarchy
- ✅ P2 Fáze B: Minimal Snapshot (Batch freeze)
- ✅ Testy: 98/98 passed

**Plánováno (P2 Fáze C):**
- A1: Geometry Hash (frozen ghost fix) - HIGH
- A2: Health Check Endpoint - HIGH
- A3: Zero-Price Validace - MEDIUM
- A4: UI Frozen Indikace - MEDIUM

👉 Detail: [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) a [docs/audit-p2b.md](docs/audit-p2b.md)

## ⚙️ Konfigurace

Vytvoř `.env` (nepovinné):
```
DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///gestima.db
PORT=8000
DRAWINGS_SHARE_PATH=/Volumes/Dokumenty/TPV-dokumentace/Vykresy
```

Import výkresů ze serveru podporuje i SSH režim bez mountování síťové jednotky:
```
DRAWINGS_SHARE_PATH=ssh://user@host:22/absolute/path
```
Příklad:
```
DRAWINGS_SHARE_PATH=ssh://gestima@192.168.1.135:22/home/gestima/uploads/vykresy
```

## 🎓 Principy

✅ **API First** - Veškerá logika v Pythonu
✅ **Single Source of Truth** - Jedno místo pro výpočty
✅ **No Hardcoded Values** - Vše z DB/API
✅ **DRY** - Žádná duplikace
✅ **Type Hints** - Všude
✅ **Tests First** - Testy pro business logiku
✅ **Soft Delete** - Záznamy se nikdy nemažou
✅ **Audit Trail** - Kdo, kdy, co změnil

Viz: [LESSONS.md](docs/LESSONS.md)

## 📞 Status

| Složka | Status |
|--------|--------|
| Backend (models) | ✅ Production Ready |
| Business logika | ✅ Production Ready |
| API (routers) | ✅ Production Ready |
| Authentication | ✅ Production Ready |
| Tests | ✅ 98/98 passed |
| Dokumentace | ✅ Complete |

## 🚀 Next Steps (P2 Fáze C)

1. **A1: Geometry Hash** (HIGH) - Detekce změn geometrie po freeze
2. **A2: Health Check** (HIGH) - Monitoring endpoint pro produkci
3. **A3: Zero-Price Validace** (MEDIUM) - Pre-freeze business validace
4. **A4: UI Frozen Indikace** (MEDIUM) - Vizuální feedback pro frozen batches

👉 Detail: [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) a [docs/audit-p2b.md](docs/audit-p2b.md)
