# Next Steps - Post P2 Fáze B

**Date:** 2026-01-24
**Context:** P2 Fáze B (Minimal Snapshot) je dokončena. Tento dokument obsahuje poznámky pro další implementaci.

---

## Immediate Priorities (Based on User Feedback)

### 1. Business Validace - Snapshot Pre-Conditions ⚠️ HIGH PRIORITY

**Problém:** Při implementaci hierarchie materiálů existuje riziko, že do snapshotu se dostane nulová cena materiálu nebo nulová hodinová sazba stroje.

**Impact:**
- Zmrazený batch s nulovou cenou → nevalidní nabídka
- Ztráta důvěry v systém
- Nemožnost rekonstruovat správnou cenu

**Řešení:**
```python
# app/services/snapshot_service.py

async def create_batch_snapshot(batch: Batch, username: str, db: AsyncSession) -> Dict[str, Any]:
    # CRITICAL: Validace PŘED vytvořením snapshotu

    # 1. Validace ceny materiálu
    if material_item.price_per_kg <= 0:
        raise ValueError(
            f"Nelze zmrazit batch #{batch.id}: "
            f"Materiál '{material_item.code}' má nulovou nebo zápornou cenu "
            f"({material_item.price_per_kg} Kč/kg). "
            f"Aktualizujte cenu materiálu před zmrazením nabídky."
        )

    # 2. Validace hodinové sazby stroje
    for op in operations:
        if not op.is_coop:  # Pouze pro vlastní operace
            machine = machines.get(op.machine_id)
            if not machine or machine.hourly_rate <= 0:
                raise ValueError(
                    f"Nelze zmrazit batch #{batch.id}: "
                    f"Operace '{op.name}' má stroj s nulovou nebo zápornou sazbou "
                    f"({machine.hourly_rate if machine else 'N/A'} Kč/hod). "
                    f"Aktualizujte sazbu stroje před zmrazením."
                )

    # 3. Validace kooperace (pokud je coop_price > 0)
    for op in operations:
        if op.is_coop and op.coop_price <= 0:
            logger.warning(
                f"Batch #{batch.id}, operace '{op.name}': "
                f"Kooperace má nulovou cenu. Zkontrolujte."
            )

    # ... rest of snapshot creation ...
```

**User Experience:**
```
❌ PŘED: Zmrazení uspěje → snapshot s nulovou cenou → tichý problém
✅ PO:    Zmrazení selže → HTTP 400 "Aktualizujte cenu materiálu" → uživatel opraví
```

**Testy (CRITICAL):**
```python
# tests/test_snapshots.py

async def test_freeze_batch_with_zero_material_price_fails():
    """Test: Zmrazení batche s nulovou cenou materiálu selže s ValueError"""
    # ... setup ...
    material_item.price_per_kg = 0.0
    await db.commit()

    with pytest.raises(ValueError, match="nulovou nebo zápornou cenu"):
        await freeze_batch(batch.id, db, user)

async def test_freeze_batch_with_zero_hourly_rate_fails():
    """Test: Zmrazení batche s nulovou hodinovou sazbou selže s ValueError"""
    # ... setup ...
    machine.hourly_rate = 0.0
    await db.commit()

    with pytest.raises(ValueError, match="nulovou nebo zápornou sazbou"):
        await freeze_batch(batch.id, db, user)

async def test_freeze_batch_with_valid_data_succeeds():
    """Test: Zmrazení batche s validními daty uspěje"""
    # Verify all prices > 0 before freeze
    assert material_item.price_per_kg > 0
    assert machine.hourly_rate > 0

    result = await freeze_batch(batch.id, db, user)
    assert result.is_frozen is True
```

**Implementation Checklist:**
- [ ] Přidat validace do `snapshot_service.py`
- [ ] Napsat 3 nové testy (zero material, zero hourly, valid data)
- [ ] Update API docs (HTTP 400 error response)
- [ ] Test edge cases (negative prices, None values)

**Estimated Effort:** 1-2 hodiny (simple, high value)

---

### 2. Health Check Endpoint ⚙️ MEDIUM PRIORITY

