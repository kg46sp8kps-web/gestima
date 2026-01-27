# FILE GUIDE - Mapa souborů

Navigace k důležitým souborům v projektu.

---

## 📚 DOKUMENTACE (Čti v tomto pořadí)

### 🚀 PRO NOVÉ UŽIVATELE
1. **[README.md](README.md)** - Přehled projektu
2. **[QUICK_START.md](QUICK_START.md)** - Setup za 30 sekund
3. **[COMMANDS.md](COMMANDS.md)** - Všechny příkazy

### ⭐ PRO AI ASISTENTA
1. **[CLAUDE.md](CLAUDE.md)** ← POVINNÁ ČETBA
2. **[FUTURE_STEPS.md](FUTURE_STEPS.md)** - Co dělat (bugy)
3. **[docs/LESSONS.md](docs/LESSONS.md)** - Co NESMÍ

### 🏗️ PRO ARCHITEKTY
1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Jak to funguje
2. **[DB_ARCHITECTURE.md](DB_ARCHITECTURE.md)** - Struktura DB
3. **[docs/ROADMAP.md](docs/ROADMAP.md)** - 5-phase plán

### 📊 STATUS & METRIKY
- **[STATUS.md](STATUS.md)** - Co je hotovo, co ne
- **[docs/GESTIMA_1.0_SPEC.md](docs/GESTIMA_1.0_SPEC.md)** - Kompletní specifikace

### 🏛️ ARCHITEKTONICKÉ ROZHODNUTÍ (ADR)
```
docs/ADR/
├── 001-soft-delete-pattern.md    # Jak se mažou záznamy
├── 002-snapshot-pattern.md        # Snapshoty pro quotes
├── 003-integer-id-vs-uuid.md      # Proč integer ID
└── 004-implementation-notes.md    # Implementační poznámky
```

---

## 🎯 SKRIPTY SPUŠTĚNÍ

| Script | Účel | Jak spustit |
|--------|------|-----------|
| [gestima.py](gestima.py) | **CLI helper** (DOPORUČENO) | `python3 gestima.py run` |
| [run.sh](run.sh) | Shell script pro spuštění | `./run.sh` |
| [test.sh](test.sh) | Shell script pro testy | `./test.sh` |
| [setup.sh](setup.sh) | Shell script pro setup | `./setup.sh` |

### Příklady
```bash
python3 gestima.py run              # Spusť app
python3 gestima.py test             # Všechny testy
python3 gestima.py test-critical    # Jen critical
python3 gestima.py setup            # Setup venv
python3 gestima.py help             # Pomoc
```

---

## 🔧 BACKEND - Zdrojový kód

### Entry Point
```
app/gestima_app.py       # FastAPI aplikace (37 řádků)
app/config.py            # Konfigurace (27 řádků)
```

### Datové modely (SQLAlchemy ORM)
```
app/models/
├── enums.py             # PartStatus, StockType, OperationType, FeatureType
├── part.py              # Parts (díly)
├── operation.py         # Operations (operace obrábění)
├── feature.py           # Features (kroky obrábění)
├── batch.py             # Batches (dávky a ceny)
├── machine.py           # Machines (stroje)
├── material.py          # Materials (materiály)
└── cutting_condition.py # CuttingConditions (řezné podmínky)
```

### Business logika (Services)
```
app/services/
├── time_calculator.py        # 📐 Výpočet času obrábění
├── price_calculator.py       # 💰 Výpočet ceny (material + machining)
├── cutting_conditions.py     # ⚙️ Načítání Vc/f/Ap z Excel
├── feature_definitions.py    # 📋 Definice feature typů
└── reference_loader.py       # 📂 Načítání referenčních dat
```

### API Endpoints (Routers)
```
app/routers/
├── parts_router.py          # /api/parts/ - CRUD operace
├── operations_router.py      # /api/operations/ - Operace
├── features_router.py        # /api/features/ - Kroky
├── batches_router.py         # /api/batches/ - Dávky a ceny
├── data_router.py            # /api/data/ - Reference data
└── pages_router.py           # / - HTML pages
```

