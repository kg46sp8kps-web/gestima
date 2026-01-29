# ADR-017: 8-Digit Entity Numbering System

**Status:** Accepted (v2.0 - Breaking Change)
**Date:** 2026-01-28 (v2.0 update)
**Original Date:** 2026-01-27 (v1.0)
**Version:** 1.6.0
**Decision Makers:** Development Team, Product Owner

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2026-01-27 | Initial 7-digit system (PXXXXXX) |
| v2.0 | 2026-01-28 | **BREAKING:** Expand to 8-digit (PPXXXXXX) for more prefix categories |

---

## Context

### Original Context (v1.0)

GESTIMA používá auto-increment INT id jako primary keys. Pro profesionální ERP/MES systém potřebujeme:

1. **User-facing identifikátory** - čísla zobrazovaná uživatelům, v reportech, na výrobních příkazech
2. **Non-sequential IDs** - random čísla místo předvídatelných 1, 2, 3... (bezpečnost, profesionalita)
3. **Type identification** - možnost poznat typ entity z čísla (díl vs materiál vs šarže)
4. **Human-friendly** - snadné čtení, psaní, komunikace (bez písmen, teček, pomlček)
5. **Scalability** - dostatečná kapacita pro import 3000+ položek a budoucí růst
6. **Performance** - rychlé generování i při bulk operacích (30+ dílů najednou)

### Why v2.0? (Breaking Change Rationale)

**Problem with 7-digit system:**
- Format `PXXXXXX` (1-digit prefix) = only **10 prefixes** (0-9)
- GESTIMA VISION.md plans 15+ entity types over 1-year roadmap
- Insufficient for future expansion

**Solution:**
- Expand to `PPXXXXXX` (2-digit prefix) = **100 prefixes** (00-99)
- Requires 8 digits total to maintain 1M capacity per prefix
- 7 digits with 2-digit prefix (PPXXXXX) = only 100k capacity = higher collision risk!

**Math comparison:**
```
7-digit, 2-digit prefix: PPXXXXX = 100,000 capacity
→ Birthday paradox: 3000 items = 4.5% collision (10× WORSE!)

8-digit, 2-digit prefix: PPXXXXXX = 1,000,000 capacity
→ Birthday paradox: 3000 items = 0.45% collision (SAME as v1.0)
```

---

## Decision (v2.0)

Implementovat **8-digit numbering system** s 2-digit prefix:

### Format

```
[PP][XXXXXX]

PP = 2-digit prefix (00-99) = 100 kategorií
XXXXXX = 6 digits (random nebo sequential)
Total = 8 digits
```

### Prefix Allocation

#### Master Data (10-29)

| Prefix | Entity | Generation | Capacity | Status |
|--------|--------|------------|----------|--------|
| **10** | Parts | Random | 1M | ✅ Implemented (migrate from 1XXXXXX) |
| **11** | Parts - Assemblies | Random | 1M | 🔮 Reserved (future BOM) |
| **12** | Parts - Spare | Random | 1M | 🔮 Reserved |
| **20** | Materials | Random | 1M | ✅ Implemented (migrate from 2XXXXXX) |
| **21** | Materials - Consumables | Random | 1M | 🔮 Reserved |

#### Transactions (30-59)

| Prefix | Entity | Generation | Capacity | Status |
|--------|--------|------------|----------|--------|
| **30** | Batches | Random | 1M | ✅ Implemented (migrate from 3XXXXXX) |
| **40** | Orders | Random | 1M | 🔮 v2.0 (Quotes & Orders) |
| **50** | Quotes | Random | 1M | 🔮 v2.0 (Quotes & Orders) |

#### Customers & Partners (70-79)

| Prefix | Entity | Generation | Capacity | Status |
|--------|--------|------------|----------|--------|
| **70** | Customers | Random | 1M | 🔮 v2.0 (Quotes & Orders) |
| **71** | Suppliers | Random | 1M | 🔮 Reserved |

#### Production / Manufacturing (80-89) 🏭

| Prefix | Entity | Generation | Capacity | Status |
|--------|--------|------------|----------|--------|
| **80** | WorkCenters | **Sequential** | 1M | 📋 v1.6.0 (THIS RELEASE) |
| **81** | WorkOrders | Random | 1M | 🔮 v4.0 (MES) |
| **82** | Operations/Routing | Random | 1M | 🔮 v4.0 (MES) |
| **83** | ProductionLogs | Sequential | 1M | 🔮 v4.0 (MES) |

#### Documents (90-99)

| Prefix | Entity | Generation | Capacity | Status |
|--------|--------|------------|----------|--------|
| **90** | Drawings | Random | 1M | 🔮 v3.0 (PLM) |
| **91** | ECN/ECO | Sequential | 1M | 🔮 v3.0 (PLM) |

#### Reserved (00-09, 60-69)