**Požadavek:** Endpoint GET /health by měl kontrolovat nejen dostupnost DB, ale i **integritu složky se zálohami**, aby byla zajištěna kontinuita dat.

**Kontext:** Production systém potřebuje monitoring - je DB dostupná? Jsou zálohy funkční?

**Health Check Components:**

```python
# app/routers/health_router.py

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check for monitoring systems (Prometheus, Nagios, etc.)

    Returns:
        200 OK: All systems healthy
        503 Service Unavailable: Critical failure (DB down)
        200 OK with "degraded": Non-critical warnings (low disk space, backup issues)
    """
    health = {
        "status": "healthy",  # healthy | degraded | unhealthy
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # 1. DATABASE CHECK (CRITICAL)
    try:
        result = await db.execute(text("SELECT 1"))
        health["checks"]["database"] = {
            "status": "ok",
            "message": "Database accessible"
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = {
            "status": "error",
            "message": str(e)
        }
        raise HTTPException(status_code=503, detail=health)

    # 2. BACKUP FOLDER CHECK (WARNING-LEVEL)
    backup_dir = settings.BACKUP_DIR
    backup_check = check_backup_integrity(backup_dir)

    if backup_check["status"] == "error":
        health["status"] = "degraded"
        health["checks"]["backups"] = backup_check
    elif backup_check["status"] == "warning":
        if health["status"] == "healthy":
            health["status"] = "degraded"
        health["checks"]["backups"] = backup_check
    else:
        health["checks"]["backups"] = backup_check

    # 3. DISK SPACE CHECK (WARNING-LEVEL)
    disk_check = check_disk_space(".")
    if disk_check["status"] == "warning":
        if health["status"] == "healthy":
            health["status"] = "degraded"
        health["checks"]["disk"] = disk_check
    else:
        health["checks"]["disk"] = disk_check

    # 4. (OPTIONAL) RECENT BACKUP CHECK
    # Zkontrolovat, že poslední záloha není starší než X dní
    recent_backup_check = check_recent_backup(backup_dir, max_age_days=7)
    if recent_backup_check["status"] == "warning":
        if health["status"] == "healthy":
            health["status"] = "degraded"
    health["checks"]["recent_backup"] = recent_backup_check

    return health


def check_backup_integrity(backup_dir: str) -> Dict[str, Any]:
    """Kontrola integrity backup složky"""
    if not os.path.exists(backup_dir):
        return {
            "status": "error",
            "message": f"Backup folder '{backup_dir}' not found"
        }

    if not os.path.isdir(backup_dir):
        return {
            "status": "error",
            "message": f"'{backup_dir}' is not a directory"
        }

    if not os.access(backup_dir, os.W_OK):
        return {
            "status": "error",
            "message": f"Backup folder '{backup_dir}' is not writable"
        }

    # Spočítat počet záloh
    try:
        backups = [f for f in os.listdir(backup_dir) if f.endswith('.db') or f.endswith('.db.gz')]
        return {
            "status": "ok",
            "message": f"Backup folder accessible, {len(backups)} backups found",
            "backup_count": len(backups)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading backup folder: {str(e)}"
        }


def check_disk_space(path: str, threshold_gb: float = 1.0) -> Dict[str, Any]:
    """Kontrola volného místa na disku"""
    import shutil
    stat = shutil.disk_usage(path)
    free_gb = stat.free / (1024**3)

    if free_gb < threshold_gb:
        return {
            "status": "warning",
            "message": f"Low disk space: {free_gb:.2f} GB free (threshold: {threshold_gb} GB)",
            "free_gb": round(free_gb, 2),
            "total_gb": round(stat.total / (1024**3), 2)
        }
    else:
        return {
            "status": "ok",
            "message": f"Sufficient disk space: {free_gb:.2f} GB free",
            "free_gb": round(free_gb, 2),
            "total_gb": round(stat.total / (1024**3), 2)
        }


def check_recent_backup(backup_dir: str, max_age_days: int = 7) -> Dict[str, Any]:
    """Kontrola, že poslední záloha není starší než X dní"""
    import glob
    from datetime import datetime, timedelta

    try:
        backups = glob.glob(os.path.join(backup_dir, "*.db")) + \
                  glob.glob(os.path.join(backup_dir, "*.db.gz"))

        if not backups:
            return {
                "status": "warning",
                "message": "No backups found"
            }

        # Najít nejnovější zálohu
        latest_backup = max(backups, key=os.path.getmtime)
        mtime = datetime.fromtimestamp(os.path.getmtime(latest_backup))
        age_days = (datetime.now() - mtime).days

        if age_days > max_age_days:
            return {
                "status": "warning",
                "message": f"Latest backup is {age_days} days old (threshold: {max_age_days} days)",
                "latest_backup": os.path.basename(latest_backup),
                "age_days": age_days
            }
        else:
            return {
                "status": "ok",
                "message": f"Latest backup is {age_days} days old",
                "latest_backup": os.path.basename(latest_backup),
                "age_days": age_days
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking recent backup: {str(e)}"
        }
```

