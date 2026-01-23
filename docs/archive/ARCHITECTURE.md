# ARCHITECTURE

## Stack
- **Backend:** FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2
- **Frontend:** Jinja2 + HTMX 1.9 + Alpine.js 3.13 + TailwindCSS (CDN)
- **Database:** SQLite + aiosqlite (WAL mode)
- **Server:** Uvicorn
- **Tests:** pytest + pytest-asyncio

## Struktura projektu
```
app/
├── gestima_app.py          # FastAPI entry point
├── config.py               # Settings (pydantic-settings)
├── database.py             # SQLAlchemy async engine + AuditMixin
├── db_helpers.py           # Database helper functions
│
├── models/                 # SQLAlchemy ORM (632 lines)
│   ├── enums.py            # Status, StockType, OperationType, FeatureType
│   ├── part.py             # Part model (audit trail)
│   ├── operation.py        # Operation model
│   ├── feature.py          # Feature model (cutting steps)
│   ├── batch.py            # Batch pricing model
│   ├── machine.py          # Machine definitions
│   ├── material.py         # Material properties
│   └── cutting_condition.py # Cutting parameters
│
├── services/               # Business logic (645 lines)
│   ├── time_calculator.py  # Machining time calculation
│   ├── cutting_conditions.py # Load Vc/f/Ap from Excel
│   ├── price_calculator.py # Material + machining cost
│   ├── feature_definitions.py # Feature types definitions
│   └── reference_loader.py # Excel data loader (caching)
│
├── routers/                # FastAPI routes (415 lines)
│   ├── parts_router.py     # CRUD for parts
│   ├── operations_router.py # CRUD for operations
│   ├── features_router.py  # CRUD for features
│   ├── batches_router.py   # Batch calculations
│   ├── data_router.py      # Load reference data (materials, conditions)
│   └── pages_router.py     # HTML pages (server-rendered)
│
├── templates/              # Jinja2 templates
│   ├── base.html           # Base layout
│   ├── index.html          # Dashboard
│   └── parts/
│       ├── list.html       # Parts list
│       ├── list_fragment.html # HTMX fragment
│       ├── new.html        # Create part form
│       └── edit.html       # Edit part (split-layout)
│
└── static/
    ├── css/gestima.css     # Main stylesheet
    ├── js/gestima.js       # Main JavaScript
    └── img/logo.png
```

## Architektonické principy

### 1. Single Source of Truth
- Výpočty POUZE v Pythonu (services/)
- JavaScript POUZE zobrazuje data z API
- NIKDY neduplikovat logiku (Python vs JS)

### 2. API-First approach
```
User Action → API Call → Backend (calculate + save) → JSON Response → UI Update
```

### 3. Audit Trail
- Každý model má: `created_at/by`, `updated_at/by`, `deleted_at/by`, `version`
- Soft delete pattern (ADR-001)
- Optimistic locking (version field)

### 4. No Hardcoded Values
- Vše z DB/API (materiály, stroje, řezné podmínky)
- Config v `.env` + `config.py`
- Reference data v Excel → načteno při startu

### 5. Service Layer Pattern
```
Router → Service (business logic) → Model (data access) → DB
```

## Data Flow

### Vytvoření dílu
```
1. User: vyplní form → POST /api/parts
2. Backend: validace (Pydantic) → save Part → return JSON
3. Frontend: redirect na /parts/{id}/edit
```

### Výpočet času operace
```
1. User: přidá feature → POST /api/features
2. Backend:
   - Načte cutting conditions (Vc, f, Ap)
   - Vypočítá čas (time_calculator.py)
   - Uloží feature do DB
   - Přepočítá čas celé operace
   - Return JSON (feature + operation)
3. Frontend: aktualizuje UI (čas feature + čas operace)
```