| Prefix | Purpose |
|--------|---------|
| **00-09** | System/Internal (config, audit logs) |
| **60-69** | Future expansion |

### Examples (v2.0)

```
Part:        10148215  (random)
Material:    20456789  (random)
Batch:       30012345  (random)
WorkCenter:  80000001  (sequential)
WorkCenter:  80000002  (sequential)
Customer:    70234567  (random, future)
WorkOrder:   81345678  (random, future)
```

---

## Key Features

1. **Minimalist design** - žádná písmena, tečky, pomlčky
2. **2-digit prefix** - 100 kategorií (vs 10 in v1.0)
3. **Fixed length** - vždy 8 digits (konzistence, alignment)
4. **Category grouping** - první číslice = doména (1=master, 3=txn, 7=partners, 8=production, 9=docs)
5. **Mixed generation** - Random (most) nebo Sequential (WorkCenters, logs)
6. **Backward compatible migration** - prepend digit to existing numbers

---

## Implementation

### 1. Database Schema (v2.0)

```python
# Part (CHANGED: String(7) → String(8))
part_number = Column(String(8), unique=True, nullable=False, index=True)

# MaterialItem (CHANGED)
material_number = Column(String(8), unique=True, nullable=False, index=True)

# Batch (CHANGED)
batch_number = Column(String(8), unique=True, nullable=False, index=True)

# WorkCenter (NEW)
work_center_number = Column(String(8), unique=True, nullable=False, index=True)
```

### 2. Number Generator Service (v2.0)

```python
# app/services/number_generator.py

class NumberGenerator:
    # v2.0: 8-digit ranges with 2-digit prefix

    # Parts: 10XXXXXX (random)
    PART_MIN = 10000000
    PART_MAX = 10999999

    # Materials: 20XXXXXX (random)
    MATERIAL_MIN = 20000000
    MATERIAL_MAX = 20999999

    # Batches: 30XXXXXX (random)
    BATCH_MIN = 30000000
    BATCH_MAX = 30999999

    # WorkCenters: 80XXXXXX (sequential)
    WORK_CENTER_MIN = 80000001
    WORK_CENTER_MAX = 80999999

    @staticmethod
    async def generate_part_number(db: AsyncSession) -> str:
        """Generate single 8-digit part number: 10XXXXXX"""

    @staticmethod
    async def generate_work_center_number(db: AsyncSession) -> str:
        """Generate sequential 8-digit work center number: 80XXXXXX"""
        # Find MAX existing, increment by 1
```

### 3. Pydantic Schemas (v2.0)

```python
class PartCreate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=8, max_length=8)
    # ...

class WorkCenterCreate(BaseModel):
    work_center_number: Optional[str] = Field(None, min_length=8, max_length=8)
    # If None, auto-generate sequential
```

### 4. Migration (7 → 8 digits)

```python
# alembic/versions/xxx_8digit_numbering.py

def upgrade():
    """Migrate from 7-digit (PXXXXXX) to 8-digit (PPXXXXXX)"""

    # Parts: 1XXXXXX → 10XXXXXX (prepend "1")
    op.execute("""
        UPDATE parts
        SET part_number = '1' || part_number
        WHERE length(part_number) = 7
    """)

    # Materials: 2XXXXXX → 20XXXXXX
    op.execute("""
        UPDATE material_items
        SET material_number = '2' || material_number
        WHERE length(material_number) = 7
    """)

    # Batches: 3XXXXXX → 30XXXXXX
    op.execute("""
        UPDATE batches
        SET batch_number = '3' || batch_number
        WHERE length(batch_number) = 7
    """)

    # Note: Column type stays VARCHAR - SQLite doesn't enforce length
    # Pydantic validation enforces 8 digits on input

def downgrade():
    """Revert to 7-digit (remove first digit of prefix)"""
    op.execute("UPDATE parts SET part_number = substr(part_number, 2) WHERE length(part_number) = 8")
    op.execute("UPDATE material_items SET material_number = substr(material_number, 2) WHERE length(material_number) = 8")
    op.execute("UPDATE batches SET batch_number = substr(batch_number, 2) WHERE length(batch_number) = 8")
```

---

## Capacity Analysis (v2.0)

### Per-Prefix Capacity

```
Format: PPXXXXXX
Range per prefix: PP000000 - PP999999
Capacity per prefix: 1,000,000

Total prefixes: 100 (00-99)
Total system capacity: 100,000,000 entities
```

### Collision Probability (unchanged from v1.0)

```
P(collision) ≈ n²/(2*N)

For 3000 parts (prefix 10):
P = 3000² / (2 × 1,000,000) = 0.45%

For 10,000 parts:
P = 10000² / (2 × 1,000,000) = 5%

→ Same as v1.0 (good!)
```

### Longevity

