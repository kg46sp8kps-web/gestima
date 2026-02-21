# Gestima OpenAI Fine-Tuning Test Dataset (10 parts)

**Generated:** 2026-02-19
**Files:**
- `ft_test_10.jsonl` — 11.41 MB, 10 entries
- `scripts/generate_ft_test_10.py` — Generator script

**SHA-256:** `0bee72fa17a8b5cbb6cf78b1d30020e97ab9cb6c4d5a3c330a4ce2c74892bfbc`

---

## Quick Start

```bash
# Upload to OpenAI
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose="fine-tune" \
  -F file="@ft_test_10.jsonl"

# Create fine-tuning job
curl https://api.openai.com/v1/fine_tuning/jobs \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "training_file": "file-XXXXXXXXXX",
    "model": "gpt-4o-2024-08-06",
    "suffix": "gestima-test-10"
  }'
```

---

## Dataset Summary

### Selected Parts

| Article  | VPs | Material | Stock      | Operations                      | Time (min) |
|----------|-----|----------|------------|---------------------------------|------------|
| A48719F  | 51  | 1.7225   | round_bar  | SAW→LATHE→MANUAL→QC             | 5.09       |
| 10070319 | 47  | 1.0715   | round_bar  | SAW→LATHE→DRILL→QC              | 1.59       |
| 1094169  | 44  | 1.0715   | round_bar  | SAW→LATHE→QC                    | 4.10       |
| 0051311  | 56  | 1.0570   | flat_bar   | SAW→MILL→DRILL→MANUAL→QC        | 7.57       |
| 0329422  | 46  | 1.0036   | flat_bar   | SAW→MILL→QC                     | 6.84       |
| 0343417  | 43  | 1.0503   | square_bar | SAW→MILL→QC                     | 9.61       |
| 10947285 | 37  | 1.4104   | round_bar  | SAW→LATHE→MILL→DRILL→MANUAL     | 9.43       |
| 0050985  | 35  | 2.1090   | round_bar  | SAW→LATHE→MILL→DRILL→QC         | 4.00       |
| 0060882  | 41  | 1.4104   | round_bar  | SAW→LATHE→DRILL→QC              | 1.13       |
| 0302361  | 42  | 1.0503   | flat_bar   | SAW→MILL→QC                     | 6.39       |

### Diversity Achieved

**Materials (7 unique):**
- 1.0036 (Carbon steel)
- 1.0503 (C45 carbon steel) × 2
- 1.0570 (Carbon steel)
- 1.0715 (Free-cutting steel) × 2
- 1.4104 (Stainless steel) × 2 ✓ UNUSUAL
- 1.7225 (Alloy steel)
- 2.1090 (Copper alloy) ✓ UNUSUAL

**Stock shapes (3):**
- round_bar — 6 parts
- flat_bar — 3 parts
- square_bar — 1 part

**Operation diversity:**
- LATHE parts: 6
- MILL parts: 6
- DRILL parts: 5
- LATHE + MILL (both): 2
- Unusual materials: 3 parts

---

## Selection Criteria

### 1. Precision Cut
- `manning_pct` ≤ 100%
- LATHE `manning_pct` ≥ 50%
- MILL `manning_pct` ≥ 70%
- `norm_ratio` ≤ 5.0

### 2. Low Variability
- CV ≤ 0.5 for LATHE/MILL time
- CV ≤ 0.5 for LATHE/MILL manning

### 3. Data Quality
- `file_id` present (PDF exists)
- Minimum 3 VPs (production orders)
- NOT in FEW_SHOT_EXAMPLES (6 excluded articles)

### 4. Sanity Checks
- Total time: 0.1–120 min
- Has SAW operation
- Not ONLY saw

**Candidate pool:** 1,096 parts → **449 eligible** → **10 selected**

---

## Format Specification

