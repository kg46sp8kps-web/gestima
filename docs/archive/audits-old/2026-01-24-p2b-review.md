# Auditní zpráva P2 Fáze B - Post-Implementation Review

**Datum:** 2026-01-24
**Scope:** Minimal Snapshot implementace (ADR-012)
**Auditor:** External Review
**Verze dokumentu:** 1.0

---

## Executive Summary

P2 Fáze B (Minimal Snapshot) byla úspěšně implementována a všechny testy (8/8) prošly. Identifikovány však byly 4 kritické/střední nálezy, které je nutné vyřešit před nasazením do produkce.

**Aktuální stav:**
- ✅ Batch freeze funguje (is_frozen, snapshot_data)
- ✅ Clone batch funguje
- ✅ Soft delete pro frozen batches
- ✅ Price stability po freeze
- ⚠️ 2 HIGH a 2 MEDIUM nálezy vyžadují řešení

---

## A1: "The Frozen Ghost" - Inkonzistence geometrie [CRITICAL]

### Popis rizika

**Problém:** Zmrazený Batch s `is_frozen=True` může mít metadata odpovídající staré geometrii, zatímco LIVE data v Operations/Features jsou jiná.

**Scénář:**
1. Uživatel vytvoří Part s operacemi (soustružení Ø50 × 100 mm)
2. Vytvoří Batch, zmrazí (snapshot obsahuje délku 100 mm)
3. Jiný uživatel změní geometrii: délka → 150 mm (v Operation/Feature)
4. Frozen Batch stále ukazuje cenu za 100 mm (snapshot), ale technologie je jiná

**Root Cause:** Snapshot neobsahuje hash ani verzi zdrojových dat (Part, Operations, Features).

### Impact

- ❌ **Imutabilita je iluze** - máme zmrazenou cenu, ale nevíme k jaké verzi technologie se vztahuje
- ❌ **Audit selhává** - nelze rekonstruovat, jestli cena odpovídá aktuální geometrii
- ❌ **Business riziko** - nabídka za 5000 Kč odpovídá staré geometrii, výroba podle nové → ztráta

### Navržené řešení

**Varianta A: Geometry Hash (doporučeno)**

```python
# app/services/snapshot_service.py

def calculate_geometry_hash(part: Part, operations: List[Operation], features: List[Feature]) -> str:
    """Vypočítá SHA256 hash geometrie pro detekci změn."""
    import hashlib

    data = {
        "part": {
            "stock_type": part.stock_type,
            "diameter": part.diameter,
            "length": part.length,
            "material_group_id": part.material_group_id,
        },
        "operations": [
            {
                "id": op.id,
                "operation_type": op.operation_type,
                "cutting_mode": op.cutting_mode,
            }
            for op in operations
        ],
        "features": [
            {
                "id": f.id,
                "feature_type": f.feature_type,
                "diameter": f.diameter,
                "length": f.length,
                "depth": f.depth,
            }
            for f in features
        ],
    }

    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


async def create_batch_snapshot(batch: Batch, username: str, db: AsyncSession) -> Dict[str, Any]:
    # ... existing code ...

    # PŘIDAT: Geometry hash
    geometry_hash = calculate_geometry_hash(part, operations, features)

    snapshot = {
        "snapshot_version": 1,  # Pro budoucí změny struktury
        "frozen_at": datetime.utcnow().isoformat(),
        "frozen_by": username,
        "geometry_hash": geometry_hash,  # ✅ NOVÉ
        "costs": { ... },
        "metadata": { ... }
    }
    return snapshot


def get_batch_costs(batch: Batch, db: AsyncSession) -> Dict[str, Any]:
    """Vrátí ceny - ověří, že geometrie se nezměnila."""
    if batch.is_frozen and batch.snapshot_data:
        # VALIDACE: Zkontrolovat hash
        current_hash = calculate_geometry_hash(batch.part, ...)
        snapshot_hash = batch.snapshot_data.get("geometry_hash")

        if current_hash != snapshot_hash:
            # CRITICAL WARNING
            return {
                "costs": batch.snapshot_data["costs"],
                "warning": "GEOMETRY_CHANGED",
                "message": "⚠️ Technologie dílu byla změněna po zmrazení nabídky. Cena nemusí odpovídat!",
                "hash_mismatch": {
                    "snapshot": snapshot_hash,
                    "current": current_hash
                }
            }

        return batch.snapshot_data["costs"]
    else:
        # LIVE ceny
        return { ... }
```

**Varianta B: Soft Lock (preventivní)**

- Frozen Batch → automaticky nastaví Part.is_locked = True
- Locked Part nelze editovat (HTTP 403)
- Edice Part vyžaduje unfreeze všech batches (nebo clone)

