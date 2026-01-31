# Seed Scripts Testing - Dokumentace

**Verze:** 1.0 (2026-01-28)
**Autor:** Roy (pod auditem)
**Status:** ✅ Implemented & Tested

---

## 🎯 Účel

Auto-validace seed scriptů proti schema změnám. Prevence L-015 anti-pattern (změna validace aby pasovala špatná data).

**Problém který řeší:**
```
Změníš DB schema → Seed scripts broken → Demo nefunguje → Maintenance hell
```

**Řešení:**
```
Změníš schema → pytest failne → MUSÍŠ opravit seed → Demo funguje vždy ✅
```

---

## 🏗️ Architektura

### Před (bez testů):
```
scripts/
├── seed_machines.py          # Samostatný script
├── seed_material_catalog.py  # Standalone
└── seed_complete_part.py     # Standalone

❌ Žádná validace
❌ Broken seedy se zjistí až při spuštění
❌ Maintenance burden (manuální testing)
```

### Po (s testy):
```
scripts/
├── seed_machines.py          # ✅ Session parameter (testovatelné!)
├── seed_material_catalog.py  # ⚠️ TODO (subprocess test OK zatím)
└── seed_complete_part.py     # ⚠️ TODO

tests/
└── test_seed_scripts.py      # ✅ Auto-validace
    ├── test_seed_machines_compliance       # Fast (direct call)
    ├── test_seed_demo_command_succeeds     # Integration (subprocess)
    ├── test_seed_machines_data_passes_validation
    └── test_seed_scripts_have_session_parameter
```

---

## 📝 Implementační Vzor

### Seed Script Pattern (RECOMMENDED):

```python
# scripts/seed_XXX.py

async def seed_XXX(session=None):
    """Seed XXX entities

    Args:
        session: Optional AsyncSession (pro testy). If None, vytvoří vlastní.

    Returns:
        int: Počet vytvořených entit
    """
    # Use provided session or create own
    own_session = session is None
    if own_session:
        session = async_session()
        session = await session.__aenter__()

    try:
        created = 0

        for data in SEED_DATA:
            # Check if exists
            existing = await session.execute(
                select(Model).where(Model.code == data["code"])
            )
            if existing.scalar_one_or_none():
                continue

            # Create
            entity = Model(**data)
            session.add(entity)
            created += 1

        # Commit only if we own the session
        if own_session:
            await session.commit()

        return created
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(seed_XXX())
```

**Klíčové vlastnosti:**
- ✅ `session=None` parameter (umožňuje testování)
- ✅ Kontrola existence (idempotent)
- ✅ Commit pouze pokud vlastní session
- ✅ Zachována standalone funkcionalita
- ✅ Return count (pro assertions v testech)

---

## 🧪 Test Pattern

### Test Template:

```python
# tests/test_seed_scripts.py

@pytest.mark.asyncio
async def test_seed_XXX_compliance(db_session):
    """
    seed_XXX.py MUST produce valid data that passes business rules.

    Validates:
    - Entities exist
    - Required fields present
    - ADR compliance
    - No duplicates
    """
    from scripts.seed_XXX import seed_XXX

    # Run seed
    try:
        created = await seed_XXX(session=db_session)
        assert created >= 0, "Seed function failed"
    except Exception as e:
        pytest.fail(f"❌ seed_XXX() failed: {e}")

    # Validate output
    result = await db_session.execute(select(Model))
    entities = result.scalars().all()

    assert len(entities) >= EXPECTED_MIN, f"Expected at least {EXPECTED_MIN}, found {len(entities)}"

    for entity in entities:
        # Required fields
        assert entity.code, f"Entity {entity.id} missing code"

        # Business rules (ADRs)
        assert entity.field > 0, f"Entity {entity.code} violates ADR-XXX"

    # Check duplicates
    result = await db_session.execute(
        select(Model.code, func.count(Model.code))
        .group_by(Model.code)
        .having(func.count(Model.code) > 1)
    )
    duplicates = result.all()
    assert len(duplicates) == 0, f"Duplicate codes: {duplicates}"
```

---

## 📋 Co Seed-Demo Vytváří?

### ✅ Reference Data (Catalog):

