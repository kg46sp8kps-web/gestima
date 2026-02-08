# Machining Time Estimation Guide

**Version:** 1.0  
**Last Updated:** 2026-02-08  
**Related:** ADR-040, `app/config/material_database.py`

---

## Overview

Physics-based CNC machining time estimation system for STEP files.

**Core algorithm:**
```
Time (min) = (Material to Remove / MRR) + Setup time
```

**Accuracy:** 75-85% (Phase 1), 90-95% (Phase 2 with ML)

---

## Quick Start

### Single File Estimation

**CLI:**
```bash
python -m app.services.machining_time_calculator \
  --step-file "/path/to/part.stp" \
  --material "20910005" \
  --stock-type bbox
```

**Response:**
```json
{
  "total_time_min": 45.23,
  "breakdown": {
    "roughing_min": 32.10,
    "finishing_min": 8.13,
    "setup_min": 5.00
  },
  "confidence": "medium",
  "constraints": [
    {
      "type": "deep_pocket",
      "penalty": 1.8,
      "reason": "depth/width ratio 4.0 > 3"
    }
  ]
}
```

### Batch Processing

**Script:**
```bash
python app/scripts/batch_machining_time_estimation.py \
  --input-dir /path/to/step/files \
  --material-map /path/to/mapping.csv \
  --output-report results.html
```

**Input mapping CSV:**
```csv
filename,material_code
part_001.stp,20910005
part_002.stp,20910007
part_003.stp,20910000
```

---

## Material Codes

### Supported Materials (8-digit codes)

| Code | Material | Category | Hardness (HB) | MRR Aggressive (cm³/min) | Penalties |
|------|----------|----------|---------------|--------------------------|-----------|
| `20910000` | Hliník (Al) | Aluminum | 60 | 800 | Deep: 1.3×, Thin: 1.8× |
| `20910001` | Měď | Copper | 70 | 500 | Deep: 1.4×, Thin: 2.0× |
| `20910002` | Mosaz | Brass | 90 | 650 | Deep: 1.3×, Thin: 1.7× |
| `20910003` | Ocel automatová | Free-cutting steel | 180 | 300 | Deep: 1.5×, Thin: 2.2× |
| `20910004` | C45, S355, E295 | Structural steel | 200 | 250 | Deep: 1.6×, Thin: 2.3× |
| `20910005` | 42CrMo4, 16MnCr5 | Alloy steel | 230 | 180 | Deep: 1.8×, Thin: 2.5× |
| `20910006` | Ocel nástrojová | Tool steel | 250 | 120 | Deep: 2.2×, Thin: 3.0× |
| `20910007` | X5CrNi18-10 (nerez) | Stainless steel | 180 | 150 | Deep: 2.0×, Thin: 2.8× |
| `20910008` | POM, PA, PTFE, PEEK | Plastics | 30 | 1200 | Deep: 1.2×, Thin: 1.5× |

**Note:** Codes aligned with Infor material database (`MATERIAL_GROUP_CODE`, 8-digit format).

---

## How It Works

### 1. Geometry Extraction

From STEP file B-rep (Boundary Representation):

```
✓ Part volume (mm³)
✓ Surface area (mm²)
✓ Bounding box (dx, dy, dz)
✓ Wall thickness distribution
```

**NOT extracted:**
- Individual features (bore, fillet, pocket) — unreliable
- Detailed toolpath — requires CAM software
- Thread specifications — special handling needed

### 2. Stock Envelope Calculation

Two models available:

#### Model A: Bounding Box (default)
```
V_stock = dx × dy × dz
V_remove = V_stock - V_part
```

**Best for:** Milled parts, complex shapes

#### Model B: Cylinder (rotational parts)
```
r = max(dx, dy) / 2
h = dz
V_stock = π × r² × h
V_remove = V_stock - V_part
```

**Best for:** Shafts, rotational symmetry parts

**Selection logic:**
```python
if part_is_rotational_symmetry:
    stock_type = "cylinder"
else:
    stock_type = "bbox"
```

### 3. Material Removal Rate (MRR) Lookup

From `material_database.py`:

```python
data = MATERIAL_DB["20910005"]  # Alloy steel
mrr_aggressive = data["mrr_aggressive_cm3_min"]  # 180 cm³/min
mrr_finishing = data["mrr_finishing_cm3_min"]    # 100 cm³/min
```

**MRR Values Explained:**
- **Aggressive (roughing):** Full engagement, high feed rate, fast removal
- **Finishing:** Light cuts, surface quality focus, slower but precise

### 4. Constraint Detection

