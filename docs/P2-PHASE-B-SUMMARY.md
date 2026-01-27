# P2 Fáze B - Minimal Snapshot Implementation Summary

**Status:** ✅ COMPLETED
**Date:** 2026-01-24
**Version:** 2.10.0

---

## Executive Summary

Implementována **Minimal Snapshot** funkce pro zmrazení cen v nabídkách (Batch). Řeší problém "price decay" - změna ceny materiálu v DB → nabídka z minulého měsíce ukazuje jinou cenu.

**Klíčové výsledky:**
- ✅ 8 nových testů (100% pass rate)
- ✅ 98/99 celková úspěšnost testů
- ✅ 3 nové API endpointy
- ✅ Kompletní ADR-012 dokumentace
- ✅ Breaking change: Part.status odstraněn

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER WORKFLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Vytvoří Part + Operations + Batch                       │
│  2. Vypočítá ceny (LIVE z MaterialItem.price_per_kg)        │
│  3. Zmrazí nabídku: POST /api/batches/{id}/freeze          │
│     ├─ Vytvoří snapshot s aktuálními cenami                 │
│     ├─ is_frozen = True                                     │
│     └─ unit_price_frozen, total_price_frozen (redundantně)  │
│  4. Cena materiálu se změní v DB (+25%)                      │
│  5. Frozen batch stále ukazuje původní cenu ✅               │
│  6. (Volitelně) Clone batch pro novou verzi nabídky         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Database Schema Changes

**File:** `app/models/batch.py`

```python
class Batch(Base, AuditMixin):
    # ... existing fields ...

    # Freeze metadata (ADR-012)
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    frozen_at = Column(DateTime, nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Snapshot (minimal)
    snapshot_data = Column(JSON, nullable=True)

    # Redundantní sloupce pro reporty (hybrid approach)
    unit_price_frozen = Column(Float, nullable=True, index=True)
    total_price_frozen = Column(Float, nullable=True)

    # Relationship
    frozen_by = relationship("User")
```

**Migration Notes:**
- Nové sloupce jsou nullable → existující batches zůstanou `is_frozen=False`
- Není potřeba datová migrace (staré batches = unfrozen)

### 2. Snapshot Service

**File:** `app/services/snapshot_service.py` (NOVÝ)

**Purpose:** Single source of truth pro snapshot logiku

```python
async def create_batch_snapshot(batch: Batch, username: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Vytvoří minimal snapshot pro zmrazení cen batche.

    Returns:
        {
            "frozen_at": "2026-01-24T14:30:00",
            "frozen_by": "admin",
            "costs": {...},  # 6 cen
            "metadata": {...}  # part_number, material_code, material_price_per_kg
        }
    """
```

**Design Decision:** Minimal snapshot (pouze ceny + metadata), ne full snapshot (part + operations + features).

**Rationale:**
- Menší JSON (desítky bytes vs kilobytes)
- Rychlejší queries
- Ceny jsou jediné co se mění a potřebujeme zmrazit

### 3. API Endpoints

**File:** `app/routers/batches_router.py`

#### POST /api/batches/{id}/freeze

**Request:**
```bash
curl -X POST http://localhost:8000/api/batches/123/freeze \
  -H "Cookie: access_token=<jwt>"
```

**Response (200 OK):**
```json
{
  "id": 123,
  "quantity": 10,
  "is_frozen": true,
  "frozen_at": "2026-01-24T14:30:00",
  "frozen_by_id": 1,
  "snapshot_data": {
    "frozen_at": "2026-01-24T14:30:00",
    "frozen_by": "admin",
    "costs": {
      "material_cost": 250.0,
      "machining_cost": 180.0,
      "setup_cost": 50.0,
      "coop_cost": 0.0,
      "unit_cost": 480.0,
      "total_cost": 4800.0
    },
    "metadata": {
      "part_number": "DIL-001",
      "quantity": 10,
      "material_code": "11300",
      "material_price_per_kg": 80.0
    }
  },
  "unit_price_frozen": 480.0,
  "total_price_frozen": 4800.0
}
```

**Error Responses:**
- `404 Not Found` - batch neexistuje
- `409 Conflict` - batch je již zmrazený

**Permissions:** OPERATOR, ADMIN

---

#### POST /api/batches/{id}/clone

**Request:**
```bash
curl -X POST http://localhost:8000/api/batches/123/clone \
  -H "Cookie: access_token=<jwt>"
```

**Response (200 OK):**
```json
{
  "id": 124,
  "part_id": 1,
  "quantity": 10,
  "is_frozen": false,
  "frozen_at": null,
  "snapshot_data": null,
  "unit_cost": 480.0,
  "total_cost": 4800.0
}
```

