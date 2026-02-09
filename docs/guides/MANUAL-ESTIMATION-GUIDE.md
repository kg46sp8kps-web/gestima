# Manual Time Estimation Guide

**For:** Shop floor engineers, production planners
**Purpose:** How to estimate machining times for ML training data collection
**Version:** 1.0
**Date:** 2026-02-09

---

## Overview

This guide explains how to manually estimate machining times for parts in the Gestima system. These estimates will be used to train a machine learning model that automates time estimation in the future.

**Goal:** Collect 50+ time estimates per part type (Turning + Milling) to enable ML training.

---

## Opening the Module

### Method 1: Windows Menu
1. Click **Windows** menu (top navigation)
2. Select **Manual Time Estimation**

### Method 2: Browser Console (Dev/QA)
```javascript
useWindowsStore().openWindow('manual-estimation-list', 'Manual Time Estimation')
```

---

## UI Overview

### Left Panel (Part List)

**Tabs:**
- **Turning (12)** — Lathe operations (rotational parts)
- **Milling (25)** — Mill operations (prismatic parts)

**Status badges:**
- ⏱ **Pending** — No estimate yet (needs your input)
- ✓ **Estimated** — Has manual estimate (awaiting production)
- ✅ **Verified** — Has actual time from production (ground truth)

**List items:**
- Filename (e.g., "JR811181.step")
- Part type (ROT or PRI)
- Estimate (if available)

### Right Panel (Details + Form)

**Key Features Section:**
- 10 most important geometry metrics
- Volume, removal ratio, surface area, bbox, material

**Similar Parts Widget:**
- Top 5 similar parts with time estimates
- Similarity score (0-100%)
- Use as baseline for your estimate

**Estimate Form:**
- Input field (time in minutes)
- Save button

---

## How to Estimate

### Step 1: Understand the Part

**Key Features to Check:**

**1. Volume (How much material to remove?)**
- `part_volume_mm3` — Final part size
- `stock_volume_mm3` — Starting stock size
- `removal_ratio` — % of stock to remove (high = more roughing)

**Example:**
```
Part volume: 8,900 mm³
Stock volume: 12,500 mm³
Removal ratio: 0.288 (28.8%)
→ Moderate roughing required
```

**2. Surface Area (How much finishing?)**
- `surface_area_mm2` — Total machined area
- Higher area = more finishing passes

**Example:**
```
Surface area: 3,200 mm²
→ Moderate finishing time
```

**3. BBox (Bounding Box — Part size)**
- `bbox_x × bbox_y × bbox_z` — Overall dimensions
- Larger parts = more tool travel time

**Example:**
```
BBox: Ø35 × 120 mm
→ Small shaft, quick setup
```

**4. Material (Machinability)**
- `material_machinability_index` — 0.0 (hard) to 1.0 (easy)
- Hard materials = slower feeds/speeds

**Example:**
```
Material: Ocel automatová (20910000)
Machinability: 0.5
→ Medium-hard (standard feeds)
```

**5. Rotational Score (Turning complexity)**
- `rotational_score` — 0.0 (prismatic) to 1.0 (pure shaft)
- High score = simpler turning operations

**Example:**
```
Rotational score: 0.72
→ Mostly cylindrical, good for turning
```

---

### Step 2: Use Similar Parts

**Similar Parts Widget** shows:
- Top 5 most similar parts (by geometry)
- Their estimated times
- Similarity score (0-100%)

**How to use:**
- If similarity > 80% → use that estimate as baseline
- If multiple similar parts → average their times
- If no similar parts → estimate from scratch (see Step 3)

**Example:**
```
Similar Parts (3):
• JR811181.step: 45.5 min (similarity: 87%)
• 3DM_90057637: 52.0 min (similarity: 82%)
• PDM-280739: 38.0 min (similarity: 78%)

Suggested: 45-52 min (average: 45.2 min)
```

**Decision:** Start with 45 min baseline, adjust based on differences.

---

### Step 3: Typical Time Ranges

**Turning (ROT) Parts:**

| Complexity | Description | Time Range |
|-----------|-------------|-----------|
| **Simple** | Shaft, no grooves/threads | 15-30 min |
| **Medium** | Shaft with 1-2 grooves or threads | 30-60 min |
| **Complex** | Multiple diameters, tapers, deep grooves | 60-120 min |

**Milling (PRI) Parts:**

| Complexity | Description | Time Range |
|-----------|-------------|-----------|
| **Simple** | Bracket, no pockets | 20-40 min |
| **Medium** | Bracket with 1-2 pockets | 40-80 min |
| **Complex** | Multiple setups, 5-axis, deep pockets | 80-180 min |

**Factors that INCREASE time:**

| Factor | Increase | Reason |
|--------|----------|--------|
| High `removal_ratio` (>50%) | +30-50% | More roughing passes |
| High `surface_area_mm2` | +20-40% | More finishing passes |
| Low `material_machinability_index` (<0.5) | +40-80% | Slower speeds, harder material |
| Complex geometry (pockets, grooves) | +30-60% | More tool changes, slow feeds |
| Thin walls (<3mm) | +50-100% | Reduced feeds to prevent deflection |
| Deep pockets (depth/width > 3) | +40-80% | Small tools, chip evacuation issues |

---

### Step 4: Estimation Workflow

**1. Open part in list (Left Panel)**
- Click part name
- Right panel shows details

**2. Review key features**
- Volume, removal, surface area, bbox, material
- Check for complexity factors (thin walls, deep pockets)