**Trade-offs:**
- A: Detekuje změny, ale nedokáže jim zabránit → lepší pro flexibilitu
- B: Brání změnám, ale komplikuje workflow → lepší pro data integrity

### Priorita a status

- **Priorita:** 🔴 HIGH (DATA INTEGRITY)
- **Status:** ❌ TODO
- **Target:** P2 Fáze C nebo před nasazením do produkce
- **Effort:** 4-6 hodin (implementace + testy)

### Testy (required)

```python
# tests/test_snapshot_geometry.py

async def test_frozen_batch_detects_geometry_change():
    """Test: Změna geometrie po freeze vyvolá warning"""
    # 1. Freeze batch (geometry hash = ABC123)
    frozen = await freeze_batch(batch.id, db, user)
    assert frozen.snapshot_data["geometry_hash"] == "ABC123"

    # 2. Změnit geometrii
    operation.length = 150  # was 100
    await db.commit()

    # 3. Načíst costs → WARNING
    costs = await get_batch_costs(frozen, db)
    assert costs["warning"] == "GEOMETRY_CHANGED"
    assert "Technologie dílu byla změněna" in costs["message"]


async def test_frozen_batch_unchanged_geometry_no_warning():
    """Test: Beze změny geometrie žádný warning"""
    frozen = await freeze_batch(batch.id, db, user)
    costs = await get_batch_costs(frozen, db)
    assert "warning" not in costs
```

---

## A2: "The Silent Failure" - Absence monitoringu [CRITICAL]

### Popis rizika

**Problém:** P1 požadavek "Backup strategie" je splněn (CLI: backup, backup-list, backup-restore), ale chybí monitoring. Pokud selže backup folder, dojde místo na disku nebo SQLite dosáhne limitu, dozvíme se až při ztrátě dat.

**Scénář:**
1. Produkce běží měsíce
2. Backup folder dosáhne limitu (disk full)
3. Aplikace funguje, ale backupy selžou (tichá chyba)
4. Dojde k havárii DB → restore selže → **DATA LOSS**

**Root Cause:** P1 requirement "Health check endpoint" je ❌ CHYBÍ (viz CLAUDE.md)

### Impact

- ❌ **Zero visibility** do health stavu produkce
- ❌ **Delayed detection** - problém zjistíme až při katastrofě
- ❌ **No monitoring integration** - nelze zapojit Prometheus, Nagios, Uptime Robot

### Navržené řešení

**Implementace:** Viz [docs/NEXT-STEPS.md](NEXT-STEPS.md) sekce "Health Check Endpoint"

**Checklist:**
- [ ] Vytvořit `app/routers/health_router.py`
- [ ] Checks:
  - Database connectivity (SELECT 1)
  - Backup folder exists + writable
  - Disk space > threshold (1 GB)
  - Recent backup age < 7 days
- [ ] Response:
  - `200 OK` - healthy
  - `200 OK + degraded` - warnings (low disk, old backup)
  - `503 Service Unavailable` - critical (DB down)
- [ ] Testy: 7 testů (ok, db error, backup warnings, disk warning, combined)

### Priorita a status

- **Priorita:** 🔴 HIGH (OPERATIONS)
- **Status:** ⚠️ TRACKED in NEXT-STEPS.md (ale ne jako formální riziko)
- **Target:** P2 Fáze C
- **Effort:** 2-3 hodiny

---

## A3: "The Zero-Price Bomb" - Kontaminace snapshotu [MEDIUM]

### Popis rizika

**Problém:** Aktuální kód (`snapshot_service.py`) dovoluje zmrazit Batch s nulovou cenou materiálu nebo nulovou hodinovou sazbou stroje. Výsledek: nevalidní snapshot, který už nikdy neopravíš (imutabilní).

**Scénář:**
1. Uživatel vytvoří MaterialItem s `price_per_kg = 0` (placeholder)
2. Vytvoří Part s tímto materiálem
3. Zmrazí Batch → snapshot obsahuje `material_price_per_kg: 0`
4. Později opraví cenu materiálu → 80 Kč/kg
5. Frozen Batch stále ukazuje 0 Kč → **nevalidní nabídka**

**Root Cause:** Chybí pre-freeze validace.

### Impact

- ❌ **Kontaminace DB** nevalidními snapshoty
- ❌ **Ztráta důvěry** v systém (nabídka s nulovou cenou)
- ❌ **Nelze opravit** - snapshot je imutabilní

### Navržené řešení