**Response Examples:**

**200 OK (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-24T14:30:00",
  "checks": {
    "database": {
      "status": "ok",
      "message": "Database accessible"
    },
    "backups": {
      "status": "ok",
      "message": "Backup folder accessible, 5 backups found",
      "backup_count": 5
    },
    "disk": {
      "status": "ok",
      "message": "Sufficient disk space: 25.3 GB free",
      "free_gb": 25.3,
      "total_gb": 100.0
    },
    "recent_backup": {
      "status": "ok",
      "message": "Latest backup is 2 days old",
      "latest_backup": "gestima_20260122_143000.db.gz",
      "age_days": 2
    }
  }
}
```

**200 OK (Degraded - warnings):**
```json
{
  "status": "degraded",
  "timestamp": "2026-01-24T14:30:00",
  "checks": {
    "database": {"status": "ok", "message": "Database accessible"},
    "backups": {
      "status": "warning",
      "message": "Backup folder not writable"
    },
    "disk": {
      "status": "warning",
      "message": "Low disk space: 0.8 GB free (threshold: 1.0 GB)",
      "free_gb": 0.8
    },
    "recent_backup": {"status": "ok", "message": "Latest backup is 2 days old"}
  }
}
```

**503 Service Unavailable (Unhealthy - DB down):**
```json
{
  "status": "unhealthy",
  "timestamp": "2026-01-24T14:30:00",
  "checks": {
    "database": {
      "status": "error",
      "message": "Connection refused"
    }
  }
}
```

**Integration with Monitoring:**
```bash
# Prometheus scrape config
curl -s http://localhost:8000/health | jq -r '.status'
# Output: healthy | degraded | unhealthy

# Nagios check
if [ $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health) -eq 200 ]; then
  echo "OK - Service healthy"
  exit 0
else
  echo "CRITICAL - Service unhealthy"
  exit 2
fi
```

**Implementation Checklist:**
- [ ] Vytvořit `app/routers/health_router.py`
- [ ] Registrovat router v `app/gestima_app.py`
- [ ] Napsat testy `tests/test_health.py` (7 testů: ok, db error, backup warnings, disk warning, recent backup warning, combined)
- [ ] Přidat config `HEALTH_CHECK_DISK_THRESHOLD_GB` do `app/config.py`
- [ ] Dokumentovat v API docs (Swagger)

**Estimated Effort:** 2-3 hodiny

---

### 3. UI Indikace Frozen Batch 🎨 MEDIUM PRIORITY

**Požadavek:** V budoucnu bude nutné v šablonách (Jinja2) zajistit, aby pole v `is_frozen` dávkách byla v prohlížeči označena jako readonly nebo disabled.

**Current State:**
- API správně blokuje editaci frozen batches (HTTP 403)
- Frontend NEMÁ vizuální indikaci frozen stavu

**User Pain:**
- Uživatel klikne na "Edit" → zadá změny → klikne "Save" → HTTP 403 chyba
- Frustrující UX (proč mi to nedá editovat?)

**Proposed Solution:**

#### A) Visual Indication (Badge + Styling)
```html
<!-- app/templates/batches.html -->

