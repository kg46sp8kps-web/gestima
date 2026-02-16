# ADR-045: Feature-Based Deterministic Machining Time Calculation

**Status:** Accepted
**Date:** 2026-02-15
**Author:** Backend Architect
**Version:** 1.0.0

## Context

AI models (GPT-4o fine-tuned) extract machining features from PDF drawings as JSON:

```json
{
  "features": [
    {"type": "outer_diameter", "count": 1, "detail": "ø60 h9", "location": "hlava"},
    {"type": "through_hole", "count": 2, "detail": "ø5.3 mm", "location": "levý roh"},
    {"type": "pocket", "count": 1, "detail": "80×22×3.4mm", "location": "střed"},
    {"type": "chamfer", "count": 3, "detail": "1×45°", "location": "konec"}
  ]
}
```

While AI-generated time estimates are fast and convenient, they lack:
- **Determinism** — Same input may produce different outputs
- **Explainability** — Cannot show detailed breakdown
- **Consistency** — Different models/versions may differ
- **Calibration** — Cannot be tuned against real production data

We need a **deterministic calculation engine** that converts AI-extracted features into precise machining times using cutting conditions from our database.

## Decision

Implement `feature_calculator.py` service with:

### 1. Detail String Parsing

Extract numeric dimensions from AI's free-text "detail" field using regex patterns:

```python
parse_diameter("ø60 h9") → 60.0
parse_diameter("M10×1.5") → 10.0
parse_length("80×22×3.4mm") → 80.0
parse_depth("H=5") → 5.0
parse_thread_pitch("M8") → 1.25 (ISO standard)
```

### 2. Feature Type Mapping

Map AI feature types to database operation lookup:

```python
AI_FEATURE_TO_DB_OPERATION = {
    "outer_diameter": ("turning", "hrubovani"),
    "through_hole": ("drilling", "vrtani"),
    "thread_external": ("threading", "zavitovani"),
    "pocket": ("milling", "frezovani"),
    "chamfer": None,  # Constant time
    "surface_finish": None,  # Informational only
}
```

### 3. Cutting Conditions Lookup

Retrieve Vc, f, Ap from `cutting_conditions_catalog`:

```python
conditions = get_catalog_conditions(
    material_group="20910004",  # 8-digit code
    operation_type="turning",
    operation="hrubovani",
    mode="mid"  # low/mid/high
)
# → {"Vc": 220, "f": 0.25, "Ap": 2.5}
```

### 4. Machining Time Formulas

Standard machining calculations:

```python
# Turning
rpm = (Vc * 1000) / (π × D)
feed_rate = rpm × f
time = (length / feed_rate) × passes

# Drilling
rpm = (Vc * 1000) / (π × D)
feed_rate = rpm × f
time = depth / feed_rate

# Milling
rpm = (Vc * 1000) / (π × tool_D)
feed_rate = rpm × fz × teeth
time = (path / feed_rate) × depth_passes

# Threading
rpm = (Vc * 1000) / (π × D)
feed_rate = rpm × pitch
time = (length / feed_rate) × 5_passes
```

### 5. Robust Error Handling

- **Per-feature try/except** — One bad feature doesn't kill calculation
- **Smart defaults** — Missing length? Use diameter for turning
- **Warnings collection** — Return partial results + warnings
- **Fallback lookups** — Try `dokoncovani` if `hrubovani` not found

### 6. Constant Times

Simple features use fixed times:

```python
CONSTANT_TIMES = {
    "chamfer": 0.05,     # min per chamfer
    "radius": 0.05,      # min per radius
    "edge_break": 0.02,  # min per edge
}
```

## API

```python
def calculate_features_time(
    features_json: list[dict],
    material_group: str,
    cutting_mode: str = "mid",
    part_type: str = "PRI"
) -> dict:
    """
    Returns:
        {
            "calculated_time_min": 12.5,
            "feature_times": [
                {
                    "type": "outer_diameter",
                    "detail": "ø60 h9",
                    "count": 1,
                    "time_sec": 45.2,
                    "method": "turning Vc=220 f=0.25"
                },
                ...
            ],
            "warnings": ["Unknown feature: knurling"],
            "cutting_mode": "mid",
            "material_group": "20910004"
        }
    """
```

## Use Cases

### 1. AI Estimation Enhancement

AI provides features → deterministic calculation provides breakdown:

