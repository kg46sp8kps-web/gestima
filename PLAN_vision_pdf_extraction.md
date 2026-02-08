# PLÁN: Claude Vision PDF Extraction s garantovanou konzistencí

**Datum:** 2026-02-07
**Cíl:** Extrahovat rozměry z PDF pomocí Claude Vision API s **KONZISTENTNÍM JSON výstupem**

---

## KLÍČ: Anthropic Structured Outputs

**Problém:** Claude Vision může vracet různé formáty, chybějící pole, apod.

**Řešení:** `response_format` parametr v Anthropic API (dostupný od 2024-10)

```python
import anthropic
from pydantic import BaseModel
from typing import List, Optional

# 1. DEFINUJ PYDANTIC SCHEMA (garantuje strukturu)
class RotationalPartDimensions(BaseModel):
    part_type: str = "ROT"  # Always "ROT"
    part_number: str
    material: Optional[str] = None
    weight_kg: Optional[float] = None

    # OD turning sections
    od_sections: List[dict]  # [{"diameter": 27.5, "length": 45, "z_start": 0, "z_end": 45}]

    # Bore (if present)
    bore_diameter: Optional[float] = None
    bore_depth: Optional[float] = None

    # Holes (radial)
    holes: List[dict] = []  # [{"diameter": 7, "count": 2, "depth": 10}]

    # Grooves
    grooves: List[dict] = []  # [{"width": 3, "depth": 0.8, "z_position": 40}]

    # Threads
    threads: List[dict] = []  # [{"type": "M30×2", "depth": 6}]

    # Overall
    total_length: float
    max_diameter: float


class PrismaticPartDimensions(BaseModel):
    part_type: str = "PRI"
    part_number: str
    material: Optional[str] = None
    weight_kg: Optional[float] = None

    # Envelope
    length: float
    width: float
    height: float

    # Holes
    holes: List[dict] = []  # [{"diameter": 6.6, "depth": 20, "x": 10, "y": 15}]

    # Pockets
    pockets: List[dict] = []  # [{"length": 30, "width": 20, "depth": 10}]

    # Threads
    threads: List[dict] = []  # [{"type": "M5", "x": 0, "y": 0}]


# 2. ANTHROPIC API CALL S STRUCTURED OUTPUT
async def extract_dimensions_from_pdf(pdf_path: Path) -> dict:
    """
    Extract dimensions from PDF using Claude Vision API.
    GUARANTEED to return consistent JSON structure.
    """

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Read PDF as base64
    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    # Prompt (simple, protože schema je defined)
    prompt = """
    Analyze this technical drawing and extract ALL dimensions.

    Instructions:
    - For ROTATIONAL parts (turned on lathe): Return RotationalPartDimensions
    - For PRISMATIC parts (milled): Return PrismaticPartDimensions
    - Extract EVERY dimension you can see
    - If unsure about a value, use null
    - z_start=0 is the LEFT end of the part
    """

    # API call with structured output
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }],
        # ✅ KLÍČOVÉ: Pydantic schema garantuje strukturu
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "part_dimensions",
                "strict": True,  # Enforce exact schema
                "schema": RotationalPartDimensions.model_json_schema()
                # Nebo PrismaticPartDimensions based on initial detection
            }
        }
    )

    # Parse JSON (GUARANTEED to match schema)
    dimensions = json.loads(response.content[0].text)

    return dimensions
```

---

## KONZISTENCE GARANTOVÁNA

**Výhody Structured Outputs:**
- ✅ **100% validní JSON** (API odmítne nevalidní response)
- ✅ **Všechna pole přítomna** (null pokud Claude neví)
- ✅ **Typová bezpečnost** (float je float, ne string)
- ✅ **Žádné parsing errors** (Pydantic auto-validace)

**Anthropic dokumentace:**
https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode

---

## WORKFLOW

### Backend Implementation