### Message Structure

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Jsi CNC technolog. Analyzuj výrobní výkres..."
    },
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgo...",
            "detail": "high"
          }
        },
        {
          "type": "text",
          "text": "Analyzuj výkres a navrhni technologický postup."
        }
      ]
    },
    {
      "role": "assistant",
      "content": "{\"material_norm\":\"1.0715\",\"stock\":{...},\"operations\":[...]}"
    }
  ]
}
```

### Assistant Answer Schema

```json
{
  "material_norm": "1.0715",
  "stock": {
    "shape": "round_bar",
    "diameter_mm": 35.0,
    "width_mm": null,
    "height_mm": null,
    "length_mm": 25.0
  },
  "operations": [
    {
      "category": "SAW",
      "machine": "BOMAR STG240A",
      "operation_time_min": 0.09,
      "setup_time_min": 0,
      "manning_pct": 69,
      "num_operations": 1
    }
  ]
}
```

### Key Format Rules

1. **material_norm key** — MUST be `material_norm` (not `material`)
2. **Stock dimensions** — Real values from DB (not all null)
3. **manning_pct** — Capped to 1–100 range
4. **operation_time_min** — Trimmed mean 10% of per-VP total times
5. **setup_time_min** — `int(trimmed mean)`
6. **Stock shape** — Lowercase

---

## Ground Truth Computation

### Trimmed Mean 10%

```python
def trimmed_mean_10(values):
    if len(values) < 5:
        return median(values) if len(values) >= 3 else mean(values)
    n = len(values)
    trim = max(1, int(n * 0.10))
    sorted_vals = sorted(values)
    trimmed = sorted_vals[trim : n - trim]
    return mean(trimmed)
```

### Manning Cap

```python
manning = actual_manning or planned_manning or 1.0
if manning <= 2.0:
    manning *= 100