### Databáze
```
app/database.py           # SQLAlchemy setup + AuditMixin
app/db_helpers.py         # Helper functions
gestima.db                # SQLite database
gestima.db-shm            # WAL files
gestima.db-wal
```

---

## 🎨 FRONTEND

### Templates (Jinja2)
```
app/templates/
├── base.html                  # Base layout
├── index.html                 # Dashboard/home
└── parts/
    ├── list.html              # Parts list
    ├── list_fragment.html      # HTMX fragment
    ├── new.html               # Create form
    └── edit.html              # Edit form (split-layout)
```

### Static assets
```
app/static/
├── css/
│   └── gestima.css            # Main stylesheet
├── js/
│   └── gestima.js             # Alpine.js components
└── img/
    └── logo.png               # Logo
```

---

## 🧪 TESTY

### Test files
```
tests/
├── conftest.py                      # pytest config
├── test_audit_infrastructure.py     # 6373 řádků! (soft delete tests)
├── test_pricing.py                  # Price calculations
├── test_conditions.py               # Cutting conditions
├── test_calculator.py               # Time calculator
├── test_models.py                   # Model validation
└── test_imports.py                  # Import verification
```

### Spuštění testů
```bash
pytest -v                           # Všechny
pytest -v -m critical              # Jen critical (14 testů)
pytest -v -m business              # Business logika
pytest -v -k "test_pricing"        # Filtrovat
pytest -v --pdb                    # Debug mode
```

---

## 📦 KONFIGURAČNÍ SOUBORY

| Soubor | Obsah |
|--------|-------|
| [requirements.txt](requirements.txt) | Python dependencies |
| [pytest.ini](pytest.ini) | pytest configuration |
| [.cursorrules](.cursorrules) | AI assistant guidelines |
| [.gitignore](.gitignore) | Git ignore |
| [.cursorignore](.cursorignore) | Cursor ignore |

---

## 📂 REFERENČNÍ DATA (Excel)

```
data/archive/
├── materials.xlsx               # Material properties (loaded at startup)
└── cutting_conditions.xlsx      # Cutting parameters
```

Načítáno automaticky při startu (via `reference_loader.py`).

---

## 🗺️ NAVIGACE - Kde hledat co

### "Jak spustit aplikaci?"
1. [QUICK_START.md](QUICK_START.md) - 30 sekund
2. [COMMANDS.md](COMMANDS.md) - Všechny příkazy

### "Kde je chyba v kódu?"
1. [FUTURE_STEPS.md](FUTURE_STEPS.md) - Seznam bugů
2. [STATUS.md](STATUS.md) - Co je hotovo
3. `app/services/` - Business logika

### "Jaká jsou pravidla pro AI?"
1. [CLAUDE.md](CLAUDE.md) ← Přečíst PRVNÍ
2. [docs/LESSONS.md](docs/LESSONS.md) - Anti-patterns

### "Jak databáze funguje?"
1. [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) - Schema
2. `app/models/` - SQLAlchemy modely
3. `app/database.py` - Setup

### "Jaké API endpoints existují?"
1. `http://localhost:8000/docs` - Swagger UI (když je app spuštěná)
2. `app/routers/` - Zdrojový kód endpoints
3. [docs/GESTIMA_1.0_SPEC.md](docs/GESTIMA_1.0_SPEC.md) - Dokumentace

### "Jak frontend funguje?"
1. [ARCHITECTURE.md](ARCHITECTURE.md) - UI patterns
2. `app/templates/` - Jinja2 templates
3. `app/static/` - CSS + JavaScript

### "Jak to bylo rozhodováno?"
1. `docs/ADR/` - Architecture Decision Records
2. [docs/ROADMAP.md](docs/ROADMAP.md) - Dlouhodobý plán

