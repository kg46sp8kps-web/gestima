# ADR-021: WorkCenter Model Design

**Status:** ✅ Implemented
**Date:** 2026-01-28
**Version:** 1.6.0
**Decision Makers:** Development Team, Product Owner
**Related:** ADR-017 (8-digit numbering), VISION.md (MES v4.0)
**Implementation Date:** 2026-01-28

---

## Context

GESTIMA potřebuje evidenci pracovišť (strojů a pracovních stanic) jako základ pro:

1. **TPV (Technologický Postup Výroby)** - přiřazení operací k pracovištím
2. **Kalkulace** - hodinové sazby pro výpočet cen
3. **MES (v4.0)** - real-time tracking, kapacitní plánování

### Fyzická pracoviště (input od uživatele)

**CNC Soustruhy:**
- MASTURN 32
- SMARTURN 160
- NLX 2000
- NZX 2000

**CNC Frézky:**
- FV20 (klasická fréza, 3-axis)
- MCV 750 (3-axis)
- TAJMAC H40 (4-axis horizontal)
- MILLTAP 700 + WH3 (3-axis)
- MILLTAP 700 5AX + WH3 (5-axis)
- MILLTAP 700 5AX (5-axis)

**Pily:**
- BOMAR STG240A
- BOMAR STG250

**Ostatní:**
- KONTROLA (quality control)
- VS20 (vrtačka/drill)
- MECHANIK (manuální montáž)
- KOOPERACE (external/outsourcing)

---

## Decision

### Single Model: WorkCenter

**Rozhodnutí:** Použít **jeden model `WorkCenter`** místo separace Machine + WorkCenter.

**Důvod:**
- GESTIMA je in-house (1 firma)
- 1 stroj = 1 pracoviště (1:1 mapping)
- Virtuální pracoviště (KONTROLA, KOOPERACE) nepotřebují "machine master data"
- KISS principle - jednodušší model, jednodušší údržba

**VISION.md alignment:**
```
Machine (v1.4) = master data (cost, capabilities)
WorkCenter (v4.0) = Machine + calendar + real-time status
```
→ V GESTIMA context: WorkCenter OBSAHUJE machine data (není potřeba separace)

### Model Structure

```python
class WorkCenter(Base, AuditMixin):
    """Pracoviště - fyzický stroj nebo virtuální pracovní stanice

    Single model approach - Machine data merged into WorkCenter (2026-01-28).
    """
    __tablename__ = "work_centers"

    id = Column(Integer, primary_key=True, index=True)

    # Identification (ADR-017 v2.0: 8-digit, prefix 80, SEQUENTIAL)
    work_center_number = Column(String(8), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)

    # Type classification
    work_center_type = Column(SQLEnum(WorkCenterType), nullable=False)
    subtype = Column(String(50), nullable=True)  # horizontal, vertical

    # Economics (pro TPV kalkulace)
    hourly_rate_amortization = Column(Float, nullable=True)  # Odpisy stroje (Kč/h)
    hourly_rate_labor = Column(Float, nullable=True)         # Mzda operátora (Kč/h)
    hourly_rate_tools = Column(Float, nullable=True)         # Nástroje (Kč/h)
    hourly_rate_overhead = Column(Float, nullable=True)      # Provozní režie (Kč/h)

    # Tech specs (optional - pro constraint checking)
    max_workpiece_diameter = Column(Float, nullable=True)   # mm
    max_workpiece_length = Column(Float, nullable=True)     # mm
    min_workpiece_diameter = Column(Float, nullable=True)   # mm (merged from Machine)
    axes = Column(Integer, nullable=True)                   # 3, 4, 5

    # Bar feeder / Saw specs (merged from Machine)
    max_bar_diameter = Column(Float, nullable=True)         # mm
    max_cut_diameter = Column(Float, nullable=True)         # mm
    bar_feed_max_length = Column(Float, nullable=True)      # mm

    # Capabilities (merged from Machine)
    has_bar_feeder = Column(Boolean, default=False)
    has_sub_spindle = Column(Boolean, default=False)
    has_milling = Column(Boolean, default=False)            # Live tooling
    max_milling_tools = Column(Integer, nullable=True)

    # Production suitability (merged from Machine)
    suitable_for_series = Column(Boolean, default=True)
    suitable_for_single = Column(Boolean, default=True)

    # Setup times (merged from Machine)
    setup_base_min = Column(Float, default=30.0)            # Základní seřízení (min)
    setup_per_tool_min = Column(Float, default=3.0)         # Seřízení na nástroj (min)

    # Organization
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=99)
    notes = Column(Text, nullable=True)

    # Computed properties
    @property
    def hourly_rate_setup(self) -> float | None:
        """Seřizovací sazba (BEZ nástrojů) - používá se při tp"""
        rates = [self.hourly_rate_amortization, self.hourly_rate_labor, self.hourly_rate_overhead]
        return sum(rates) if all(r is not None for r in rates) else None

    @property
    def hourly_rate_operation(self) -> float | None:
        """Výrobní sazba (S nástroji) - používá se při tj"""
        rates = [self.hourly_rate_amortization, self.hourly_rate_labor,
                 self.hourly_rate_tools, self.hourly_rate_overhead]
        return sum(rates) if all(r is not None for r in rates) else None

    @property
    def hourly_rate_total(self) -> float | None:
        """Celková hodinová sazba (alias pro hourly_rate_operation)"""
        return self.hourly_rate_operation
```