<div class="batch-card {% if batch.is_frozen %}batch-frozen{% endif %}">
  <!-- Header with freeze badge -->
  <div class="batch-header">
    <h3>Dávka {{ batch.quantity }} ks</h3>

    {% if batch.is_frozen %}
      <span class="badge badge-warning">
        🔒 ZMRAZENO
      </span>
      <div class="freeze-info">
        <small class="text-muted">
          Zmrazeno {{ batch.frozen_at|datetime('%d.%m.%Y %H:%M') }}
          uživatelem {{ batch.frozen_by.username }}
        </small>
      </div>
    {% endif %}
  </div>

  <!-- Form with disabled fields -->
  <form method="POST" action="/api/batches/{{ batch.id }}">
    <div class="form-group">
      <label>Množství</label>
      <input type="number"
             name="quantity"
             value="{{ batch.quantity }}"
             {% if batch.is_frozen %}disabled{% endif %}
             class="form-control">
    </div>

    <!-- Buttons -->
    <div class="button-group">
      {% if batch.is_frozen %}
        <!-- Disabled Save button -->
        <button type="submit" class="btn btn-primary" disabled title="Zmrazený batch nelze editovat">
          💾 Uložit (nedostupné)
        </button>

        <!-- Clone button -->
        <button type="button"
                class="btn btn-secondary"
                onclick="cloneBatch({{ batch.id }})">
          📋 Klonovat (vytvořit editovatelnou kopii)
        </button>

        <!-- Info tooltip -->
        <div class="alert alert-info">
          ℹ️ Tento batch je zmrazený a nelze jej editovat.
          Pro úpravy použijte tlačítko "Klonovat".
        </div>

      {% else %}
        <!-- Normal Save button -->
        <button type="submit" class="btn btn-primary">
          💾 Uložit
        </button>

        <!-- Freeze button (operator/admin) -->
        {% if current_user.role in ['operator', 'admin'] %}
          <button type="button"
                  class="btn btn-warning"
                  onclick="freezeBatch({{ batch.id }})">
            🔒 Zmrazit nabídku
          </button>
        {% endif %}
      {% endif %}
    </div>
  </form>
</div>
```

#### B) JavaScript (Alpine.js or vanilla)
```javascript
// app/static/main.js

function freezeBatch(batchId) {
  if (!confirm('Opravdu chcete zmrazit tento batch? Po zmrazení již nelze editovat.')) {
    return;
  }

  fetch(`/api/batches/${batchId}/freeze`, {
    method: 'POST',
    credentials: 'include'
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(err => {
        throw new Error(err.detail || 'Chyba při zmrazování');
      });
    }
    return response.json();
  })
  .then(data => {
    alert('✅ Batch úspěšně zmrazen!');
    // Reload stránky pro zobrazení frozen stavu
    window.location.reload();
  })
  .catch(err => {
    alert('❌ Chyba při zmrazování: ' + err.message);
  });
}

function cloneBatch(batchId) {
  fetch(`/api/batches/${batchId}/clone`, {
    method: 'POST',
    credentials: 'include'
  })
  .then(response => response.json())
  .then(data => {
    alert(`✅ Vytvořen klon batch #${data.id}`);
    // Redirect na edit stránku nového batche
    window.location.href = `/batches/${data.id}/edit`;
  })
  .catch(err => {
    alert('❌ Chyba při klonování: ' + err.message);
  });
}
```

#### C) CSS (Visual Feedback)
```css
/* app/static/style.css */

/* Frozen batch card styling */
.batch-frozen {
  background-color: #f8f9fa;
  border-left: 4px solid #ffc107;
  opacity: 0.95;
  position: relative;
}

.batch-frozen::before {
  content: "🔒";
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 48px;
  opacity: 0.1;
}

/* Disabled inputs in frozen batch */
.batch-frozen input:disabled,
.batch-frozen select:disabled,
.batch-frozen textarea:disabled {
  background-color: #e9ecef;
  cursor: not-allowed;
  border-color: #ced4da;
}