**Use Case:** Uživatel chce upravit zmrazenou nabídku → naklonuje ji, upraví klon (LIVE ceny).

**Permissions:** OPERATOR, ADMIN

---

#### DELETE /api/batches/{id}

**Behavior:**
- **Frozen batch:** Soft delete (batch.deleted_at)
- **Unfrozen batch:** Hard delete (smazán z DB)

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/batches/123 \
  -H "Cookie: access_token=<jwt>"
```

**Response (200 OK) - Frozen:**
```json
{
  "message": "Zmrazená dávka smazána (soft delete)"
}
```

**Response (200 OK) - Unfrozen:**
```json
{
  "message": "Dávka smazána"
}
```

**Permissions:** ADMIN only

---

### 4. Breaking Changes

#### Part.status REMOVED

**File:** `app/models/part.py`

**Rationale:** Freeze je pouze na Batch level, ne Part level.

**Migration:**
```python
# BEFORE (v2.9.0)
class Part(Base, AuditMixin):
    status = Column(Enum(PartStatus), default=PartStatus.DRAFT)

# AFTER (v2.10.0)
class Part(Base, AuditMixin):
    # status column removed
```

**Impact:**
- `PartStatus` enum odstraněn z `app/models/enums.py`
- Import `PartStatus` odstraněn z `app/models/__init__.py`
- Testy aktualizovány (odstranění `PartStatus` importu)

**Future:** Pokud bude potřeba Part-level workflow, bude znovu přidán s vazbou na Quote modul.

---

## Test Coverage

**File:** `tests/test_snapshots.py` (8 nových testů)

| Test | Purpose | Result |
|------|---------|--------|
| `test_freeze_batch` | Vytvoření snapshotu s aktuálními cenami | ✅ PASS |
| `test_freeze_already_frozen_batch` | HTTP 409 při opakovaném freeze | ✅ PASS |
| `test_freeze_batch_not_found` | HTTP 404 pro neexistující batch | ✅ PASS |
| `test_clone_batch` | Klonování vytvoří nový unfrozen batch | ✅ PASS |
| `test_clone_batch_not_found` | HTTP 404 pro neexistující batch | ✅ PASS |
| `test_frozen_batch_soft_delete` | Soft delete pro frozen batch | ✅ PASS |
| `test_unfrozen_batch_hard_delete` | Hard delete pro unfrozen batch | ✅ PASS |
| `test_price_stability_after_freeze` | Změna ceny materiálu neovlivní frozen batch | ✅ PASS |

**Overall Test Results:**
```bash
======================== 98 passed, 1 skipped in 3.83s =========================
```

**Critical Test:** `test_price_stability_after_freeze`
- Zmrazí batch s cenou materiálu 80 Kč/kg
- Změní cenu materiálu na 100 Kč/kg (+25%)
- Ověří, že frozen batch stále ukazuje 80 Kč/kg ✅

---

## Documentation

### ADR-012: Minimal Snapshot Pattern

**File:** `docs/ADR/012-minimal-snapshot.md`

**Key Decisions:**

1. **Minimal vs Full Snapshot**
   - ✅ Minimal (pouze ceny + metadata)
   - ❌ Full (celá struktura part + operations + features)
   - **Důvod:** Ceny jsou jediné co se mění, minimální data

2. **JSON vs Dedicated Columns**
   - ✅ Hybrid (JSON + redundantní sloupce)
   - **Důvod:** JSON pro flexibilitu, sloupce pro rychlé SQL reporty

3. **Immutability**
   - ✅ Frozen batch nelze editovat/smazat (pouze soft delete)
   - **Důvod:** Ochrana integrity nabídek

4. **Clone Workflow**
   - ✅ POST /clone endpoint
   - **Důvod:** Uživatel potřebuje způsob jak vytvořit novou verzi nabídky

**Trade-offs:**
- JSON není typovaný → možné problémy při změně struktury snapshotu
- Redundance (ceny ve 2 místech) → trade-off za rychlé reporty
- Soft delete queries → musíme filtrovat `deleted_at IS NULL`

**Alternatives Considered:**
- Temporal tables (verzování materials) → over-engineering
- Kopie cen do samostatných sloupců → ztráta metadata

---

## Next Steps (Poznámky k další práci)

### 1. Business Validace (Priority: HIGH)

**Problém:** Snapshot může obsahovat nulovou cenu materiálu nebo nulovou hodinovou sazbu stroje.

**Řešení:**
```python
# app/services/snapshot_service.py