**seed_material_catalog.py:**
- Material Groups (12): OCEL-KONS, OCEL-AUTO, NEREZ, etc.
- Material Price Categories (46): Kombinace materiálu + tvaru
- Material Price Tiers: 0-15kg, 15-100kg, 100+kg pro každou kategorii

**seed_material_norms_complete.py:**
- Material Norms (479): W.Nr., EN ISO, ČSN, AISI standards
- Mapování mezi různými normami (1.0503 = C45 = 12050)

**seed_machines.py:**
- Machines (5): NLX2000, CTX450, SPRINT32, DMU50, MAZAK510
- ADR-016 compliant hourly rate breakdowns
- Machine capabilities (axes, bar feeder, milling, etc.)

**seed_material_items.py:**
- MaterialItems (4): C45-ROUND-20, C45-ROUND-30, C45-ROUND-40, NEREZ-ROUND-20
- Concrete stock items ready for part creation
- Links to MaterialGroup and MaterialPriceCategory

**seed_demo_parts.py:**
- Parts (3): Demo Hřídel 1, Demo Pouzdro, Demo Šroub
- ADR-017 compliant 7-digit part_numbers
- Links to MaterialItems for display in UI

**create-admin:**
- Demo user: demo / demo123 (ADMIN role)

### ❌ Co Seed-Demo NEVYTVÁŘÍ:

**Transactional Data (manual/import):**
- ❌ Operations (operace: "Soustruž Ø18", "Vrtat 4x M6")
- ❌ Batches (výrobní dávky: "100 ks @ 2026-01-28")
- ❌ Production data (work orders, quotes, etc.)

**Proč?**
- Reference data + demo entities = enough for UI testing & development
- Real transactional data = project-specific, high volume
- Import/API = better fit for production data
- Seed = focused on development & testing workflow

---

## 🚀 Usage

### Vývoj (každodenní použití):

```bash
# Quick check (fast tests)
python3 gestima.py test tests/test_seed_scripts.py

# Include integration test (slow)
python3 gestima.py test tests/test_seed_scripts.py -m slow

# Just machines
python3 gestima.py test tests/test_seed_scripts.py::test_seed_machines_compliance
```

### CI/CD Pipeline:

```yaml
# .github/workflows/test.yml
- name: Test seed scripts
  run: python3 gestima.py test tests/test_seed_scripts.py -v
```

### Debug když test failne:

```bash
# 1. Zjisti CO selhalo
python3 gestima.py test tests/test_seed_scripts.py -v --tb=short

# 2. Spusť seed standalone (debug)
python3 scripts/seed_machines.py

# 3. Zkontroluj ADRs
ls docs/ADR/

# 4. Oprav seed data (NE validaci!)
vim scripts/seed_machines.py
```

---

## 📊 Current Coverage

| Seed Script | Test Status | Session Param | Notes |
|-------------|-------------|---------------|-------|
| `seed_machines.py` | ✅ Full | ✅ Yes | ADR-016 validation |
| `seed_material_items.py` | ✅ Full | ✅ Yes | MaterialItem FK validation |
| `seed_demo_parts.py` | ✅ Full | ✅ Yes | ADR-017 part_number format |
| `seed_material_catalog.py` | ⚠️ Integration | ❌ No | Subprocess test (OK) |
| `seed_material_norms_complete.py` | ⚠️ Integration | ❌ No | Subprocess test (OK) |

**Test Execution Time:**
- Fast tests (direct call): ~0.2s
- Integration test (subprocess): ~2.5s

**Seeded Data Stats (production DB after seed-demo):**
```
✅ CATALOG DATA (reference data):
   Material Groups: 12 (OCEL-KONS, OCEL-AUTO, NEREZ, etc.)
   Material Price Categories: 46 (shape + material combinations)
   Material Norms: 479 (DIN EN, ČSN, AISI standards)
   Machines: 5 (NLX2000, CTX450, SPRINT32, DMU50, MAZAK510)

✅ DEMO DATA (for UI testing):
   Material Items: 4 (C45-ROUND-20/30/40, NEREZ-ROUND-20)
   Parts: 3 (Demo Hřídel 1, Demo Pouzdro, Demo Šroub)

❌ PRODUCTION TRANSACTIONAL DATA (created manually/import):
   Operations: 0 (operace na částech)
   Batches: 0 (výrobní dávky)
   Work Orders: 0 (výrobní příkazy)

💡 WHY?
   Seed-demo creates:
   - REFERENCE DATA (catalogs, standards, machines)
   - DEMO DATA (minimal stock items + parts for UI testing)

   Production transactional data (operations, batches, work orders) are added via:
   - Manual entry through UI
   - Excel import
   - API integration

   This is CORRECT behavior for development & testing workflow!
```