/* Freeze badge */
.badge-warning {
  background-color: #ffc107;
  color: #212529;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

/* Freeze info */
.freeze-info {
  margin-top: 4px;
}

.freeze-info small {
  font-size: 11px;
  color: #6c757d;
}

/* Alert info box */
.alert-info {
  background-color: #d1ecf1;
  border-left: 3px solid #0c5460;
  padding: 10px;
  margin-top: 10px;
}
```

**Implementation Checklist:**
- [ ] Vytvořit/upravit `app/templates/batches.html` (nebo ekvivalent)
- [ ] Přidat `freezeBatch()` a `cloneBatch()` do `app/static/main.js`
- [ ] Přidat `.batch-frozen` styling do `app/static/style.css`
- [ ] Přidat Jinja2 filter `datetime()` pokud ještě neexistuje
- [ ] Test v prohlížeči (Firefox, Chrome, Safari)

**Estimated Effort:** 2-3 hodiny (závisí na existenci Jinja2 templates)

---

## Additional Recommendations (Not User-Requested)

### 4. Snapshot Versioning 🔄 LOW PRIORITY

**Problem:** JSON struktura snapshotu se může v budoucnu změnit.

**Solution:** Přidat `snapshot_version` do snapshot_data:
```python
snapshot = {
    "snapshot_version": 1,  # ✅ ADD THIS
    "frozen_at": "...",
    "frozen_by": "...",
    "costs": {...},
    "metadata": {...}
}
```

**Benefit:**
- Backward compatibility při změně snapshot struktury
- Možnost upgrade migrace (v1 → v2)

**Implementation:** 10 minut

---

### 5. Batch Update Bloking 🚫 LOW PRIORITY

**Current State:** API endpoint `PUT /api/batches/{id}` NEEXISTUJE.

**Future:** Pokud bude přidán, MUSÍ blokovat update frozen batche:
```python
@router.put("/batches/{id}")
async def update_batch(id: int, data: BatchUpdate, db: AsyncSession, user: User):
    batch = await get_batch_or_404(id, db)

    # ADR-012: Frozen batch nelze editovat
    if batch.is_frozen:
        raise HTTPException(403, "Zmrazený batch nelze editovat. Použijte POST /clone pro vytvoření kopie.")

    # ... rest of update logic ...
```

**Testy:**
```python
async def test_update_frozen_batch_fails():
    """Test: Update frozen batche selže s HTTP 403"""
    frozen_batch = await freeze_batch(batch.id, db, user)

    with pytest.raises(HTTPException) as exc:
        await update_batch(frozen_batch.id, update_data, db, user)

    assert exc.value.status_code == 403
    assert "zmrazený" in exc.value.detail.lower()
```

**Implementation:** Když bude potřeba

---

## Summary

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 🔴 HIGH | 1. Business Validace (snapshot pre-conditions) | 1-2h | **CRITICAL** - data integrity |
| 🟡 MEDIUM | 2. Health Check Endpoint | 2-3h | Production monitoring |
| 🟡 MEDIUM | 3. UI Indikace Frozen Batch | 2-3h | User experience |
| 🟢 LOW | 4. Snapshot Versioning | 10min | Future-proofing |
| 🟢 LOW | 5. Batch Update Blocking | TBD | Only if PUT endpoint added |

**Total Estimated Effort:** 5-8 hours

**Recommended Order:**
1. Business Validace (HIGH - data integrity issue)
2. Health Check (MEDIUM - production requirement)
3. UI Indikace (MEDIUM - UX improvement)
4. Snapshot Versioning (LOW - quick win)

---

## References

- **ADR-012:** `docs/ADR/012-minimal-snapshot.md` - architektonické rozhodnutí
- **P2 Phase B Summary:** `docs/P2-PHASE-B-SUMMARY.md` - kompletní implementační dokumentace
- **CLAUDE.md:** P2 checklist, pravidla, vzory
- **Tests:** `tests/test_snapshots.py` - živá dokumentace use cases

---

**Document Version:** 1.0
**Last Updated:** 2026-01-24
**Author:** Claude (AI Assistant) + User Feedback