manning = min(manning, 100.0)
manning = max(manning, 1.0)
```

### Per-Category Aggregation

1. Group by VP → category
2. Sum times/setups per VP
3. Average manning per VP
4. Trimmed mean across VPs
5. CV computation: `stdev(values) / mean(values)`

---

## Validation Results

```
✅ Line count: 10
✅ All entries have 3 messages (system, user, assistant)
✅ All assistant answers have material_norm key
✅ All stock dimensions present (not all null)
✅ All manning_pct in range 1–100
✅ All operation_time_min ≥ 0
✅ All setup_time_min are integers
✅ All PDF images are base64 PNG with detail: high
✅ All JSON parseable
```

**File size:** 11,959,209 bytes (11.41 MB)
**Avg per entry:** 1,195,921 bytes (~1.14 MB)

---

## Sample Assistant Answers

### Part 1: A48719F (1.7225 alloy steel)

```json
{
  "material_norm": "1.7225",
  "stock": {
    "shape": "round_bar",
    "diameter_mm": 110.0,
    "width_mm": null,
    "height_mm": null,
    "length_mm": 6.0
  },
  "operations": [
    {
      "category": "SAW",
      "machine": "BOMAR STG240A",
      "operation_time_min": 0.94,
      "setup_time_min": 0,
      "manning_pct": 82,
      "num_operations": 1
    },
    {
      "category": "LATHE",
      "machine": "SMARTURN 160",
      "operation_time_min": 3.36,
      "setup_time_min": 78,
      "manning_pct": 76,
      "num_operations": 1
    },
    {
      "category": "MANUAL",
      "machine": "MECHANIK",
      "operation_time_min": 0.79,
      "setup_time_min": 2,
      "manning_pct": 70,
      "num_operations": 1
    },
    {
      "category": "QC",
      "machine": "KONTROLA",
      "operation_time_min": 0.08,
      "setup_time_min": 0,
      "manning_pct": 100,
      "num_operations": 1
    }
  ]
}
```

**Context:**
- Total production time: 5.09 min
- Total setup time: 80 min
- 51 VPs (production orders)
- Rotational part with manual finishing

### Part 2: 10070319 (1.0715 free-cutting steel)

```json
{
  "material_norm": "1.0715",
  "stock": {
    "shape": "round_bar",
    "diameter_mm": 35.0,
    "width_mm": null,
    "height_mm": null,
    "length_mm": 25.0
  },
  "operations": [
    {
      "category": "SAW",
      "machine": "BOMAR STG240A",
      "operation_time_min": 0.09,
      "setup_time_min": 0,
      "manning_pct": 69,
      "num_operations": 1
    },
    {
      "category": "LATHE",
      "machine": "SMARTURN 160",
      "operation_time_min": 1.05,
      "setup_time_min": 33,
      "manning_pct": 57,
      "num_operations": 1
    },
    {
      "category": "DRILL",
      "machine": "VS20",
      "operation_time_min": 0.45,
      "setup_time_min": 2,
      "manning_pct": 95,
      "num_operations": 1
    },
    {
      "category": "QC",
      "machine": "KONTROLA",
      "operation_time_min": 0.05,
      "setup_time_min": 0,
      "manning_pct": 100,
      "num_operations": 1
    }
  ]
}
```

**Context:**
- Total production time: 1.59 min
- Total setup time: 35 min
- 47 VPs (production orders)
- Typical lathe + drilling workflow

---

## Next Steps

After testing with this 10-part dataset:

1. **Verify learning:**
   - Operation sequences (SAW → LATHE/MILL → DRILL → QC)
   - Material recognition (W.Nr vs EN vs AISI)
   - Time estimates vs GT

2. **Test inference:**
   - Use `/api/ft-debug/{part_id}/inference` endpoint
   - Compare AI predictions with GT
   - Calculate MAPE (Mean Absolute Percentage Error)

3. **Scale if successful:**
   - Generate full dataset (449 eligible parts)
   - Estimated cost: ~$150 for full fine-tuning
   - Monitor model performance on held-out test set

---

## Generator Script

Location: `scripts/generate_ft_test_10.py`

**Key functions:**
- `trimmed_mean_10()` — Robust average
- `compute_cv()` — Coefficient of variation
- `extract_wnr_from_code()` — Material code parsing
- `pdf_to_base64()` — PyMuPDF rendering (150–300 DPI)
- `compute_gt_from_records()` — GT aggregation logic

**Dependencies:**
- PyMuPDF (fitz) — PDF rendering
- sqlite3 — Database access
- Python 3.10+

**Reproducibility:**
```bash
python scripts/generate_ft_test_10.py
# Outputs: ft_test_10.jsonl
```

---

## Technical Details

### PDF Rendering

```python
dpi = min(300, int(72 * min(scale_w, scale_h)))
dpi = max(dpi, 150)
zoom = dpi / 72.0
mat = fitz.Matrix(zoom, zoom)
pix = page.get_pixmap(matrix=mat, alpha=False)
png_bytes = pix.tobytes("png")
```

**Result:** 150–300 DPI PNG, max dimension 4096px

### Image Size

Average base64 PNG size: ~1.14 MB per entry
Total dataset: 11.41 MB for 10 parts

**Full dataset estimate:** 449 parts × 1.14 MB ≈ **512 MB**

### Training Cost Estimate

**Test dataset (10 parts):**
- ~10 epochs typical
- ~$2–5 estimated cost

**Full dataset (449 parts):**
- ~$150 estimated cost (OpenAI GPT-4o fine-tuning pricing)

---

## Troubleshooting

### Missing PDF

```
SKIP {article}: PDF render failed
```

**Fix:** Check `file_records.file_path` → ensure file exists in `uploads/`

### Invalid stock dimensions

All `null` values → check `material_inputs` table for:
- `stock_shape`
- `stock_diameter` / `stock_width` / `stock_height` / `stock_length`

### High CV values

CV > 0.5 → part excluded
**Meaning:** High variability in production times across VPs → unreliable GT

---

## References

- **Service:** `app/services/ft_debug_service.py`
- **Schema:** `app/schemas/ft_debug.py`
- **Original generator:** `scripts/generate_ft_v2_data.py`
- **System prompt:** `ft_debug_service.py:40-93`
- **WC mapping:** `ft_debug_service.py:97-115`

---

**Generated by:** scripts/generate_ft_test_10.py
**Date:** 2026-02-19
**Version:** 1.0
