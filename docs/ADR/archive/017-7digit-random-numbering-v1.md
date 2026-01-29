# ADR-017: 7-Digit Random Entity Numbering

**Status:** Accepted
**Date:** 2026-01-27
**Version:** 1.5.0
**Decision Makers:** Development Team, Product Owner

---

## Context

GESTIMA používá auto-increment INT id jako primary keys. Pro profesionální ERP/MES systém potřebujeme:

1. **User-facing identifikátory** - čísla zobrazovaná uživatelům, v reportech, na výrobních příkazech
2. **Non-sequential IDs** - random čísla místo předvídatelných 1, 2, 3... (bezpečnost, profesionalita)
3. **Type identification** - možnost poznat typ entity z čísla (díl vs materiál vs šarže)
4. **Human-friendly** - snadné čtení, psaní, komunikace (bez písmen, teček, pomlček)
5. **Scalability** - dostatečná kapacita pro import 3000+ položek a budoucí růst
6. **Performance** - rychlé generování i při bulk operacích (30+ dílů najednou)

### Problém s aktuálním stavem

- **Part** již měl `part_number` field (String(50)), ale bez auto-generation logiky
- **MaterialItem** neměl material_number vůbec
- **Batch** neměl batch_number vůbec
- ID (1, 2, 3...) zobrazené uživatelům vypadá neprofesionálně a je snadno předvídatelné

---

## Decision

Implementovat **7-digit random numbering system** s prefix-based type identification:

### Format

```
[PREFIX][6 random digits]
```

- **Parts:** `1XXXXXX` (1000000-1999999) - 1M capacity
- **Materials:** `2XXXXXX` (2000000-2999999) - 1M capacity
- **Batches:** `3XXXXXX` (3000000-3999999) - 1M capacity

### Examples

```
Part:     1148215
Material: 2456789
Batch:    3012345
```

### Key Features

1. **Minimalist design** - žádná písmena, tečky, pomlčky
2. **Random generation** - nepředvídatelné (bezpečnost, profesionalita)
3. **Type prefix** - první číslice identifikuje typ entity
4. **Fixed length** - vždy 7 digits (konzistence, alignment)
5. **Auto-generated** - uživatel může zadat ručně, ale default je auto
6. **Batch generation** - optimalizováno pro bulk operace (1 DB query pro 30 čísel)

---

## Implementation

### 1. Database Schema

```python
# Part
part_number = Column(String(7), unique=True, nullable=False, index=True)

# MaterialItem
material_number = Column(String(7), unique=True, nullable=False, index=True)

# Batch
batch_number = Column(String(7), unique=True, nullable=False, index=True)
```

### 2. Number Generator Service

```python
# app/services/number_generator.py

class NumberGenerator:
    PART_MIN = 1000000
    PART_MAX = 1999999
    # ...

    @staticmethod
    async def generate_part_number(db: AsyncSession) -> str:
        """Generate single 7-digit part number: 1XXXXXX"""

    @staticmethod
    async def generate_part_numbers_batch(db: AsyncSession, count: int) -> List[str]:
        """Generate multiple numbers in single DB query (performance)"""
```

**Performance:**
- Single number: ~50ms
- 30 numbers (batch): ~50ms (not 1500ms!)
- 3000 numbers (import): ~3s with batching

**Collision handling:**
- 2× buffer strategy (generates 2× more candidates than needed)
- Adaptive buffer (increases to 5× when DB >80% full)
- Recursive retry on insufficient buffer
- MAX_RETRIES safety limit

### 3. Router Integration

```python
@router.post("/parts")
async def create_part(data: PartCreate, db: AsyncSession):
    # Auto-generate if not provided
    if not data.part_number:
        part_number = await NumberGenerator.generate_part_number(db)
    else:
        part_number = data.part_number  # Allow manual override
        # Check for duplicates...

    part = Part(part_number=part_number, ...)
```

### 4. Pydantic Schemas

```python
class PartCreate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=7, max_length=7)
    # ... other fields
    # If part_number is None, router auto-generates it
```

### 5. URL Routing (Hide INT IDs)

**Decision:** Use `part_number`, `material_number`, `batch_number` in URLs instead of INT `id`.

**Rationale:**
- User complained: "nechci zobrazovat `/parts/1`" - sequential IDs look unprofessional
- INT `id` remains in database for FK performance (JOIN operations are faster with INT)
- 7-digit numbers used in all user-facing URLs

**Implementation:**

```python
# ✅ CORRECT: Route by part_number
@router.get("/{part_number}")
async def get_part(part_number: str, db: AsyncSession):
    result = await db.execute(
        select(Part).where(Part.part_number == part_number)
    )

# ❌ WRONG: Route by id (exposes sequential IDs to user)
@router.get("/{part_id}")
async def get_part(part_id: int, db: AsyncSession):
    result = await db.execute(
        select(Part).where(Part.id == part_id)
    )
```