async def create_batch_snapshot(batch: Batch, username: str, db: AsyncSession) -> Dict[str, Any]:
    # ... existing code ...

    # ✅ ADD: Validace cen před vytvořením snapshotu
    if material_item.price_per_kg <= 0:
        raise ValueError(
            f"Nelze zmrazit batch: Materiál '{material_item.code}' má nulovou cenu. "
            f"Aktualizujte cenu materiálu před zmrazením."
        )

    # Pro každý stroj v operacích
    if hourly_rate <= 0:
        raise ValueError(
            f"Nelze zmrazit batch: Stroj má nulovou hodinovou sazbu. "
            f"Aktualizujte sazbu stroje před zmrazením."
        )

    # ... rest of code ...
```

**Testy:**
```python
# tests/test_snapshots.py

async def test_freeze_batch_with_zero_material_price(db_session, sample_batch, mock_user):
    """Test pokusu o zmrazení batche s nulovou cenou materiálu - očekáváme ValueError"""
    # Set material price to 0
    material_item.price_per_kg = 0.0
    await db_session.commit()

    with pytest.raises(ValueError, match="nulovou cenu"):
        await freeze_batch(sample_batch.id, db_session, mock_user)
```

**Soubory k úpravě:**
- `app/services/snapshot_service.py` - přidat validace
- `tests/test_snapshots.py` - přidat 2 nové testy (zero price, zero hourly rate)

---

### 2. Health Check Endpoint (Priority: MEDIUM)

**Požadavek:** GET /health pro monitoring

**Implementace:**
```python
# app/routers/health_router.py (NOVÝ)

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text
import os

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint pro monitoring.

    Kontroluje:
    - DB dostupnost (simple query)
    - Backup složka (existence, zapisovatelnost)
    - Volné místo na disku (warning pokud < 1GB)
    """
    health = {
        "status": "healthy",
        "checks": {}
    }

    # 1. DB check
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = {"status": "error", "message": str(e)}

    # 2. Backup folder check
    backup_dir = "./backups"
    if not os.path.exists(backup_dir):
        health["status"] = "degraded"
        health["checks"]["backups"] = {"status": "warning", "message": "Backup folder not found"}
    elif not os.access(backup_dir, os.W_OK):
        health["status"] = "degraded"
        health["checks"]["backups"] = {"status": "warning", "message": "Backup folder not writable"}
    else:
        health["checks"]["backups"] = {"status": "ok"}

    # 3. Disk space check
    import shutil
    stat = shutil.disk_usage(".")
    free_gb = stat.free / (1024**3)
    if free_gb < 1.0:
        health["status"] = "degraded"
        health["checks"]["disk"] = {"status": "warning", "free_gb": round(free_gb, 2)}
    else:
        health["checks"]["disk"] = {"status": "ok", "free_gb": round(free_gb, 2)}

    if health["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health)

    return health
```

**Response Example (200 OK):**
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok"},
    "backups": {"status": "ok"},
    "disk": {"status": "ok", "free_gb": 25.3}
  }
}
```

**Response Example (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "checks": {
    "database": {"status": "error", "message": "Connection refused"},
    "backups": {"status": "ok"},
    "disk": {"status": "ok", "free_gb": 25.3}
  }
}
```

**Soubory k úpravě:**
- `app/routers/health_router.py` - NOVÝ
- `app/gestima_app.py` - registrovat health_router
- `tests/test_health.py` - NOVÝ (5 testů: ok, db error, backup warning, disk warning, combined)

---

### 3. UI Indikace Frozen Batch (Priority: MEDIUM)

**Požadavek:** Frozen batch fields disabled/readonly v prohlížeči

**Implementace (Jinja2 template):**
```html
<!-- app/templates/batches.html (nebo ekvivalent) -->

<!-- Badge indikace -->
{% if batch.is_frozen %}
  <span class="badge badge-warning">🔒 FROZEN</span>
  <small class="text-muted">
    Zmrazeno {{ batch.frozen_at|datetime }} uživatelem {{ batch.frozen_by.username }}
  </small>
{% endif %}

<!-- Disable inputs -->
<input type="number"
       name="quantity"
       value="{{ batch.quantity }}"
       {% if batch.is_frozen %}disabled{% endif %}
>

<!-- Disable Uložit button -->
<button type="submit"
        class="btn btn-primary"
        {% if batch.is_frozen %}disabled{% endif %}>
  Uložit
</button>

<!-- Show Clone button pro frozen batch -->
{% if batch.is_frozen %}
  <button type="button"
          class="btn btn-secondary"
          onclick="cloneBatch({{ batch.id }})">
    📋 Klonovat (vytvořit editovatelnou kopii)
  </button>
{% endif %}
```

**JavaScript (Alpine.js):**
```javascript
// app/static/main.js

function cloneBatch(batchId) {
  fetch(`/api/batches/${batchId}/clone`, {
    method: 'POST',
    credentials: 'include'
  })
  .then(r => r.json())
  .then(data => {
    alert(`Vytvořen klon batch #${data.id}`);
    // Redirect na edit stránku nového batche
    window.location.href = `/batches/${data.id}/edit`;
  })
  .catch(err => {
    alert('Chyba při klonování: ' + err.message);
  });
}
```

**CSS (pro visual feedback):**
```css
/* app/static/style.css */

.batch-frozen {
  background-color: #f8f9fa;
  border-left: 4px solid #ffc107;
  opacity: 0.8;
}

.batch-frozen input,
.batch-frozen select,
.batch-frozen textarea {
  cursor: not-allowed;
}

.badge-warning {
  background-color: #ffc107;
  color: #212529;
}
```

**Soubory k úpravě:**
- `app/templates/batches.html` (nebo ekvivalent) - přidat badge, disable controls
- `app/static/main.js` - přidat cloneBatch() funkci
- `app/static/style.css` - přidat .batch-frozen styling

---

## Future Work (Quote Module Integration)

**Kontext:** Freeze je prozatím manuální operace (uživatel klikne na tlačítko).

**Budoucí práce:**
1. Vytvořit `Quote` model (nabídka = kolekce batches)
2. Vazba `Batch.quote_id → Quote.id`
3. **Automatický freeze při změně stavu nabídky:**
   ```python
   # app/routers/quotes_router.py

   @router.put("/quotes/{id}/status")
   async def update_quote_status(id: int, status: QuoteStatus, db: AsyncSession):
       if status == QuoteStatus.QUOTED:
           # Auto-freeze všechny batches v nabídce
           for batch in quote.batches:
               if not batch.is_frozen:
                   await freeze_batch(batch.id, db, current_user)
   ```

4. **Workflow stavy:**
   - DRAFT → uživatel vytváří
   - CALCULATED → ceny vypočítány
   - QUOTED → nabídka odeslána zákazníkovi (auto-freeze batches)
   - APPROVED → zákazník schválil
   - LOCKED → fakturováno (immutable)

**Reference:** ADR-012, sekce "Future Work - Quote Module Integration"

---

## Rollback Plan

Pokud by bylo potřeba vrátit změny (emergency):

```bash
# 1. Revert code to v2.9.0
git checkout v2.9.0

# 2. Drop freeze columns (SQL migration)
sqlite3 gestima.db << EOF
ALTER TABLE batches DROP COLUMN is_frozen;
ALTER TABLE batches DROP COLUMN frozen_at;
ALTER TABLE batches DROP COLUMN frozen_by_id;
ALTER TABLE batches DROP COLUMN snapshot_data;
ALTER TABLE batches DROP COLUMN unit_price_frozen;
ALTER TABLE batches DROP COLUMN total_price_frozen;
EOF

# 3. Restore Part.status (pokud potřeba)
# (není potřeba - Part.status nebyl v produkci používán)
```

**Impact:** Žádná data ztracena (freeze fields jsou nové, staré batches zůstanou is_frozen=False).

---

## Performance Considerations

**Snapshot Size:**
- Minimal snapshot: ~200-300 bytes (JSON)
- Full snapshot: ~5-10 KB (celá struktura part + operations)
- **Savings:** 95% redukce velikosti dat

**Query Performance:**
```sql
-- Rychlý report: batches seřazené podle ceny (použití indexu)
SELECT * FROM batches
WHERE is_frozen = true
ORDER BY unit_price_frozen DESC;

-- Pomalé: parsování JSON (ale přijatelné pro single record fetch)
SELECT snapshot_data->'costs'->>'unit_cost' FROM batches WHERE id = 123;
```

**Recommendations:**
- Používat `unit_price_frozen` sloupec pro reporty (indexovaný)
- Používat `snapshot_data` pouze pro detail view (single record)

---

## Changelog Entry

Kompletní záznam v `CHANGELOG.md` - verze 2.10.0

---

## Contact & Support

**Questions:**
- ADR-012 obsahuje kompletní rozhodnutí a trade-offs
- Tests (`tests/test_snapshots.py`) slouží jako živá dokumentace use cases

**Future Enhancements:**
- Sledovat `docs/ADR/` pro nová architektonická rozhodnutí
- Quote module integration (budoucí verze)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-24
**Author:** Claude (AI Assistant)