**Machine Stats:**
```
Lathes: 3
  - NLX2000: 1200 Kč/h (series, bar feeder, 5-axis)
  - CTX450: 1000 Kč/h (single pieces, 4-axis)
  - SPRINT32: 1100 Kč/h (small parts, fast, 4-axis)

Mills: 2
  - DMU50: 1400 Kč/h (5-axis, complex parts)
  - MAZAK510: 900 Kč/h (3-axis, simple parts)
```

### Example Seeded Data (seed_machines.py):

```
Code: NLX2000
  Name: DMG MORI NLX2000
  Type: lathe
  Hourly Rate Breakdown (ADR-016):
    - Amortization: 500.0 Kč/h
    - Labor: 300.0 Kč/h
    - Tools: 200.0 Kč/h
    - Overhead: 200.0 Kč/h
    - TOTAL: 1200.0 Kč/h ✅
  Setup: 30min base + 3min/tool
  Active: True ✅

Code: DMU50
  Name: DMG DMU 50
  Type: mill
  Hourly Rate Breakdown (ADR-016):
    - Amortization: 600.0 Kč/h
    - Labor: 350.0 Kč/h
    - Tools: 250.0 Kč/h
    - Overhead: 200.0 Kč/h
    - TOTAL: 1400.0 Kč/h ✅
  Setup: 40min base + 4min/tool
  Active: True ✅
```

**Validation Checks:**
- ✅ All machines have code, name, type
- ✅ All hourly rates > 0 (ADR-016)
- ✅ Total rates: 900-1400 Kč/h (realistic)
- ✅ No duplicate codes
- ✅ Setup times >= 0

---

## 🎯 Kdy Test Failne?

### Scenario 1: Schema Change (max_length)

```python
# PŘED: Part.part_number = String(7), max_length=7
# ZMĚNA: Part.part_number = String(10), max_length=10

# Seed vytvoří: "1234567" (7 chars) → ✅ PASS
# Validace změněna: max_length=10 → ✅ OK
```

**Result:** Test prochází (relaxace validace je OK).

---

### Scenario 2: Schema Change (tighter validation)

```python
# PŘED: Machine.hourly_rate >= 0
# ZMĚNA: Machine.hourly_rate > 0

# Seed vytvoří: hourly_rate=0 → ❌ FAIL!
```

**Result:** Test failne → musíš opravit seed data.

**Fix:**
```python
# scripts/seed_machines.py
"hourly_rate_amortization": 0.0,  # ❌ ŠPATNĚ (violates new validation)
"hourly_rate_amortization": 500.0, # ✅ SPRÁVNĚ
```

---

### Scenario 3: Seed Data Violate ADR

```python
# ADR-017: part_number MUST be 1XXXXXX (7 digits)
# Seed vytvoří: "DEMO-003" (8 chars, obsahuje písmena)

# Test failne:
# AssertionError: part_number 'DEMO-003' must be 7 digits!
```

**Fix:**
```python
# scripts/seed_complete_part.py
# ❌ ŠPATNĚ
part_number = "DEMO-003"

# ✅ SPRÁVNĚ
from app.services.number_generator import NumberGenerator
part_number = await NumberGenerator.generate_part_number()  # → "1234567"
```

---

## 🚨 Red Flags (kdy spustit testy)

Vždy když:
- ✅ Změníš Pydantic Field validaci (`max_length`, `gt`, `ge`)
- ✅ Změníš DB Column definition (`String(7)` → `String(10)`)
- ✅ Přidáš nové required field
- ✅ Vytvoříš nový seed script
- ✅ Upravuješ existující seed data
- ✅ Před mergem PR do main