**3. Check similar parts**
- If similarity > 80% → use as baseline
- If no similar parts → use typical time ranges

**4. Adjust for differences**
- Larger part → add time
- Harder material → add time
- More complex geometry → add time

**5. Enter estimate**
- Input time in minutes (e.g., `52.5`)
- Round to 0.5 min (don't over-precision: 45.5 min, not 45.37 min)

**6. Click Save Estimate**
- Status changes to ✓ **Estimated**
- Part now available for similar parts search

---

### Example Estimation

**Part:** JR811181.step (Turning)

**Step 1: Key Features**
```
Part volume: 8,900 mm³
Removal: 3,600 mm³ (28.8%)
Surface: 3,200 mm²
BBox: Ø35 × 120 mm
Material: Ocel automatová (0.5 machinability)
Rotational score: 0.72
```

**Step 2: Similar Parts**
```
• 3DM_90057637: 38.5 min (similarity: 87%)
```

**Step 3: Analysis**
- Similar to 3DM_90057637 (baseline: 38.5 min)
- Slightly larger volume (+15%)
- Moderate removal ratio (28.8%)
- Medium-hard material (0.5)

**Step 4: Adjustment**
- Baseline: 38.5 min
- Larger volume: +5 min
- **Final estimate: 43.5 min**

**Step 5: Save**
- Enter `43.5` in form
- Click **Save Estimate**

---

## Collecting Ground Truth (Actual Times)

### After Production

Once a part has been machined, collect actual time from:
- ERP system (labor hours logged)
- Machine tracking (spindle time + setup time)
- Shop floor report (operator log)

### Import Actual Times via CSV

**1. Prepare CSV file**
```csv
filename,actual_time_min
JR811181.step,48.5
0347039.step,62.0
3DM_90057637.step,35.0
```

**2. Import via API**
```bash
POST /api/estimation/import-actual-times
Content-Type: multipart/form-data

file: actual_times.csv
```

**Effect:**
- `actual_time_min` field populated in database
- Status changes to ✅ **Verified**
- Used for ML training (ground truth)

---

## Exporting Training Data

**When ready to train ML model:**

**1. Click Export Training Data (CSV) button**
- Located at top of list panel

**2. Select part type**
- Turning (ROT)
- Milling (PRI)
- All

**3. Download CSV**
- Contains:
  - All 60+ geometry features
  - `estimated_time_min` (your estimates)
  - `actual_time_min` (ground truth from production)

**4. CSV used for:**
- XGBoost training (Phase 7)
- Feature importance analysis
- Model validation

---

## Tips for Accurate Estimates

**1. Start with similar parts**
- Don't estimate from scratch if not needed
- Use similarity widget (top 5)

**2. Check removal_ratio**
- High removal (>50%) = more roughing time
- Low removal (<20%) = mostly finishing

**3. Material matters**
- Steel 50% slower than aluminum
- Stainless 80% slower than aluminum
- Plastics 60% faster than aluminum

**4. Round to 0.5 min**
- Don't over-precision (45.5 min, not 45.37 min)
- Estimates are not exact (±10% acceptable)

**5. Include setup time**
- Estimate total cycle time (load → unload)
- Setup time typically 5-15 min

**6. Consult shop floor**
- Ask machine operators for complex parts
- Operator experience = valuable input

**7. Track your accuracy**
- After production, compare estimate vs. actual
- Adjust future estimates based on trends

---

## FAQ

**Q: How many estimates needed for ML training?**
A: Minimum 50 per part type (50 ROT + 50 PRI). More = better accuracy.

**Q: What if I don't know how to estimate a part?**
A: Leave it pending, ask shop floor expert, or check similar parts (similarity > 80%).

**Q: Can I update an estimate later?**
A: Yes, use PATCH endpoint (or re-open in UI and save again).

**Q: What if auto-classification is wrong (ROT/PRI)?**
A: Report to dev team. Classification threshold (0.6) can be adjusted. In UI, manual override may be added in Phase 7.

**Q: What if actual time is very different from estimate?**
A: Normal. ML model will learn correction factors. If difference > 100%, investigate (wrong material? unexpected issue?).

**Q: How long does it take to estimate a part?**
A: 2-5 minutes per part (with similar parts). 5-10 minutes if complex (no similar parts).

**Q: Can I use CAM software to estimate?**
A: Yes, if you have access. CAM estimates are very accurate (use as ground truth).

**Q: What if part has non-standard setup?**
A: Add extra time for complex fixtures, multiple setups, or 5-axis operations.

**Q: How to estimate batch parts (multiple identical parts)?**
A: Estimate time for 1 part (including setup). Batch time = setup + (cycle time × quantity).

---

## Workflow Summary

```
1. Open Manual Estimation module
2. Select tab (Turning | Milling)
3. Click part (⏱ Pending status)
4. Review key features (volume, removal, surface, bbox, material)
5. Check similar parts (top 5, similarity > 80%)
6. Estimate time (baseline + adjustments)
7. Enter time in form (round to 0.5 min)
8. Click Save Estimate
9. Repeat for next part
10. After production: Import actual times (CSV)
11. Export training data (CSV) when 50+ samples collected
12. ML model training (Phase 7) → automated estimation
```

---

## Related Documentation

- **ADR-041:** ML Time Estimation Architecture
- **FEATURE-EXTRACTION-DESIGN.md:** 60+ features explained
- **PHASE5-VALIDATION-REPORT.md:** Validation results (37 parts)

---

**Version:** 1.0
**Date:** 2026-02-09
**Contact:** dev@gestima.cz (for issues or questions)