```python
# app/services/pdf_vision_extractor.py

from pathlib import Path
from typing import Union
import anthropic
import base64
import json
from pydantic import BaseModel, Field
from typing import List, Optional

# Pydantic schemas (výše definované)
class RotationalPartDimensions(BaseModel):
    # ... (viz výše)
    pass

class PrismaticPartDimensions(BaseModel):
    # ... (viz výše)
    pass


async def extract_part_dimensions(pdf_path: Path) -> Union[RotationalPartDimensions, PrismaticPartDimensions]:
    """
    Extract dimensions from technical drawing PDF.
    Returns structured, validated data.
    """

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode()

    # Step 1: Detect part type (ROT vs PRI)
    detection_prompt = """
    Is this a ROTATIONAL part (cylindrical, turned on lathe) or PRISMATIC part (milled, rectangular)?
    Answer ONLY: "ROT" or "PRI"
    """

    detection_response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": detection_prompt}
            ]
        }]
    )

    part_type = detection_response.content[0].text.strip()

    # Step 2: Extract dimensions with correct schema
    schema_class = RotationalPartDimensions if part_type == "ROT" else PrismaticPartDimensions

    extraction_prompt = f"""
    Extract ALL dimensions from this technical drawing as JSON.
    Part type: {part_type}

    For each feature (OD sections, holes, grooves, etc.), include:
    - Exact dimension values (mm)
    - Position (z-coordinate for ROT, x/y for PRI)
    - Count (if multiple identical features)

    If you cannot determine a value, use null.
    """

    extraction_response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": extraction_prompt}
            ]
        }],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "part_dimensions",
                "strict": True,
                "schema": schema_class.model_json_schema()
            }
        }
    )

    # Parse and validate
    dimensions_dict = json.loads(extraction_response.content[0].text)
    dimensions = schema_class(**dimensions_dict)  # Pydantic validation

    return dimensions


# Router endpoint
@router.post("/api/feature-recognition/extract-pdf-dimensions")
async def extract_pdf_dimensions(
    pdf_filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Extract dimensions from PDF using Claude Vision API.
    Returns structured JSON with guaranteed schema.
    """

    pdf_path = Path("uploads/drawings") / pdf_filename

    if not pdf_path.exists():
        raise HTTPException(404, f"PDF not found: {pdf_filename}")

    try:
        dimensions = await extract_part_dimensions(pdf_path)

        return {
            "filename": pdf_filename,
            "success": True,
            "dimensions": dimensions.model_dump()
        }

    except Exception as e:
        return {
            "filename": pdf_filename,
            "success": False,
            "error": str(e)
        }
```

---

## VALIDACE: STEP vs PDF Cross-Check

```python
# app/services/step_pdf_validator.py

def validate_pdf_against_step(
    pdf_dimensions: Union[RotationalPartDimensions, PrismaticPartDimensions],
    step_analysis: Dict  # Z batch_combined_results.json
) -> Dict:
    """
    Compare PDF-extracted dimensions with STEP measurements.
    Flag discrepancies > 5%.
    """

    validation = {
        "matches": [],
        "discrepancies": [],
        "confidence": "high"
    }

    if pdf_dimensions.part_type == "ROT":
        # Compare max diameter
        pdf_max_dia = pdf_dimensions.max_diameter
        step_max_dia = step_analysis.get("bbox", {}).get("max_diameter")

        if step_max_dia:
            delta = abs(pdf_max_dia - step_max_dia)
            delta_pct = (delta / pdf_max_dia) * 100

            if delta_pct < 5:
                validation["matches"].append({
                    "feature": "max_diameter",
                    "pdf": pdf_max_dia,
                    "step": round(step_max_dia, 2),
                    "delta_pct": round(delta_pct, 1)
                })
            else:
                validation["discrepancies"].append({
                    "feature": "max_diameter",
                    "pdf": pdf_max_dia,
                    "step": round(step_max_dia, 2),
                    "delta_pct": round(delta_pct, 1),
                    "warning": "Large discrepancy - check PDF extraction"
                })
                validation["confidence"] = "medium"

        # Compare total length
        pdf_length = pdf_dimensions.total_length
        step_length = step_analysis.get("bbox", {}).get("z_length")

        if step_length:
            delta = abs(pdf_length - step_length)
            delta_pct = (delta / pdf_length) * 100

            if delta_pct < 5:
                validation["matches"].append({
                    "feature": "total_length",
                    "pdf": pdf_length,
                    "step": round(step_length, 2),
                    "delta_pct": round(delta_pct, 1)
                })
            else:
                validation["discrepancies"].append({
                    "feature": "total_length",
                    "pdf": pdf_length,
                    "step": round(step_length, 2),
                    "delta_pct": round(delta_pct, 1)
                })
                validation["confidence"] = "low"

    return validation
```

---

## FRONTEND: Zobrazení Extrakce