**Rule of thumb:** Pokud se dotýkáš models/ nebo schemas/ → spusť seed testy!

---

## 📈 Budoucí Vylepšení

### Phase 2 (Completed 2026-01-28):
- [x] Create `seed_material_items.py` s session parameter
- [x] Create `seed_demo_parts.py` s session parameter
- [x] Add tests for seed_material_items.py
- [x] Add tests for seed_demo_parts.py
- [x] Update gestima.py seed-demo workflow

### Phase 3 (Optional):
- [ ] Update `seed_material_catalog.py` s session parameter
- [ ] Update `seed_material_norms_complete.py` s session parameter
- [ ] Přidat Pydantic Response validation do testů

### Phase 3 (Nice to have):
- [ ] Performance benchmark (seed should complete in <10s)
- [ ] Seed data fixtures (pytest fixtures pro reusable test data)
- [ ] Schema migration tests (test Alembic migrations s seed data)

---

## 🔗 Reference

- **Test soubor:** [tests/test_seed_scripts.py](../tests/test_seed_scripts.py)
- **Příklad implementace:** [scripts/seed_machines.py](../scripts/seed_machines.py)
- **Anti-pattern L-015:** [CLAUDE.md](../CLAUDE.md#l-015-changing-validation-to-fit-bad-data-critical)
- **ADR-017:** [docs/ADR/017-7digit-random-numbering.md](ADR/017-7digit-random-numbering.md)

---

## 💡 Roy's Tips

> "Have you tried turning it off and on again?"
> = Hard refresh (pytest cache): `pytest --cache-clear`

> "This is going to be a long day..."
> = >3 seed test failures → problém je v schema změně, NE v seedech!

> "Did you read the FIRST error?"
> = První failing test v pytest výstupu = root cause. Ostatní jsou následné.

---

## 📞 Troubleshooting

### Problem: Test failne po schema změně

**Symptoms:**
```
AssertionError: Machine NLX2000 has invalid hourly rate: 0
```

**Solution:**
1. READ: Co test říká (která validace failne)
2. CHECK: docs/ADR/ - je to správná validace?
3. FIX: Seed data aby odpovídala validaci
4. DO NOT: Change validation to fit bad data (L-015!)

---

### Problem: Seed script funguje standalone, ale test failne

**Symptoms:**
```
# Standalone OK:
python3 scripts/seed_machines.py  # ✅ Works

# Test FAILS:
pytest tests/test_seed_scripts.py  # ❌ AssertionError
```

**Možné příčiny:**
1. Test používá jinou DB (test DB vs produkční)
2. Seed script nemá `session` parameter → použij subprocess test
3. Test má chybu v assertions

**Solution:**
```bash
# Debug test DB:
pytest tests/test_seed_scripts.py -v -s  # Show print() output

# Zkontroluj že test používá db_session fixture
```

---

### Problem: Integration test (seed-demo) trvá moc dlouho

**Symptoms:**
```
tests/test_seed_scripts.py::test_seed_demo_command_succeeds ... 120s ... TIMEOUT
```

**Solution:**
```python
# Zvýšit timeout v testu:
result = subprocess.run(
    [...],
    timeout=300  # 5 minut místo 120s
)
```

**Nebo skip slow tests:**
```bash
pytest tests/test_seed_scripts.py -v -m "not slow"
```

---

## 📝 Checklist pro Nový Seed Script

Když vytváříš nový seed script:

- [ ] Přidej `session=None` parameter do seed funkce
- [ ] Implementuj session management (own_session pattern)
- [ ] Kontrola existence (idempotent)
- [ ] Return count (pro test assertions)
- [ ] Vytvoř test v `tests/test_seed_scripts.py`
- [ ] Validace required fields
- [ ] Validace business rules (ADRs)
- [ ] Check duplicates
- [ ] Update tento dokument (Coverage tabulka)
- [ ] Run: `pytest tests/test_seed_scripts.py -v`

---

**Poslední update:** 2026-01-28
**Spravuje:** Roy (IT Crowd Rules)
**"Have you tried turning it off and on again?"** 🔄