---

## 🔄 TYPICAL WORKFLOW

### 1. Nový vývojář - Setup
```
1. Čti: README.md
2. Čti: QUICK_START.md
3. Spusť: python3 gestima.py setup
4. Spusť: python3 gestima.py run
5. Otevři: http://localhost:8000
```

### 2. Implementace bugfixu
```
1. Čti: CLAUDE.md (pravidla)
2. Čti: FUTURE_STEPS.md (jaký bug?)
3. Čti: docs/LESSONS.md (neudělej chyby)
4. Čti: zdrojový kód (app/models/ či app/services/)
5. Implementuj
6. Testuj: python3 gestima.py test-critical
7. Commit: git commit -m "..."
```

### 3. Code Review
```
1. Zkontroluj: Type hints (PEP 484)
2. Zkontroluj: Tests (pytest)
3. Zkontroluj: LESSONS.md compliance
4. Zkontroluj: Jeden zdroj pravdy
5. Zkontroluj: API First (ne JS výpočty)
6. Merge
```

---

## 📊 SOUBOROVÁ STRUKTURA

```
GESTIMA/
├── 📄 Dokumentace (ROOT)
│   ├── README.md                    # Main entry point
│   ├── QUICK_START.md               # 30s setup
│   ├── COMMANDS.md                  # CLI commands
│   ├── STATUS.md                    # What's done
│   ├── FILE_GUIDE.md                # This file
│   ├── ARCHITECTURE.md              # System design
│   ├── DB_ARCHITECTURE.md           # Database schema
│   ├── FUTURE_STEPS.md              # Bugs & tasks
│   └── CLAUDE.md                    # AI rules ⭐
│
├── 🚀 Skripty
│   ├── gestima.py                   # CLI helper
│   ├── run.sh                       # Shell script
│   ├── test.sh
│   └── setup.sh
│
├── 📦 app/ (APLIKACE)
│   ├── gestima_app.py
│   ├── config.py
│   ├── database.py
│   ├── db_helpers.py
│   │
│   ├── models/           (8 ORM modelů)
│   ├── services/         (5 business logiky modulů)
│   ├── routers/          (6 API routerů)
│   │
│   ├── templates/        (Jinja2 + HTMX)
│   └── static/           (CSS + JS)
│
├── 🧪 tests/
│   ├── conftest.py
│   ├── test_pricing.py
│   ├── test_calculator.py
│   └── ... (5+ dalších)
│
├── 📚 docs/
│   ├── LESSONS.md        (Anti-patterns)
│   ├── ROADMAP.md        (5-phase plan)
│   ├── GESTIMA_1.0_SPEC.md (Full spec)
│   └── ADR/              (Architecture decisions)
│
├── 📂 data/
│   └── archive/          (Excel reference files)
│
├── 🗄️ Database
│   ├── gestima.db
│   ├── gestima.db-shm
│   └── gestima.db-wal
│
└── ⚙️ Config
    ├── requirements.txt
    ├── pytest.ini
    ├── .cursorrules
    └── .gitignore
```

---

## 🔗 Quick Links

| Co | Kde | Příkaz |
|----|-----|--------|
| App home | [README.md](README.md) | `cat README.md` |
| Quick setup | [QUICK_START.md](QUICK_START.md) | `./run.sh` |
| Commands | [COMMANDS.md](COMMANDS.md) | `python3 gestima.py help` |
| AI rules | [CLAUDE.md](CLAUDE.md) | Čti před implementací |
| Bugs | [FUTURE_STEPS.md](FUTURE_STEPS.md) | `cat FUTURE_STEPS.md` |
| Status | [STATUS.md](STATUS.md) | `cat STATUS.md` |
| API Docs | http://localhost:8000/docs | Když je app spuštěná |

---

**Vytvořeno:** 2026-01-23
**Účel:** Navigace projektem
**Verze:** 1.0