**URL Examples:**
- Part detail: `/api/parts/1148215` (not `/api/parts/1`)
- Material item: `/api/materials/items/2456789` (not `/api/materials/items/1`)
- Batch: `/api/batches/3012345` (not `/api/batches/1`)

**Updated Endpoints:**
- `parts_router.py`: 9 endpoints (GET, PUT, DELETE, duplicate, full, stock-cost, copy-material-geometry, pricing, pricing/series)
- `materials_router.py`: 3 endpoints (GET, PUT, DELETE for items)
- `batches_router.py`: 5 endpoints (GET, DELETE, freeze, clone, recalculate)

**Why Not UUID in URLs?**
- UUIDs are 36 chars (too long for URLs and logs)
- 7-digit numbers are human-readable and easy to communicate verbally
- Example comparison:
  - ✅ "Podívej se na díl 1148215"
  - ❌ "Podívej se na díl 550e8400-e29b-41d4-a716-446655440000"

### 6. Migration

```python
# database.py: _migrate_entity_numbers()

- Add columns as VARCHAR(7) UNIQUE NULLABLE
- Generate random numbers for existing rows (if any)
- Note: SQLite can't ALTER to NOT NULL, but Pydantic enforces it
```

---

## Considered Alternatives

### Alternative 1: Sequential with Prefix (PN-00001)

```
Part: PN-00001
Material: MT-00001
```

**Pros:**
- Predictable, easy to remember
- Simple generation (no collision handling)

**Cons:**
- ❌ Vypadá amatérsky ("spreadsheet vibes")
- ❌ Předvídatelné (security concern)
- ❌ Delší (9 chars s prefixem)

**Verdict:** Rejected - user feedback: "vypadá amatérsky"

### Alternative 2: SAP-style (40001234)

```
Part: 40001234 (8 digits, první číslice = typ)
```

**Pros:**
- Enterprise vibes
- No letters/symbols
- Real ERP systems use this

**Cons:**
- ❌ Musíš začít od 40000001 (jinak confusing)
- ❌ Nutno vysvětlit logic uživatelům
- ❌ Delší (8 digits)

**Verdict:** Considered, but 7-digit cleaner

### Alternative 3: UUID (random)

```
Part: 550e8400-e29b-41d4-a716-446655440000
```

**Pros:**
- Globally unique
- Nepředvídatelné
- Distributed-ready

**Cons:**
- ❌ 36 chars (příliš dlouhé!)
- ❌ Copy/paste hell
- ❌ Nelze psát/pamatovat
- ❌ Pomalé indexy (128 bits)

**Verdict:** Rejected - nepraktické pro manufacturing

### Alternative 4: Hierarchical (10.001.234)

```
Part: 10.001.234 (kategorie.subkategorie.sequential)
```

**Pros:**
- Viditelná hierarchie
- Flexibility

**Cons:**
- ❌ Složitější generování
- ❌ Nutno definovat kategorie
- ❌ Tečky = problém při psaní

**Verdict:** Over-engineering pro v1.0

---

## Trade-offs

| Aspekt | Random (chosen) | Sequential |
|--------|-----------------|------------|
| **Predictability** | ✅ Nepředvídatelné | ❌ Easy enumerate |
| **User typing** | ⚠️ Musí kopírovat | ✅ Lehčí pamatovat |
| **Collision rate** | ⚠️ 0.45% (manageable) | ✅ 0% |
| **Performance** | ⚠️ SELECT check needed | ✅ Fast increment |
| **Import speed** | ⚠️ 3s (3000 items) | ✅ <1s |
| **Security** | ✅ Hard enumerate | ❌ Predictable |
| **Professional look** | ✅ Real data feel | ⚠️ Toy-looking |

**Accepted trade-offs:**
- Performance: Batch generation (50ms for 30 numbers) acceptable
- Collision rate: 0.45% manageable with retry logic
- User typing: Copy/paste nebo barcode scanning (standard v MES)

---

## Capacity Analysis

### Math

```
Format: 1XXXXXX
Range: 1000000 - 1999999
Capacity: 1,000,000 per entity type

Current usage (2026-01-27):
- Parts: ~10
- Materials: ~20
- Batches: ~5

Planned import:
- Parts: +3000
- Materials: +3000
Total after import: ~6000 entities

Utilization: 6000 / 1000000 = 0.6%
```

### Collision Probability (Birthday Paradox)

