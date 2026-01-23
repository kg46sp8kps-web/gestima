# DB ARCHITECTURE

## Database
- **Type:** SQLite 3
- **Driver:** aiosqlite (async)
- **Mode:** WAL (Write-Ahead Logging)
- **Location:** `gestima.db`

## Core Tables

### parts (Díly)
```sql
id                  INTEGER PRIMARY KEY
part_number         TEXT NOT NULL UNIQUE     -- Číslo výkresu
name                TEXT                     -- Název dílu
status              TEXT                     -- draft/active/archived
material_group      TEXT                     -- Kód materiálu (11xxx, 12xxx...)
material_name       TEXT                     -- Označení (1.4301, S235...)
stock_type          TEXT                     -- tyc/trubka/prizez/odlitek/plech
stock_diameter      REAL                     -- mm
stock_diameter_inner REAL                    -- mm (pro trubky)
stock_length        REAL                     -- mm
stock_width         REAL                     -- mm (pro přířez/plech)
stock_height        REAL                     -- mm
drawing_path        TEXT                     -- Cesta k výkresu
-- Audit fields (AuditMixin)
created_at          DATETIME
created_by          TEXT
updated_at          DATETIME
updated_by          TEXT
deleted_at          DATETIME
deleted_by          TEXT
version             INTEGER                  -- Optimistic locking
```

**Relationships:**
- `operations` (1:N)
- `batches` (1:N)

**Indexes:**
- `part_number` (UNIQUE)
- `status`
- `deleted_at`

---

### operations (Operace obrábění)
```sql
id                  INTEGER PRIMARY KEY
part_id             INTEGER NOT NULL         -- FK → parts.id
sequence            INTEGER                  -- Pořadí operace (1, 2, 3...)
operation_type      TEXT                     -- turning/milling/drilling/grinding/cooperation
machine_id          INTEGER                  -- FK → machines.id
cutting_mode        TEXT                     -- LOW/MID/HIGH
setup_time_min      REAL                     -- Čas seřízení [min]
unit_time_min       REAL                     -- Čas obrábění [min] (počítané)
note                TEXT
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Relationships:**
- `part` (N:1)
- `machine` (N:1)
- `features` (1:N)

**Indexes:**
- `part_id`
- `sequence`

---

### features (Kroky obrábění)
```sql
id                  INTEGER PRIMARY KEY
operation_id        INTEGER NOT NULL         -- FK → operations.id
feature_type        TEXT                     -- turning_external/drilling/milling_face...
sequence            INTEGER                  -- Pořadí kroku
-- Geometry (feature-specific)
diameter            REAL
diameter_initial    REAL
length              REAL
width               REAL
depth               REAL
thread_pitch        REAL
tool_diameter       REAL
-- Cutting conditions (locked values)
vc                  REAL                     -- Řezná rychlost [m/min]
f                   REAL                     -- Posuv [mm/ot nebo mm/zub]
ap                  REAL                     -- Hloubka řezu [mm]
locked_vc           BOOLEAN
locked_f            BOOLEAN
locked_ap           BOOLEAN
-- Calculated values
predicted_time_sec  REAL                     -- Vypočítaný čas [s]
note                TEXT
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Relationships:**
- `operation` (N:1)

**Indexes:**
- `operation_id`
- `sequence`

---

### batches (Dávky a ceny)
```sql
id                  INTEGER PRIMARY KEY
part_id             INTEGER NOT NULL         -- FK → parts.id
quantity            INTEGER                  -- Množství kusů
material_cost_total REAL                     -- Materiál celkem [Kč]
machining_cost_total REAL                    -- Obrábění celkem [Kč]
setup_cost_total    REAL                     -- Seřízení celkem [Kč]
cooperation_cost_total REAL                  -- Kooperace celkem [Kč]
unit_cost           REAL                     -- Cena/kus [Kč]
total_cost          REAL                     -- Celkem [Kč]
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Relationships:**
- `part` (N:1)

**Indexes:**
- `part_id`

---

## Reference Tables

### machines (Stroje)
```sql
id                  INTEGER PRIMARY KEY
name                TEXT NOT NULL UNIQUE     -- EMCO, HAAS, MAZAK...
machine_type        TEXT                     -- lathe/mill/grinder
hourly_rate         REAL                     -- Hodinová sazba [Kč/h]
max_rpm             INTEGER                  -- Max. otáčky
is_active           BOOLEAN
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Used by:** `operations.machine_id`

---