```python
ai_features = extract_features_from_drawing(pdf)
breakdown = calculate_features_time(
    ai_features["features"],
    material_group=ai_features["material_group"],
    cutting_mode="mid"
)
# Show user: "12.5 min (5 min turning, 3 min drilling, ...)"
```

### 2. Calibration Reference

Compare AI estimate vs deterministic calculation:

```python
ai_time = ai_estimation["estimated_time_min"]
det_time = calculate_features_time(...)["calculated_time_min"]
deviation = abs(ai_time - det_time) / det_time
# If deviation > 30% → flag for review
```

### 3. Manual Time Estimation

User manually enters features → get time calculation:

```python
manual_features = [
    {"type": "outer_diameter", "count": 1, "detail": "ø50", "location": "tělo"},
    {"type": "thread_external", "count": 1, "detail": "M20×2.5", "location": "konec"}
]
time = calculate_features_time(manual_features, "20910004")["calculated_time_min"]
```

## Consequences

### Positive

✅ **Deterministic** — Same features → same time (no randomness)
✅ **Explainable** — Shows exact formula used per feature
✅ **Consistent** — Uses same cutting conditions as manual operations
✅ **Tunable** — Update cutting catalog → all calculations update
✅ **Testable** — Can write unit tests with exact expected outputs
✅ **Database-driven** — Cutting conditions managed in DB, not code

### Negative

⚠️ **Limited to parsed features** — Garbage in, garbage out
⚠️ **Simplistic paths** — Real toolpaths are more complex
⚠️ **No setup time** — Only calculates spindle time
⚠️ **Detail parsing fragility** — Free-text "detail" may not parse

### Mitigations

- Use AI extraction as **input**, deterministic calc as **verification**
- Show warnings when dimensions can't be parsed
- Default to conservative estimates (e.g., length = diameter if missing)
- Collect real production data to validate formulas

## Implementation

**Files:**
- `app/services/feature_calculator.py` (558 LOC) — Main calculation engine
- `tests/test_feature_calculator.py` (348 LOC) — 28 tests, all passing
- `scripts/demo_feature_calculator.py` (167 LOC) — Demo/examples

**Dependencies:**
- `app/services/cutting_conditions_catalog.py` — Database of Vc, f, Ap
- Standard Python: `math`, `re`, `logging`, `typing`

**Test Coverage:**
- Detail parsing (diameter, length, width, depth, pitch)
- Time formulas (turning, drilling, milling, threading)
- Feature mapping (41 feature types)
- Error handling (unknown features, missing dimensions, unknown materials)
- Material comparison (aluminum vs steel vs stainless)
- Cutting mode effects (low vs mid vs high)

## Alternatives Considered

### A. Pure AI Estimation (Current)

**Rejected:** Non-deterministic, unexplainable, hard to calibrate.

### B. Manual Time Standards Database

**Rejected:** Too rigid, doesn't scale to custom features.

### C. CAM Simulation

**Rejected:** Requires STEP file + CAM software, too slow for quoting.

### D. Hybrid (Chosen)

AI extracts features → Deterministic calculation → User validation.

## References

- **ADR-035:** TimeVision Calibrated Estimation (AI + human feedback)
- **ADR-043:** TimeVision Technology Integration (AI panel in UI)
- **Cutting Conditions Catalog:** Sandvik Coromant, Iscar, Kennametal standards
- **Machining Formulas:** Standard CNC programming textbooks

## Future Work

1. **Path length estimation** — Better approximation for milling paths
2. **Setup time calculation** — Add fixture/tool change time
3. **Multi-pass strategies** — Optimize roughing + finishing
4. **Tool selection** — Auto-select optimal tool diameter
5. **Machine constraints** — Respect max RPM, power limits
6. **Real data calibration** — Compare against actual production times

## Verification

```bash
pytest tests/test_feature_calculator.py -v
# 28 passed, 6 warnings in 0.04s

python scripts/demo_feature_calculator.py
# Shows 4 demo scenarios with feature breakdown
```

**Example Output:**

```
Material: 20910004 (Ocel konstrukční)
Cutting mode: mid
Total time: 0.42 min

Feature breakdown:
  - outer_diameter       × 1:   0.21 min  (turning Vc=220 f=0.25)
  - thread_external      × 1:   0.01 min  (threading Vc=80 pitch=1.5)
  - chamfer              × 4:   0.20 min  (constant 0.05 min)
```

---

**Status:** ✅ IMPLEMENTED
**Tests:** ✅ 28 passing
**Integration:** Ready for TimeVision AI panel integration
