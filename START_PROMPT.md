# GESTIMA 1.0 - START PROMPT

**Zkopíruj tento prompt do nové Cursor session.**

---

## PROMPT

```
Pokračuji ve vývoji GESTIMA 1.0 - kalkulátoru CNC obrábění.

## AKTUÁLNÍ STAV
Základní struktura je připravena:
- FastAPI backend (gestima_app.py)
- SQLAlchemy modely (Part, Operation, Feature, Batch)
- Pydantic schemas
- API routers (*_router.py)
- Services: time_calculator, cutting_conditions, price_calculator
- Jinja2 + HTMX + Alpine.js
- Automatické testy (pytest)

## CO DOKONČIT

### 1. SPUŠTĚNÍ
```bash
cd GESTIMA_NEW
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.gestima_app:app --reload
```

### 2. TESTY
```bash
pytest -m critical
```

### 3. TODO
- [ ] Kompletní UI pro editaci dílu
- [ ] HTML komponenty pro operace/kroky
- [ ] Cenový ribbon
- [ ] Change mode (LOW/MID/HIGH)
- [ ] Upload výkresu

## PRAVIDLA
- HTMX pro AJAX, Alpine.js pro lokální stav
- Server-side rendering
- Žádný npm/React
- Type hints všude
- Max 200 řádků/soubor

Začni kontrolou že app běží.
```

---

## STRUKTURA

```
GESTIMA_NEW/
├── app/
│   ├── gestima_app.py
│   ├── config.py
│   ├── database.py
│   ├── models/              # Dataclasses
│   ├── routers/             # *_router.py
│   ├── services/            # time_calculator.py, cutting_conditions.py...
│   ├── templates/
│   └── static/
├── data/                    # Excel
├── tests/                   # pytest
└── requirements.txt
```

## SPUŠTĚNÍ

```bash
uvicorn app.gestima_app:app --reload
# http://localhost:8000
# http://localhost:8000/docs
```