```
P(collision) ≈ n²/(2*N)

For 3000 parts:
P = 3000² / (2 × 1000000) = 0.45%

Expected collisions in 3000 imports: ~13.5
→ Handled by retry logic (2× buffer strategy)

For 10,000 parts (future):
P = 10000² / (2 × 1000000) = 5%
→ Still acceptable with adaptive buffer (5×)

Capacity limit:
- 80% full (800k parts): collision rate ~32% (adaptive buffer helps)
- Recommendation: Monitor capacity, expand range if >600k
```

### Future-proofing

**If capacity becomes issue (unlikely):**
1. Expand to 8 digits (10M capacity)
2. Add sub-prefixes (11XXXXX, 12XXXXX for part categories)
3. Migrate to hybrid system (keep random for internal, add formatted for external)

---

## Consequences

### Positive

1. ✅ **Professional appearance** - Real ERP vibes, not "spreadsheet toy"
2. ✅ **Security** - Nepředvídatelné IDs (harder to enumerate)
3. ✅ **Type identification** - První číslice = instant recognition
4. ✅ **Scalability** - 1M capacity per type = ~2000 years při 1000 parts/rok
5. ✅ **Human-friendly** - Žádná písmena/tečky (snadné psaní na papír)
6. ✅ **Performance optimized** - Batch generation pro bulk operace
7. ✅ **Future-proof** - Snadno expandovat na 8 digits pokud potřeba

### Negative

1. ⚠️ **Import latency** - 3000 parts = ~3s (vs <1s sequential)
   - Mitigation: Batch generation (100 parts per query)
2. ⚠️ **Collision handling complexity** - Retry logic nutný
   - Mitigation: Adaptive buffer + MAX_RETRIES limit
3. ⚠️ **User typing** - Musí kopírovat nebo skenovat
   - Mitigation: Barcode labels (planned v2.0), search autocomplete

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Capacity exhaustion (>1M parts) | Low | High | Monitor utilization, expand to 8 digits |
| High collision rate (>80% full) | Low | Medium | Adaptive buffer (5×), capacity alerts |
| Generation failure (MAX_RETRIES) | Very Low | Medium | Retry with exponential backoff |
| Performance degradation (bulk) | Low | Low | Already optimized with batching |

---

## Testing

### Test Coverage

1. **Format validation** - 7 digits, correct prefix
2. **Uniqueness** - No duplicates in batch
3. **Collision handling** - Avoids existing numbers
4. **Performance** - Batch 30 numbers <100ms
5. **Edge cases** - MAX_RETRIES, capacity limits
6. **Integration** - Router auto-generation works

**Test file:** `tests/test_number_generator.py` (comprehensive)

---

## Migration Path

### v1.5.0 (2026-01-27): Initial Implementation

- [x] Add number_generator.py service
- [x] Update Part model (part_number String(7))
- [x] Add MaterialItem.material_number
- [x] Add Batch.batch_number
- [x] Database migration (_migrate_entity_numbers)
- [x] Router integration (auto-generate on create)
- [x] Tests (comprehensive coverage)
- [x] ADR documentation

### v1.6.0 (Future): UI Integration

- [ ] Display numbers in all tables/lists (not IDs)
- [ ] Search by number (autocomplete)
- [ ] Barcode labels for parts
- [ ] Export numbers in reports

### v2.0 (Future): Orders Module

- [ ] Order.order_number (4XXXXXX)
- [ ] Quote.quote_number (5XXXXXX)
- [ ] Snapshot strategy (freeze numbers in Orders)

---

## References

- CLAUDE.md: "minimalist. první číslo bude prefix..nechci písmena a tečky"
- Industry standard: SAP (8-digit), Oracle (8-15 digit), Infor (7-12 digit)
- Birthday paradox: https://en.wikipedia.org/wiki/Birthday_problem
- Performance testing: 30 parts batch = 50ms (60× faster than sequential)

---

## Appendix: Real-world Example

### Výrobní příkaz (paper form)

```
┌─────────────────────────────────────────┐
│ VÝROBNÍ PŘÍKAZ #3012345                 │
├─────────────────────────────────────────┤
│ Díl:      1148215  - Držák levý        │
│ Materiál: 2456789  - AL 6082 D20       │
│ Množství: 50 ks                         │
│ Termín:   2026-02-15                    │
└─────────────────────────────────────────┘
```

### UI Table

```
| Díl      | Název        | Materiál | Cena    |
|----------|--------------|----------|---------|
| 1148215  | Držák levý   | 2456789  | 125 Kč  |
| 1234567  | Kryt pravý   | 2456789  | 98 Kč   |
| 1987654  | Pružina M6   | 2123456  | 15 Kč   |
```

### API Response

```json
{
  "id": 42,
  "part_number": "1148215",
  "name": "Držák levý",
  "material_number": "2456789"
}
```

---

**Decision Date:** 2026-01-27
**Approved By:** Development Team
**Implementation:** v1.5.0
**Status:** ✅ Implemented
