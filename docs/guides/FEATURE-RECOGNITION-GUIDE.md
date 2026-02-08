# Feature Recognition API Guide

**Module:** Feature Recognition Testing Module
**Status:** Phase 1 - SVG Pattern Matching
**Created:** 2026-02-04

---

## Overview

Feature Recognition Module analyzuje technické výkresy a automaticky extrahuje výrobní features (díry, závity, zkosení, atd.) + navrhuje manufacturing operations.

**Přístup:** Hybrid (Pattern Matching + Claude API)
- **Phase 1:** Pattern matching (regex-based, fast, no cost) ✅ IMPLEMENTED
- **Phase 2:** Claude API fallback (deep analysis, paid) 🚧 FUTURE

---

## API Endpoints

### 1. Analyze Drawing
```http
POST /api/feature-recognition/analyze
Content-Type: multipart/form-data
```

**Upload & analyze technical drawing (SVG or PDF).**

**Request:**
```bash
curl -X POST http://localhost:8000/api/feature-recognition/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@stuetzfuss_contour.svg" \
  -F "part_id=12345"
```

**Parameters:**
- `file` (required): SVG or PDF file
- `part_id` (optional): Part ID to associate

**Response:**
```json
{
  "recognition_id": null,
  "source": "pattern_matching",
  "confidence": 0.95,
  "metadata": {
    "part_number": "249322",
    "drawing_number": "PDM-249322_03",
    "material_number": "1.1191",
    "revision": "03"
  },
  "features": [
    {
      "type": "hole",
      "raw_text": "Ø19",
      "diameter": 19.0,
      "through": true
    },
    {
      "type": "thread",
      "raw_text": "M30×2",
      "diameter": 30,
      "pitch": 2.0
    }
  ],
  "operations": [
    {
      "operation_type": "drilling",
      "tool": "drill_19mm",
      "params": {
        "diameter": 19,
        "depth": "through"
      },
      "estimated_time_min": 3.8,
      "confidence": 1.0,
      "notes": null
    },
    {
      "operation_type": "thread_cutting",
      "tool": "thread_mill",
      "params": {
        "thread_spec": "M30×2",
        "diameter": 30,
        "pitch": 2.0
      },
      "estimated_time_min": 15.0,
      "confidence": 1.0,
      "notes": null
    }
  ],
  "cost": 0.0,
  "warnings": []
}
```

**Status Codes:**
- `200 OK` - Analysis successful
- `400 Bad Request` - Invalid file type or size
- `413 Payload Too Large` - File exceeds size limit (SVG: 5MB, PDF: 10MB)
- `500 Internal Server Error` - Analysis failed

---

### 2. Get Recognition
```http
GET /api/feature-recognition/{recognition_id}
```

**Retrieve previous feature recognition analysis by ID.**

**Note:** Only Claude API analyses are saved to DB (pattern matching results are not saved).

**Request:**
```bash
curl http://localhost:8000/api/feature-recognition/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "id": 123,
  "created_at": "2026-02-04T10:00:00Z",
  "part_id": 12345,
  "drawing_hash": "abc123...",
  "geometry_features": {...},
  "ai_source": "claude_api",
  "ai_suggested_operations": [...],
  "ai_confidence_score": 0.85,
  "verified_at": null,
  "status": "pending"
}
```

**Status Codes:**
- `200 OK` - Recognition found
- `404 Not Found` - Recognition not found

---

### 3. Verify Recognition
```http
POST /api/feature-recognition/{recognition_id}/verify
```

**Human verification of AI results (CRITICAL for learning!).**

Verified cases become training examples for future Claude API analyses.

**Request:**
```bash
curl -X POST http://localhost:8000/api/feature-recognition/123/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "verified_operations": [
      {
        "operation_type": "drilling",
        "tool": "drill_19mm",
        "params": {"diameter": 19, "depth": "through", "length_mm": 89}
      }
    ],
    "corrections": "Ø19 is through-hole, not blind. Length 89mm from STEP model.",
    "verification_notes": "All operations verified against 3D model."
  }'
```

**Requires:** `ADMIN` or `OPERATOR` role

**Status Codes:**
- `200 OK` - Verification saved
- `400 Bad Request` - Already verified
- `404 Not Found` - Recognition not found

---

## Supported File Types

### Phase 1 (Current)
✅ **SVG** - Pattern matching (regex)
- Size limit: 5 MB
- Magic bytes validation
- Extracts: holes, threads, chamfers, radii, cones

❌ **PDF** - Not yet implemented (501 Not Implemented)

### Phase 2 (Future)
- PDF parsing (PyMuPDF)
- STEP 3D geometry analysis
- Claude API fallback for complex cases

---

## Pattern Recognition Rules

**Features detected (regex-based):**

| Feature | Pattern | Example |
|---------|---------|---------|
| Thread | `M(\d+)×?(\d+\.?\d*)?` | M30×2, M8x1.25 |
| Hole | `[ØΦ](\d+\.?\d*)` | Ø19, Φ12.5 |
| Chamfer | `(\d+\.?\d*)\s*[×x]\s*(\d+)°` | 1.5×45°, 2x45° |
| Radius | `R(\d+\.?\d*)` | R1, R2.5 |
| Cone | `(\d+)°` | 31°, 82° |

**Metadata extracted:**
- Part number (6 digits)
- Drawing number (PDM-XXXXXX_XX)
- Revision (Rev. 03)
- Material (Mat: 1.4301)
- Surface treatment + hardness

---

## Security

**File Validation:**
- Magic bytes check (no spoofed extensions)
- File size limits enforced
- Path traversal prevention
- Temp file cleanup

**Access Control:**
- Authentication required (JWT Bearer token)
- Verification requires ADMIN/OPERATOR role

**Transaction Safety:**
- Rollback on errors (L-008)
- No partial saves

---

## Testing

**Quick test with curl:**
```bash
# 1. Start server
python gestima.py run

# 2. Login (get token)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin" | jq -r '.access_token')

# 3. Analyze test file
curl -X POST http://localhost:8000/api/feature-recognition/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@stuetzfuss_contour.svg" \
  | jq
```

**Expected output:**
- Confidence: ~0.95 (high, pattern matching)
- Features: 10+ (holes, threads, chamfers)
- Operations: 15+ (drilling, threading, chamfering)
- Cost: 0.0 (no API call)

---

## Future Enhancements

**Phase 2: Claude API Integration**
- Low confidence → Claude API fallback
- Historical learning from verified cases
- Similarity search in knowledge base
- Prompt engineering with corrections

**Phase 3: STEP 3D Analysis**
- Geometric feature extraction
- Volume/surface area calculation
- Material utilization estimation

**Phase 4: UI Integration**
- Visual editor for corrections
- Side-by-side PDF/operations view
- Operation timeline visualization
- Batch recognition for multiple parts

---

## Related Documentation

- **Schema:** `app/schemas/feature_recognition.py`
- **Router:** `app/routers/feature_recognition_router.py`
- **Service:** `app/services/feature_recognition_service.py`
- **Parser:** `app/services/drawing_parser.py`
- **Model:** `app/models/feature_recognition.py`

---

**Last Updated:** 2026-02-04
**Version:** 1.0 (Phase 1)