### Změna MODE (LOW/MID/HIGH)
```
1. User: klikne MODE → POST /api/operations/{id}/change-mode
2. Backend:
   - Načte nové Vc/f/Ap pro MODE
   - Přepočítá VŠECHNY features v operaci
   - Uloží nové časy do DB
   - Return JSON (všechny features + operation)
3. Frontend: aktualizuje VŠECHNY časy v UI
```

### Výpočet ceny dávky
```
1. User: zadá množství → POST /api/batches
2. Backend (price_calculator.py):
   - Material cost = volume × density × price/kg
   - Machining cost = time × hourly_rate
   - Setup cost = setup_time × hourly_rate / quantity
   - Total = material + machining + setup + cooperation
3. Frontend: zobrazí cenový ribbon
```

## Klíčové komponenty

### TimeCalculator (time_calculator.py)
- Vstup: geometry (D, L, Ap...) + conditions (Vc, f)
- Výpočet: RPM, feed_rate, cutting_time, passes
- Výstup: predicted_time_sec

### CuttingConditions (cutting_conditions.py)
- Načte Excel: material_group × feature_type × MODE → Vc, f, Ap
- Koeficienty pro drilling (průměr vrtáku)
- Cache pro performance

### PriceCalculator (price_calculator.py)
- Material cost: stock_volume() → weight → price
- Machining cost: Σ(operation_time × machine_rate)
- Setup cost: setup_time × machine_rate / quantity
- Cooperation cost: external services

### FeatureDefinitions (feature_definitions.py)
- Definice všech feature typů (turning, milling, drilling...)
- Validace geometry
- Normalizace vstupů

### ReferenceLoader (reference_loader.py)
- Načte materials.xlsx → Material model
- Načte cutting_conditions.xlsx → CuttingCondition model
- 15min cache pro rychlost

## UI Patterns

### Split Layout (edit.html)
```
┌─────────────┬──────────────────┐
│ LEFT PANEL  │  RIGHT PANEL     │
│ (280px)     │  (flex: 1)       │
│             │                  │
│ Ribbons:    │  Operations:     │
│ - Základy   │  - List operací  │
│ - Materiál  │  - Features      │
│ - Polotovar │  - Časy          │
│ - Cena      │                  │
└─────────────┴──────────────────┘
```

### Ribbon Component
```html
<div class="ribbon">
  <div class="ribbon-header" @click="toggle">
    <div class="ribbon-title">📋 Title</div>
    <div class="ribbon-toggle">▼</div>
  </div>
  <div class="ribbon-body" x-show="expanded">
    <!-- Content -->
  </div>
</div>
```

### HTMX Patterns
```html
<!-- Partial update -->
<div hx-get="/api/parts/list-fragment"
     hx-trigger="load"
     hx-swap="innerHTML">
</div>
```

### Alpine.js Patterns
```javascript
x-data="partEdit({{ part.id }})"  // Component init
x-show="expanded"                  // Toggle visibility
x-model="partData.material_group"  // Two-way binding
@click="updatePart()"              // Event handler
```

## Testing Strategy

### Markers (pytest.ini)
- `@pytest.mark.critical` - Kritické testy (CI/CD)
- `@pytest.mark.business` - Business logika
- `@pytest.mark.system` - Systémové testy

### Test Coverage
- `test_pricing.py` - Price calculations
- `test_calculator.py` - Time calculations
- `test_conditions.py` - Cutting conditions
- `test_models.py` - Model validation
- `test_audit_infrastructure.py` - Audit trail (6373 lines)

## Deployment

### Development
```bash
source venv/bin/activate
uvicorn app.gestima_app:app --reload
```

### Production (TODO)
- User authentication (audit fields ready)
- Error logging
- Rate limiting
- Backup strategy
- HTTPS

## Constraints (DO NOT VIOLATE)

❌ NO React, Vue, Node.js, npm, Webpack
❌ NO client-side calculations (all in Python)
❌ NO hardcoded values (all from DB/API)
❌ NO duplicate logic (DRY principle)
✅ YES Python backend for ALL logic
✅ YES type hints everywhere
✅ YES tests for business logic
✅ YES Czech documentation
