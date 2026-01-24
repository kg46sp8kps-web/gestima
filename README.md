# GESTIMA 1.0 - CNC Cost Calculator

Webová aplikace pro výpočet nákladů a časů obrábění na CNC strojích.

## 🚀 Quick Start

```bash
# 1. Setup (1x)
python3 gestima.py setup

# 2. Run
python3 gestima.py run

# 3. Open
open http://localhost:8000
```

**Or:**
```bash
./run.sh
```

## 📋 Co je kde

| Co hledáš? | Kde to je? |
|-----------|-----------|
| **Jak spustit app** | [QUICK_START.md](QUICK_START.md) |
| **Jak stavba funguje** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Struktura DB** | [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) |
| **Bugy k opravě** | [FUTURE_STEPS.md](FUTURE_STEPS.md) |
| **Pravidla pro AI** | [CLAUDE.md](CLAUDE.md) ⭐ |
| **Historie změn** | [CHANGELOG.md](CHANGELOG.md) 📋 |
| **Všechny příkazy** | [COMMANDS.md](COMMANDS.md) |
| **Chyby které se nesmí opakovat** | [docs/LESSONS.md](docs/LESSONS.md) |
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
├── tests/                      # pytest (8+ souborů)
├── data/archive/               # Reference data (Excel)
├── docs/
│   ├── LESSONS.md              # Anti-patterns
│   ├── ROADMAP.md              # 5-phase plan
│   ├── GESTIMA_1.0_SPEC.md    # Full spec
│   └── ADR/                    # Architecture decisions
├── ARCHITECTURE.md             # 📘 Architektura
├── DB_ARCHITECTURE.md          # 📗 Databáze
├── FUTURE_STEPS.md             # 📙 Bugy & úkoly
├── CLAUDE.md                   # ⭐ Pravidla pro AI
├── COMMANDS.md                 # 📔 Všechny příkazy
├── QUICK_START.md              # 🚀 Brzy start
├── gestima.py                  # CLI helper
├── run.sh, test.sh, setup.sh   # Shell scripts
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
1. [CLAUDE.md](CLAUDE.md) - Pravidla
2. [FUTURE_STEPS.md](FUTURE_STEPS.md) - Co dělat
3. [docs/LESSONS.md](docs/LESSONS.md) - Neudělej chyby

**Architektura:**
1. [ARCHITECTURE.md](ARCHITECTURE.md) - Jak to funguje
2. [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) - Struktura DB

## 🔴 Aktuální bugy (TODO)

**P1 - Kritické (Týden 1):**
- BUG-002: Zobrazení strojního času
- BUG-003: Přepočet MODE (LOW/MID/HIGH)
- BUG-001: Cenový ribbon

**P2 - Důležité (Týden 2):**
- BUG-006, 007, 004, 005

👉 Více: [FUTURE_STEPS.md](FUTURE_STEPS.md)

## ⚙️ Konfigurace

Vytvoř `.env` (nepovinné):
```
DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///gestima.db
PORT=8000
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
| Backend (models) | ✅ Ready |
| Business logika | ✅ Ready |
| API (routers) | ✅ Ready |
| Frontend (UI) | 🟡 In progress |
| Tests | ✅ 14/14 critical |
| Dokumentace | ✅ Complete |

## 🚀 Next Steps

1. Opravit BUG-002 (časy operací)
2. Opravit BUG-003 (MODE přepočet)
3. Opravit BUG-001 (cenový ribbon)
4. Nasadit na produkci

👉 Detail: [FUTURE_STEPS.md](FUTURE_STEPS.md)