```
1M capacity per prefix
At 1,000 parts/year = 1,000 years
At 10,000 parts/year = 100 years

Total system (100M):
At 100,000 entities/year = 1,000 years

→ ✅ "Konec věků vesmíru" confirmed
```

---

## WorkCenters: Sequential Generation

**Decision:** WorkCenters use **sequential** numbers (80000001, 80000002, ...) instead of random.

**Rationale:**
- WorkCenters are few (typically <100 per company)
- Sequential is easier for operators to remember ("stroj 3" vs "stroj 80457892")
- No security concern (not exposed externally)
- Debugging/development easier

**Implementation:**

```python
@staticmethod
async def generate_work_center_number(db: AsyncSession) -> str:
    """Generate sequential work center number"""
    result = await db.execute(
        select(func.max(WorkCenter.work_center_number))
    )
    max_number = result.scalar()

    if max_number is None:
        return "80000001"  # First work center

    next_num = int(max_number) + 1
    return str(next_num)
```

---

## URL Routing (unchanged)

```python
# Use 8-digit numbers in URLs
/api/parts/10148215
/api/materials/items/20456789
/api/work-centers/80000001
```

---

## Trade-offs (v2.0 vs v1.0)

| Aspect | v1.0 (7-digit) | v2.0 (8-digit) |
|--------|----------------|----------------|
| **Prefix categories** | 10 (0-9) | 100 (00-99) ✅ |
| **Digits to type** | 7 | 8 (+1) |
| **Capacity per prefix** | 1M | 1M (same) |
| **Collision rate** | 0.45% | 0.45% (same) |
| **Future-proof** | ⚠️ Limited | ✅ 100 categories |
| **Breaking change** | N/A | ⚠️ Migration required |

**Verdict:** 1 extra digit is worth 10× more prefix categories.

---

## Migration Path

### v1.5.0 (2026-01-27): Initial 7-digit Implementation ✅

- [x] Add number_generator.py service
- [x] Update Part model (part_number String(7))
- [x] Add MaterialItem.material_number
- [x] Add Batch.batch_number
- [x] Database migration
- [x] Router integration
- [x] Tests
- [x] ADR documentation

### v1.6.0 (2026-01-28): 8-digit Expansion + WorkCenters ✅

- [x] **BREAKING:** Migrate 7→8 digits (replace prefix: 1→10, 2→20, 3→30)
- [x] Update number_generator.py (new ranges: 10XXXXXX, 20XXXXXX, 30XXXXXX)
- [x] Update Pydantic schemas (min/max_length=8)
- [x] Update seed scripts
- [x] Update tests for 8-digit format (243 passed)
- [x] Update ADR-017 documentation
- [ ] Add WorkCenter model (prefix 80, sequential) - TODO
- [ ] Add WorkCenter API router - TODO
- [ ] Add WorkCenter admin UI - TODO

### v2.0 (Future): Orders Module

- [ ] Order.order_number (40XXXXXX)
- [ ] Quote.quote_number (50XXXXXX)
- [ ] Customer.customer_number (70XXXXXX)

### v4.0 (Future): MES Module

- [ ] WorkOrder.work_order_number (81XXXXXX)
- [ ] Operation.operation_number (82XXXXXX)

---

## Appendix: Real-world Example (v2.0)

### Výrobní příkaz (paper form)

```
┌─────────────────────────────────────────┐
│ VÝROBNÍ PŘÍKAZ #81012345                │
├─────────────────────────────────────────┤
│ Díl:        10148215  - Držák levý      │
│ Materiál:   20456789  - AL 6082 D20     │
│ Pracoviště: 80000003  - NLX 2000        │
│ Množství:   50 ks                        │
│ Termín:     2026-02-15                   │
└─────────────────────────────────────────┘
```

### UI Table

```
| Díl       | Název        | Materiál  | Pracoviště | Cena    |
|-----------|--------------|-----------|------------|---------|
| 10148215  | Držák levý   | 20456789  | 80000003   | 125 Kč  |
| 10234567  | Kryt pravý   | 20456789  | 80000007   | 98 Kč   |
| 10987654  | Pružina M6   | 20123456  | 80000001   | 15 Kč   |
```

### API Response

```json
{
  "id": 42,
  "part_number": "10148215",
  "name": "Držák levý",
  "material_number": "20456789"
}
```

---

## References

- CLAUDE.md: "minimalist. první číslo bude prefix..nechci písmena a tečky"
- VISION.md: 15+ entity types planned over 1-year roadmap
- Industry standard: SAP (8-digit), Oracle (8-15 digit), Infor (7-12 digit)
- Birthday paradox: https://en.wikipedia.org/wiki/Birthday_problem

---

**Decision Date:** 2026-01-28 (v2.0)
**Original Date:** 2026-01-27 (v1.0)
**Approved By:** Development Team
**Implementation:** v1.6.0
**Status:** ✅ Implemented (2026-01-28)