### materials (Materiály)
```sql
id                  INTEGER PRIMARY KEY
code                TEXT NOT NULL UNIQUE     -- 11xxx, 12xxx, 13xxx...
name                TEXT                     -- Ocel nelegovaná, Nerez...
density             REAL                     -- kg/dm³
price_per_kg        REAL                     -- Kč/kg
cutting_group       TEXT                     -- Pro výběr řezných podmínek
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Loaded from:** `data/archive/materials.xlsx`

---

### cutting_conditions (Řezné podmínky)
```sql
id                  INTEGER PRIMARY KEY
material_group      TEXT                     -- 11xxx, 12xxx...
feature_type        TEXT                     -- turning_external, drilling...
cutting_mode        TEXT                     -- LOW/MID/HIGH
vc                  REAL                     -- Řezná rychlost [m/min]
f                   REAL                     -- Posuv [mm/ot nebo mm/zub]
ap                  REAL                     -- Hloubka řezu [mm]
-- Audit fields
created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, version
```

**Loaded from:** `data/archive/cutting_conditions.xlsx`

**Used by:** `time_calculator.py`, `cutting_conditions.py`

---

## Enums

### PartStatus (enums.py)
- `draft` - Rozpracováno
- `active` - Aktivní
- `archived` - Archivováno

### StockType
- `tyc` - Tyč (kruhová)
- `trubka` - Trubka (dutá)
- `prizez` - Přířez (hranol)
- `odlitek` - Odlitek
- `plech` - Plech

### OperationType
- `turning` - Soustružení
- `milling` - Frézování
- `drilling` - Vrtání
- `grinding` - Broušení
- `cooperation` - Kooperace (externí)

### FeatureType (17 typů)
- `turning_external` - Soustružení vnější
- `turning_internal` - Soustružení vnitřní
- `turning_face` - Čelní soustružení
- `turning_grooving` - Zapichování
- `milling_face` - Čelní frézování
- `milling_pocket` - Kapsář
- `milling_profile` - Profilové frézování
- `drilling` - Vrtání
- `boring` - Vyvrtávání
- `reaming` - Vystružování
- `tapping` - Závitování
- `chamfering` - Srážení hran
- `knurling` - Rýhování
- `threading_external` - Závit vnější
- `threading_internal` - Závit vnitřní
- `grinding_external` - Broušení vnější
- `grinding_internal` - Broušení vnitřní

### CuttingMode
- `LOW` - Nízká řezná rychlost (hrubování, špatné podmínky)
- `MID` - Střední (standardní)
- `HIGH` - Vysoká (dokončování, dobrá kvalita materiálu)

---

## Audit Trail Pattern (AuditMixin)

**All tables include:**
```python
created_at: datetime      # Kdy vytvořeno
created_by: str          # Kdo vytvořil (user_id)
updated_at: datetime      # Poslední změna
updated_by: str          # Kdo změnil
deleted_at: datetime      # Soft delete (NULL = aktivní)
deleted_by: str          # Kdo smazal
version: int             # Optimistic locking
```

**Soft Delete:**
- Záznamy se NIKDY fyzicky nemažou
- `deleted_at IS NULL` = aktivní
- `deleted_at IS NOT NULL` = smazané

**Optimistic Locking:**
- Při UPDATE kontrola: `WHERE version = old_version`
- Increment: `version = version + 1`
- Conflict → `409 Conflict`

**See:** [ADR-001](docs/ADR/001-soft-delete-pattern.md)

---

## Relationships (ERD)

```
parts (1) ──────────────┬── (N) operations
                        │
                        └── (N) batches

operations (1) ──────── (N) features
operations (N) ──────── (1) machines

cutting_conditions ← (lookup) → features
materials ← (lookup) → parts
```

---

## Indexes Strategy

**Primary Keys:** Auto-increment INTEGER (not UUID)
- Why: Simplicity, performance (ADR-003)

**Foreign Keys:** Indexed automatically
- `operations.part_id`
- `features.operation_id`
- `batches.part_id`

**Soft Delete:** Index on `deleted_at`
```sql
CREATE INDEX idx_parts_deleted_at ON parts(deleted_at);
```

**Unique Constraints:**
- `parts.part_number`
- `machines.name`
- `materials.code`

---

## Data Loading

### Startup (database.py)
1. Create tables if not exist
2. Load reference data:
   - `materials.xlsx` → `materials` table
   - `cutting_conditions.xlsx` → `cutting_conditions` table

### Reference Data Cache (15 min)
- `reference_loader.py` caches Excel data
- Invalidate on file change

---

## SQLAlchemy Async

### Engine (database.py)
```python
engine = create_async_engine(
    "sqlite+aiosqlite:///gestima.db",
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False}
)

# WAL mode for concurrent access
async with engine.begin() as conn:
    await conn.execute(text("PRAGMA journal_mode=WAL"))
```

### Session
```python
AsyncSession = async_sessionmaker(
    engine,
    expire_on_commit=False
)
```

### Usage in routers
```python
async with AsyncSession() as session:
    result = await session.execute(select(Part).where(...))
    part = result.scalar_one_or_none()
```

---

## Migration Strategy (TODO)

**Current:** No migrations (dev phase)

**Future:** Alembic
```bash
alembic init alembic
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## Backup Strategy (TODO)

**Current:** Manual backups

**Future:**
- Daily backup: `cp gestima.db backups/gestima_$(date +%Y%m%d).db`
- Keep last 30 days
- Cloud sync (Dropbox, Google Drive)

---

## Performance

**WAL Mode Benefits:**
- 10-100x faster concurrent reads
- Writes don't block reads
- Better crash recovery

**Indexes:**
- All FK indexed
- Soft delete filtered queries fast

**Caching:**
- Reference data (materials, conditions) cached 15min
- Excel parsing expensive → cache results

---

## Constraints

✅ SQLite sufficient for 10k+ parts
✅ Async I/O prevents blocking
✅ WAL mode for concurrent users
❌ NO raw SQL (use SQLAlchemy)
❌ NO CASCADE deletes (soft delete only)