```vue
<!-- frontend/src/components/modules/admin/PdfExtractionPanel.vue -->

<template>
  <div class="pdf-extraction-panel">
    <h3>PDF Dimension Extraction (Claude Vision)</h3>

    <!-- File selector -->
    <select v-model="selectedPdfFile">
      <option v-for="file in pdfFiles" :key="file" :value="file">
        {{ file }}
      </option>
    </select>

    <button @click="extractDimensions" :disabled="loading">
      {{ loading ? 'Extracting...' : 'Extract Dimensions' }}
    </button>

    <!-- Results -->
    <div v-if="extractionResult" class="results">
      <h4>Extracted Dimensions:</h4>

      <!-- ROT part -->
      <div v-if="extractionResult.dimensions.part_type === 'ROT'">
        <p><strong>Part Number:</strong> {{ extractionResult.dimensions.part_number }}</p>
        <p><strong>Material:</strong> {{ extractionResult.dimensions.material }}</p>
        <p><strong>Max Diameter:</strong> Ø{{ extractionResult.dimensions.max_diameter }}mm</p>
        <p><strong>Total Length:</strong> {{ extractionResult.dimensions.total_length }}mm</p>

        <h5>OD Sections:</h5>
        <table>
          <tr>
            <th>Diameter</th>
            <th>Length</th>
            <th>Z Start</th>
            <th>Z End</th>
          </tr>
          <tr v-for="(section, i) in extractionResult.dimensions.od_sections" :key="i">
            <td>Ø{{ section.diameter }}</td>
            <td>{{ section.length }}mm</td>
            <td>{{ section.z_start }}mm</td>
            <td>{{ section.z_end }}mm</td>
          </tr>
        </table>

        <h5>Bore:</h5>
        <p v-if="extractionResult.dimensions.bore_diameter">
          Ø{{ extractionResult.dimensions.bore_diameter }} × {{ extractionResult.dimensions.bore_depth }}mm deep
        </p>
        <p v-else>No bore</p>

        <h5>Holes:</h5>
        <ul>
          <li v-for="(hole, i) in extractionResult.dimensions.holes" :key="i">
            {{ hole.count }}× Ø{{ hole.diameter }} ({{ hole.depth }}mm deep)
          </li>
        </ul>
      </div>

      <!-- Validation against STEP -->
      <div v-if="validation" class="validation">
        <h4>STEP vs PDF Validation:</h4>
        <p><strong>Confidence:</strong> {{ validation.confidence }}</p>

        <h5>Matches:</h5>
        <ul>
          <li v-for="(match, i) in validation.matches" :key="i" class="match">
            ✅ {{ match.feature }}: PDF={{ match.pdf }}mm, STEP={{ match.step }}mm (Δ{{ match.delta_pct }}%)
          </li>
        </ul>

        <h5 v-if="validation.discrepancies.length > 0">Discrepancies:</h5>
        <ul>
          <li v-for="(disc, i) in validation.discrepancies" :key="i" class="discrepancy">
            ⚠️ {{ disc.feature }}: PDF={{ disc.pdf }}mm, STEP={{ disc.step }}mm (Δ{{ disc.delta_pct }}%)
            <br><em>{{ disc.warning }}</em>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const selectedPdfFile = ref('')
const loading = ref(false)
const extractionResult = ref(null)
const validation = ref(null)

async function extractDimensions() {
  loading.value = true

  try {
    // Call backend API
    const response = await fetch(
      `/api/feature-recognition/extract-pdf-dimensions?pdf_filename=${encodeURIComponent(selectedPdfFile.value)}`
    )

    extractionResult.value = await response.json()

    // Also fetch STEP validation
    const validationResponse = await fetch(
      `/api/feature-recognition/validate-pdf-step?pdf_filename=${encodeURIComponent(selectedPdfFile.value)}`
    )

    validation.value = await validationResponse.json()

  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.match {
  color: green;
}

.discrepancy {
  color: orange;
}
</style>
```

---

## IMPLEMENTAČNÍ CHECKLIST

### Backend
- [ ] Install `anthropic` Python package (`pip install anthropic`)
- [ ] Create `app/services/pdf_vision_extractor.py`
  - [ ] Define Pydantic schemas (RotationalPartDimensions, PrismaticPartDimensions)
  - [ ] Implement `extract_part_dimensions()` with structured outputs
  - [ ] Add part type detection (ROT vs PRI)

- [ ] Create `app/services/step_pdf_validator.py`
  - [ ] Implement `validate_pdf_against_step()`
  - [ ] Compare max_diameter, total_length, hole_count

- [ ] Add router endpoints in `feature_recognition_router.py`
  - [ ] `POST /api/feature-recognition/extract-pdf-dimensions`
  - [ ] `GET /api/feature-recognition/validate-pdf-step`

### Frontend
- [ ] Create `frontend/src/components/modules/admin/PdfExtractionPanel.vue`
  - [ ] PDF file selector
  - [ ] Extract button
  - [ ] Results table (OD sections, bore, holes, grooves)
  - [ ] Validation display (matches vs discrepancies)

### Testing
- [ ] Test na JR 810664 (simple ROT part)
- [ ] Test na DRM 90057637 (PRI part)
- [ ] Test na JR 810666 (complex ROT part)
- [ ] Verify structured output ALWAYS returns valid JSON
- [ ] Check validation logic (PDF vs STEP cross-check)

---

## ODHADOVANÝ ČAS

- **Backend PDF extraction:** 3 hours (Anthropic API + Pydantic schemas)
- **Backend validation:** 1 hour (compare PDF vs STEP)
- **Frontend UI:** 2 hours (extraction panel + results display)
- **Testing:** 2 hours (3+ PDF files, edge cases)
- **TOTAL:** ~8 hours (1 dev day)

---

## VÝHODY TOHOTO ŘEŠENÍ

✅ **Konzistence garantována** - Pydantic schema + Anthropic structured outputs
✅ **Validace** - PDF vs STEP cross-check odhalí chyby v extrakci
✅ **Vizualizace** - STEP 3D model (occt-import-js) + PDF dimensions overlay
✅ **Fallback** - Pokud PDF extraction selže, STEP measurements stále k dispozici
✅ **Scalable** - Po otestování na 10 dílech víme success rate

---

## RIZIKA

⚠️ **Multi-view drawings** - Claude Vision může zmást pohledy (validation odhalí)
⚠️ **Cost** - $0.05 per PDF × 1000 dílů = $50/month (akceptovatelné?)
⚠️ **API rate limits** - Max 50 requests/min (batch processing potřebuje throttling)

---

**Status:** READY TO IMPLEMENT
**Next step:** Backend PDF extraction service + test na JR 810664