### WorkCenterType Enum

```python
class WorkCenterType(str, Enum):
    """Typy pracovišť"""

    # CNC Soustruhy
    CNC_LATHE = "CNC_LATHE"

    # CNC Frézky
    CNC_MILL_3AX = "CNC_MILL_3AX"    # 3-axis
    CNC_MILL_4AX = "CNC_MILL_4AX"    # 4-axis (TAJMAC H40!)
    CNC_MILL_5AX = "CNC_MILL_5AX"    # 5-axis

    # Ostatní stroje
    SAW = "SAW"                      # Pily
    DRILL = "DRILL"                  # Vrtačky

    # Virtuální pracoviště
    QUALITY_CONTROL = "QUALITY_CONTROL"   # Kontrola
    MANUAL_ASSEMBLY = "MANUAL_ASSEMBLY"   # Mechanik/montáž
    EXTERNAL = "EXTERNAL"                  # Kooperace
```

### Number Generation

**Sequential** (ne random) - viz ADR-017 v2.0:
- WorkCenters jsou málo (typicky <100)
- Sequential je snazší pro operátory ("stroj 3")
- Žádný security concern (interní)

```python
# Prefix 80, sequential
80000001 = MASTURN 32
80000002 = SMARTURN 160
80000003 = NLX 2000
...
80000016 = KOOPERACE
```

---

## Seed Data

```python
WORK_CENTERS = [
    # CNC Soustruhy
    {"number": "80000001", "name": "MASTURN 32", "type": "CNC_LATHE"},
    {"number": "80000002", "name": "SMARTURN 160", "type": "CNC_LATHE"},
    {"number": "80000003", "name": "NLX 2000", "type": "CNC_LATHE"},
    {"number": "80000004", "name": "NZX 2000", "type": "CNC_LATHE"},

    # CNC Frézky
    {"number": "80000005", "name": "FV20 (klasická fréza)", "type": "CNC_MILL_3AX"},
    {"number": "80000006", "name": "MCV 750", "type": "CNC_MILL_3AX"},
    {"number": "80000007", "name": "TAJMAC H40", "type": "CNC_MILL_4AX"},
    {"number": "80000008", "name": "MILLTAP 700 + WH3", "type": "CNC_MILL_3AX"},
    {"number": "80000009", "name": "MILLTAP 700 5AX + WH3", "type": "CNC_MILL_5AX"},
    {"number": "80000010", "name": "MILLTAP 700 5AX", "type": "CNC_MILL_5AX"},

    # Pily
    {"number": "80000011", "name": "BOMAR STG240A", "type": "SAW"},
    {"number": "80000012", "name": "BOMAR STG250", "type": "SAW"},

    # Ostatní
    {"number": "80000013", "name": "KONTROLA", "type": "QUALITY_CONTROL"},
    {"number": "80000014", "name": "VS20 (vrtačka)", "type": "DRILL"},
    {"number": "80000015", "name": "MECHANIK", "type": "MANUAL_ASSEMBLY"},
    {"number": "80000016", "name": "KOOPERACE", "type": "EXTERNAL"},
]
```

---

## API Endpoints

```python
# app/routers/work_centers.py

GET  /api/work-centers              # List all (filter by type, active)
POST /api/work-centers              # Create new
GET  /api/work-centers/{number}     # Get by work_center_number
PUT  /api/work-centers/{number}     # Update
DELETE /api/work-centers/{number}   # Soft delete
```

---

## Future Extensions (MES v4.0)

Pole která přidáme v MES modulu (v4.0):

