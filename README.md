# GESTIMA 1.0

Kalkulátor nákladů CNC obrábění.

## Struktura projektu

```
GESTIMA_NEW/
├── app/
│   ├── gestima_app.py          # FastAPI aplikace
│   ├── config.py               # Konfigurace
│   ├── database.py             # SQLAlchemy async
│   ├── models/                 # Pydantic + SQLAlchemy
│   │   ├── enums.py
│   │   ├── part.py
│   │   ├── operation.py
│   │   ├── feature.py
│   │   ├── batch.py
│   │   └── machine.py
│   ├── routers/                # FastAPI routes (přejmenované)
│   │   ├── parts_router.py
│   │   ├── operations_router.py
│   │   ├── features_router.py
│   │   ├── batches_router.py
│   │   ├── data_router.py
│   │   └── pages_router.py
│   ├── services/               # Business logika (přejmenované)
│   │   ├── time_calculator.py
│   │   ├── cutting_conditions.py
│   │   ├── price_calculator.py
│   │   ├── reference_loader.py
│   │   └── feature_definitions.py
│   ├── templates/              # Jinja2 + HTMX
│   └── static/                 # CSS + JS (přejmenované)
│       ├── css/gestima.css
│       └── js/gestima.js
├── data/                       # Excel referenční data
├── tests/                      # Pytest
└── requirements.txt
```

## Spuštění

```bash
# 1. Vytvoř virtualenv
python -m venv venv
source venv/bin/activate

# 2. Nainstaluj závislosti
pip install -r requirements.txt

# 3. Spusť
uvicorn app.gestima_app:app --reload

# 4. Otevři
open http://localhost:8000
```

## Testy

```bash
# Všechny testy
pytest

# Jen kritické
pytest -m critical

# Jen business logika
pytest -m business
```

## Stack

- **Backend:** FastAPI + SQLAlchemy + Pydantic
- **Frontend:** Jinja2 + HTMX + Alpine.js
- **Database:** SQLite (async)
- **CSS:** TailwindCSS (CDN)
- **Tests:** pytest + pytest-asyncio

## Pojmenování souborů

Všechny soubory mají **unikátní názvy** napříč projektem:

- API routes: `*_router.py`
- Services: popisné názvy (`time_calculator.py`, `cutting_conditions.py`)
- Static: `gestima.css`, `gestima.js`
- Entry point: `gestima_app.py`

**Důvod:** Žádné konflikty názvů s původním projektem (Guesstimator).