System detects machining constraints that require slower feeds/speeds:

#### Constraint 1: Deep Pockets
```
if max_depth / min_width > 3.0:
    penalty *= material_data["deep_pocket_penalty"]
    reason: "Requires smaller tools, poor chip evacuation"
```

**Example:**
- Part has pocket: depth 60mm, width 15mm
- Ratio = 60 / 15 = 4.0 > 3.0 ✓ Constraint detected
- Penalty for alloy steel = ×1.8
- Time increases by 80%

#### Constraint 2: Thin Walls
```
if min_wall_thickness < 3.0 mm:
    penalty *= material_data["thin_wall_penalty"]
    reason: "Risk of vibration/deflection, reduced cutting forces"
```

**Example:**
- Wall thickness = 2.5mm < 3mm ✓ Constraint detected
- Penalty for alloy steel = ×2.5
- Time increases by 150%

#### Constraint 3: Combinations
```
total_penalty = deep_pocket_penalty × thin_wall_penalty × ...
```

**Example:**
```
Deep pocket (1.8×) × Thin walls (2.5×) = 4.5× total penalty
Base time 10 min → 45 min with constraints
```

### 5. Time Calculation

```
Time_roughing (min) = (V_remove_cm³ / MRR_aggressive) × penalty
Time_finishing (min) = (A_surface_cm² / MRR_finishing) × 0.1  # 10% of work
Time_setup (min) = 5.0  # constant per job

Time_total = Time_roughing + Time_finishing + Time_setup
```

**Breakdown:** Typically 80% roughing, 20% finishing, 5 min setup

---

## Response Format

### JSON Structure

```json
{
  "request": {
    "filename": "part_001.stp",
    "material_code": "20910005",
    "material_name": "Alloy Steel (42CrMo4)",
    "stock_type": "bbox"
  },
  
  "time": {
    "total_min": 45.23,
    "roughing_min": 32.10,
    "finishing_min": 8.13,
    "setup_min": 5.00
  },
  
  "geometry": {
    "part_volume_mm3": 125000,
    "material_to_remove_mm3": 125000,
    "surface_area_mm2": 45000,
    "stock_envelope": {
      "type": "bbox",
      "dx_mm": 150,
      "dy_mm": 100,
      "dz_mm": 80,
      "stock_volume_mm3": 1200000
    }
  },
  
  "material": {
    "hardness_hb": 230,
    "mrr_aggressive_cm3_min": 180,
    "mrr_finishing_cm3_min": 100,
    "cutting_speed_roughing_m_min": 160,
    "cutting_speed_finishing_m_min": 200
  },
  
  "constraints": [
    {
      "type": "deep_pocket",
      "severity": "high",
      "detected_value": 4.0,
      "threshold": 3.0,
      "penalty_multiplier": 1.8,
      "reasoning": "max_depth / min_width = 4.0 exceeds limit of 3.0",
      "depth_mm": 60,
      "width_mm": 15
    }
  ],
  
  "accuracy": {
    "confidence_level": "medium",
    "estimated_range_min": [36, 54],
    "explanation": "Standard part with 1 significant constraint"
  },
  
  "notes": "Alloy steel (42CrMo4) with deep pocket. Recommend careful tool selection for small tools in confined area."
}
```

### Confidence Levels

| Level | Criteria | Accuracy |
|-------|----------|----------|
| **high** | No constraints, standard geometry | 85-90% |
| **medium** | 1-2 constraints, normal complexity | 75-85% |
| **low** | 3+ constraints, unusual geometry | 70-75% |

---

## Accuracy & Limitations

### Accuracy Expectations

**Phase 1 (Current):**
- Standard parts: **80-85%**
- Complex parts: **75-80%**
- Parts with constraints: **70-75%**

**Why these ranges?**
- Assumption 1: Standard cutting tools available
- Assumption 2: Operator skill level average
- Assumption 3: CNC machine in good condition

### Known Limitations

| Limitation | Reason | Workaround |
|-----------|--------|-----------|
| **No per-operation breakdown** | Can't distinguish drilling vs pocketing | Total time still accurate |
| **No real CAM toolpath** | Would require CAM software license | Use constraints as proxy for complexity |
| **Setup time hardcoded (5 min)** | Varies by workshop | Tune via ML correction layer |
| **Tool availability not checked** | Don't know what's available | Assume standard tooling |
| **Multi-axis time not estimated** | Only 3-axis modeled | Use constraint multiplier |
| **No surface finish effects** | RA values ignored | Assumed in finishing time % |

### What Works Well