**Implementace:** Viz [docs/NEXT-STEPS.md](NEXT-STEPS.md) sekce "Business Validace"

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
                    f"Operace '{op.name}' má stroj s nulovou nebo zápornou sazbou. "
                    f"Aktualizujte sazbu stroje před zmrazením."
                )

    # ... rest of snapshot creation ...
```

### Priorita a status

- **Priorita:** 🟡 MEDIUM (DATA QUALITY)
- **Status:** ✅ TRACKED in NEXT-STEPS.md
- **Target:** P2 Fáze C
- **Effort:** 1-2 hodiny

---

## A4: "The UX Trap" - Frontend inkonzistence [MEDIUM]

### Popis rizika

**Problém:** API vrací HTTP 403 při pokusu editovat frozen batch, ale UI (podle checklistu) stále nemá vizuální indikaci. Uživatel "vypadá" že může editovat, pak dostane chybu.

**Scénář:**
1. Uživatel otevře frozen batch v prohlížeči
2. UI vypadá normálně (editable fields, tlačítko "Uložit")
3. Uživatel změní množství, klikne "Uložit"
4. HTTP 403 "Zmrazený batch nelze editovat"
5. Frustrace - "Proč mi to nedalo vědět hned?"

**Root Cause:** Backend/Frontend inkonzistence.

### Impact

- ❌ **Špatný UX** - frustrující pro uživatele
- ❌ **Zbytečný load** - nepotřebné API requesty
- ❌ **Confusion** - uživatel neví proč nelze editovat

### Navržené řešení

**Implementace:** Viz [docs/NEXT-STEPS.md](NEXT-STEPS.md) sekce "UI Indikace Frozen Batch"

**Checklist:**
- [ ] Badge "🔒 ZMRAZENO" v UI
- [ ] Disabled input fields pro frozen batch
- [ ] Disabled "Uložit" button + tooltip "Zmrazený batch nelze editovat"
- [ ] Tlačítko "📋 Klonovat" pro vytvoření editovatelné kopie
- [ ] CSS: `.batch-frozen` styling (opacity, border)

### Priorita a status

- **Priorita:** 🟡 MEDIUM (UX)
- **Status:** ✅ TRACKED in NEXT-STEPS.md
- **Target:** P2 Fáze C
- **Effort:** 2-3 hodiny

---

## Shrnutí

| Nález | Typ | Priorita | Status | Effort | Target |
|-------|-----|----------|--------|--------|--------|
| A1: Frozen Ghost | Data Integrity | 🔴 HIGH | ❌ TODO | 4-6h | P2C / Pre-Prod |
| A2: Silent Failure | Operations | 🔴 HIGH | ⚠️ Tracked | 2-3h | P2C |
| A3: Zero-Price Bomb | Data Quality | 🟡 MEDIUM | ✅ Tracked | 1-2h | P2C |
| A4: UX Trap | User Experience | 🟡 MEDIUM | ✅ Tracked | 2-3h | P2C |

**Total Effort:** 9-14 hodin (1-2 dny práce)

---

## Doporučení

### Před nasazením do produkce

**MUSÍ být vyřešeno:**
- ✅ A1: Frozen Ghost (geometry hash) - **CRITICAL DATA INTEGRITY**
- ✅ A2: Silent Failure (health check) - **CRITICAL OPERATIONS**

**Mělo by být vyřešeno:**
- ⚠️ A3: Zero-Price Bomb (pre-freeze validace) - preventivní ochrana
- ⚠️ A4: UX Trap (UI indikace) - lepší UX

### Navržený plán P2 Fáze C

1. **Týden 1:**
   - A2: Health Check Endpoint (2-3h)
   - A3: Zero-Price Validace (1-2h)
   - A4: UI Indikace (2-3h)
   - **Celkem: 5-8h**

2. **Týden 2:**
   - A1: Geometry Hash (4-6h)
   - Integrační testy (2h)
   - Dokumentace (1h)
   - **Celkem: 7-9h**

**Total: 12-17 hodin (2 týdny v rámci běžného vývoje)**

---

## Reference

- **ADR-012:** [docs/ADR/012-minimal-snapshot.md](ADR/012-minimal-snapshot.md) - architektonické rozhodnutí
- **NEXT-STEPS:** [docs/NEXT-STEPS.md](NEXT-STEPS.md) - implementační plán (A2, A3, A4 už tracked)
- **P2B Summary:** [docs/P2-PHASE-B-SUMMARY.md](P2-PHASE-B-SUMMARY.md) - implementační dokumentace
- **Tests:** `tests/test_snapshots.py` - živá dokumentace

---

**Verze dokumentu:** 1.0
**Datum:** 2026-01-24
**Autor:** External Audit Review