```python
# Calendar integration
calendar_id = Column(Integer, ForeignKey("calendars.id"), nullable=True)

# Real-time status (NOTE: Consider Redis cache instead of DB!)
# current_status = Column(String(20))  # "idle", "busy", "down", "maintenance"
# current_operator_id = Column(Integer, ForeignKey("users.id"))
# current_work_order_id = Column(Integer, ForeignKey("work_orders.id"))
```

**IMPORTANT (VISION.md VIS-004):** Real-time status by měl být v Redis/cache, NE v DB (high write frequency).

---

## Considered Alternatives

### Alternative 1: Separate Machine + WorkCenter models

```python
class Machine:
    # Tech specs, capabilities
    max_diameter, axes, spindle_power, ...

class WorkCenter:
    machine_id = ForeignKey("machines.id")  # Optional
    # Calendar, status, ...
```

**Pros:**
- Clean separation (master data vs runtime)
- Aligned with VISION.md wording

**Cons:**
- Over-engineering for GESTIMA context (in-house, 1:1 mapping)
- Extra complexity (2 models, 2 APIs, JOIN queries)
- Virtual work centers (KONTROLA) don't have machine

**Verdict:** Rejected - KISS principle

### Alternative 2: Extend existing Machine model

**Pros:**
- No new model needed
- Reuse existing code

**Cons:**
- Machine model has too many tech fields (bar_feeder, sub_spindle, ...)
- Not all work centers are machines (KONTROLA, KOOPERACE)
- Semantic mismatch (Machine ≠ WorkCenter)

**Verdict:** Rejected - semantic confusion

---

## Trade-offs

| Aspect | Single WorkCenter | Machine + WorkCenter |
|--------|-------------------|----------------------|
| **Simplicity** | ✅ 1 model | ❌ 2 models |
| **Queries** | ✅ No JOINs | ❌ JOIN needed |
| **Virtual WCs** | ✅ Native support | ⚠️ Nullable FK |
| **Tech specs** | ⚠️ Optional fields | ✅ Separate model |
| **MES extension** | ✅ Add fields | ✅ Add fields |
| **VISION alignment** | ⚠️ Combined | ✅ Separated |

**Verdict:** Single model wins for GESTIMA context.

---

## Consequences

### Positive

1. ✅ **Simple model** - 1 table, 1 API, no JOINs
2. ✅ **Virtual WCs supported** - KONTROLA, KOOPERACE native
3. ✅ **Hourly rates integrated** - TPV kalkulace ready
4. ✅ **Extensible** - MES fields can be added later
5. ✅ **Sequential numbers** - Easy for operators (80000001, 80000002, ...)

### Negative

1. ⚠️ **Optional tech specs** - Some fields always NULL for virtual WCs
   - Mitigation: UI hides irrelevant fields based on type
2. ⚠️ **Combined concerns** - Master data + runtime in one model
   - Mitigation: Clear field naming, status in Redis (v4.0)

---

## Implementation Checklist

### v1.6.0 (✅ Completed 2026-01-28)

- [x] Create `app/models/work_center.py` (with merged Machine fields)
- [x] Add WorkCenterType to `app/models/enums.py`
- [x] Create Pydantic schemas (Create, Update, Response)
- [x] Create `app/routers/work_centers_router.py`
- [x] Create Alembic migration (`c5e8f2a1b3d4` + `d6a7b8c9e0f1`)
- [x] Create `scripts/seed_work_centers.py`
- [x] Add WorkCenters tab to `app/templates/admin/master_data.html`
- [x] Create `tests/test_work_centers.py`
- [ ] Update CHANGELOG.md
- [ ] Deprecate Machine model (future cleanup)

---

## References

- ADR-017: 8-digit numbering (prefix 80 for WorkCenters)
- VISION.md: MES module (v4.0) - Work Centers + real-time tracking
- CLAUDE.md: KISS principle, single source of truth

---

**Decision Date:** 2026-01-28
**Approved By:** Development Team
**Implementation:** v1.6.0
**Status:** ✅ Implemented (2026-01-28)

---

## Implementation Notes

### Machine Model Merge (2026-01-28)

During implementation, decided to merge Machine model fields into WorkCenter:
- **has_bar_feeder**, **has_sub_spindle**, **has_milling** - capabilities
- **max_bar_diameter**, **max_cut_diameter**, **bar_feed_max_length** - bar feeder/saw specs
- **suitable_for_series**, **suitable_for_single** - production suitability
- **setup_base_min**, **setup_per_tool_min** - setup times

Machine model kept as deprecated (too many dependencies for immediate removal).

### UI Integration

WorkCenters tab added to `master_data.html` (formerly `material_norms.html`) - central admin page for master data management.