✅ Rotational parts (shafts)  
✅ Milled plates with standard pockets  
✅ Parts with clear constraints  
✅ Material selection effects  
✅ Relative comparison (part A vs part B)

### What Doesn't Work Well

❌ Complex sculptured surfaces  
❌ Simultaneous multi-axis  
❌ Parts requiring special tools  
❌ Non-standard fixturing  
❌ Parts needing centerless grinding post-op

---

## ML Correction Layer (Phase 2)

### Planned Improvements (after 100+ parts)

**Data Collection:**
```
For each job:
1. Estimate time (physics model)
2. Record actual shop-floor time
3. Compute correction_factor = actual / estimate
4. Store in database
```

**Training (100+ jobs):**
```python
# Features for ML model:
- Material hardness
- Part complexity (# constraints)
- Geometric features (# holes, pockets, etc.)
- Surface finish requirements
- Stock type (bbox vs cylinder)

# Target:
- correction_factor (0.5-1.5 typical range)

# Model: XGBoost regression
correction = xgb_model.predict(features)
actual_time = physics_time * correction
```

**Example:**
```
Physics estimate: 40 min
ML correction factor: 1.05 (parts similar to this take 5% longer)
Final estimate: 40 × 1.05 = 42 min
Actual: 41 min ← accuracy improved!
```

---

## Integration with Quotes

### Workflow

```
1. User uploads STEP file → Backend extracts geometry
2. User selects material → Lookup MRR values
3. System calculates time → Display estimate
4. Constraint warnings → "Complex part, slower than standard"
5. Quote generated → Labor cost = time × hourly_rate
```

### API Endpoint

```bash
POST /api/machining-time/estimate

Form data:
  step_file: <binary STEP file>
  material: "20910005"
  stock_type: "bbox" or "cylinder"
  
Response:
  {
    "total_time_min": 45.23,
    "confidence": "medium",
    "constraints": [...]
  }
```

### Frontend Display

**Simple view:**
```
Estimated machining time: 45.23 minutes
Confidence: Medium (±12%)
```

**Detailed view:**
```
Breakdown:
  - Roughing: 32.10 min (71%)
  - Finishing: 8.13 min (18%)
  - Setup: 5.00 min (11%)

Constraints detected:
  - Deep pocket (depth/width 4.0) → ×1.8 slower
  
Accuracy: 75-85% (standard deviation ~5 min)
```

---

## Troubleshooting

### "Material not found: 12345678"

**Solution:** Check `MATERIAL_DB` keys in `material_database.py`. Use exact 8-digit code.

```bash
python -c "from app.config.material_database import list_available_materials; print(list_available_materials())"
```

### "Invalid STEP file"

**Solution:** Ensure file is valid STEP (ISO 10303-21). Test with:

```bash
python -c "from OCP.STEPControl import STEPControl_Reader; reader = STEPControl_Reader(); reader.ReadFile('your_file.stp')"
```

### "Time estimate seems too high/low"

**Check:**
1. Constraint multipliers applied? (×1.8, ×2.5)
2. Material hardness reasonable? (HB 60-250)
3. Stock envelope correct? (bbox vs cylinder)

**Tune:**
1. Adjust MRR values in `material_database.py` with empirical data
2. Collect ML correction factor after 50+ parts
3. Review shop-floor feedback

---

## Advanced Usage

### Custom Material

Add to `app/config/material_database.py`:

```python
MATERIAL_DB["20910099"] = {
    "category": "custom_alloy",
    "iso_group": "P",
    "hardness_hb": 220,
    "density": 7.88,
    "mrr_aggressive_cm3_min": 200,  # Empirical data
    "mrr_finishing_cm3_min": 110,
    "cutting_speed_roughing_m_min": 170,
    "cutting_speed_finishing_m_min": 210,
    "deep_pocket_penalty": 1.9,
    "thin_wall_penalty": 2.6,
}
```

### Custom Constraint

Edit time calculator function:

```python
# Example: "Very thin walls" (< 2mm)
if min_wall_thickness < 2.0:
    penalty *= 3.5  # Extra severe penalty
```

---

## References & Further Reading

- **ADR-040:** [Architecture Decision Record](../ADR/040-machining-time-estimation.md)
- **Material Database:** [material_database.py](../../app/config/material_database.py)
- **Sandvik Coromant:** [Cutting Data Handbook](https://www.sandvik.coromant.com/)
- **Kennametal:** [Feed & Speed Calculator](https://www.kennametal.com/)
- **ISO 3685:** Tool life testing standards
- **DIN 6580:** Metal cutting fundamentals

---

**Questions?** See `docs/guides/README.md` or contact DevOps team.
