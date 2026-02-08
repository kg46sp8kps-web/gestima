# PLÁN: Vision API + STEP Data + PDF Context (Hybrid Intelligence)

**Datum:** 2026-02-07
**Koncept:** Použít STEP exact measurements + PDF engineering context = 100% přesnost + správná interpretace

---

## PRINCIP

**Problém s STEP-only:**
- STEP má přesné rozměry, ale NEVÍ co je "main shaft" vs "bore"
- Feature classification (edge convexity) má 50% false positives
- Nemá tolerance, povrch, materiál info

**Problém s PDF-only:**
- Claude Vision může zmást multi-view drawings
- Rozměry z PDF jsou "napsané" (Ø27), ne měřené → co když výkres je starý a díl byl změněn?

**HYBRIDNÍ ŘEŠENÍ:**
```
STEP measurements (exact) + PDF context (semantic) = BEST OF BOTH
```

---

## WORKFLOW

### Fáze 1: OCCT Extract Raw Geometry

```python
# app/services/occt_raw_extractor.py

from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop

def extract_raw_step_geometry(step_file: Path) -> dict:
    """
    Extract RAW geometry from STEP file.
    NO feature classification, NO interpretation.
    Just FACTS: diameters, lengths, positions.
    """

    shape = load_step_file(step_file)

    # Bounding box
    bbox = get_bounding_box(shape)

    # All cylindrical faces
    cylindrical_faces = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)

    face_index = 0
    while explorer.More():
        face = explorer.Current()
        surf = BRepAdaptor_Surface(face)

        if surf.GetType() == GeomAbs_Cylinder:
            cylinder = surf.Cylinder()
            diameter = cylinder.Radius() * 2

            # Face bounding box
            face_bbox = get_face_bounding_box(face)
            z_min = face_bbox.z_min
            z_max = face_bbox.z_max
            length = z_max - z_min

            # Orientation (FORWARD = outer, REVERSED = inner/bore)
            orientation = face.Orientation()
            is_inner = (orientation == TopAbs_REVERSED)

            cylindrical_faces.append({
                "face_id": face_index,
                "type": "cylindrical",
                "diameter": round(diameter, 3),
                "radius": round(diameter/2, 3),
                "z_min": round(z_min, 2),
                "z_max": round(z_max, 2),
                "length": round(length, 2),
                "is_inner": is_inner,
                "orientation": str(orientation)
            })

        face_index += 1
        explorer.Next()

    # Planar faces (for end faces, pockets)
    planar_faces = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)

    face_index = 0
    while explorer.More():
        face = explorer.Current()
        surf = BRepAdaptor_Surface(face)

        if surf.GetType() == GeomAbs_Plane:
            face_bbox = get_face_bounding_box(face)

            planar_faces.append({
                "face_id": face_index,
                "type": "planar",
                "z_position": round(face_bbox.z_center, 2),
                "area": round(get_face_area(face), 2)
            })

        face_index += 1
        explorer.Next()

    # Volume
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    volume = props.Mass()

    return {
        "filename": step_file.name,
        "bbox": {
            "x": round(bbox.x, 2),
            "y": round(bbox.y, 2),
            "z": round(bbox.z, 2),
            "max_diameter": round(max(bbox.x, bbox.y), 2)
        },
        "volume_mm3": round(volume, 2),
        "cylindrical_faces": cylindrical_faces,
        "planar_faces": planar_faces,
        "total_faces": face_index
    }
```

**Output example:**
```json
{
  "filename": "JR 810664.step",
  "bbox": {"x": 75.5, "y": 40, "z": 40, "max_diameter": 40},
  "volume_mm3": 12500,
  "cylindrical_faces": [
    {
      "face_id": 0,
      "type": "cylindrical",
      "diameter": 14.018,
      "z_min": 0,
      "z_max": 40,
      "length": 40,
      "is_inner": true,
      "orientation": "REVERSED"
    },
    {
      "face_id": 5,
      "type": "cylindrical",
      "diameter": 5.0,
      "z_min": 10,
      "z_max": 20,
      "length": 10,
      "is_inner": true,
      "orientation": "REVERSED"
    }
  ],
  "planar_faces": [
    {"face_id": 1, "type": "planar", "z_position": 0, "area": 1256},
    {"face_id": 2, "type": "planar", "z_position": 40, "area": 1256}
  ]
}
```

---

### Fáze 2: Claude Vision Interprets PDF + STEP Data

```python
# app/services/vision_step_matcher.py

import anthropic
import base64
import json
from pydantic import BaseModel
from typing import List, Optional

class InterpretedRotationalPart(BaseModel):
    """
    Claude Vision interprets PDF drawing and matches features to STEP data.
    """
    part_number: str
    part_type: str = "ROT"

    # Interpreted features (matched to STEP faces)
    main_shaft: Optional[dict] = None  # {"step_face_id": 3, "diameter": 27.003, "length": 75.5, "tolerance": "general", "label": "Ø27"}
    bore: Optional[dict] = None  # {"step_face_id": 0, "diameter": 19.01, "depth": 89, "tolerance": "H7"}

    grooves: List[dict] = []  # [{"step_face_id": 12, "width": 2.5, "z_position": 81, "label": "DIN 76-1"}]
    holes: List[dict] = []  # [{"step_face_id": 8, "diameter": 7, "count": 2, "depth": 10}]
    threads: List[dict] = []  # [{"type": "M30×2", "depth": 6, "z_position": 0}]

    # Engineering context (from PDF)
    material: Optional[str] = None
    weight_kg: Optional[float] = None
    tolerance_general: Optional[str] = None
    surface_finish: Optional[str] = None

    # Confidence
    confidence: str = "high"  # high/medium/low
    notes: List[str] = []  # ["Bore tolerance H7 indicates precision fit", "Thread not in STEP model"]


async def interpret_pdf_with_step_data(
    pdf_path: Path,
    step_geometry: dict  # Output from extract_raw_step_geometry()
) -> InterpretedRotationalPart:
    """
    Send PDF image + STEP geometry JSON to Claude Vision.
    Claude matches PDF annotations to STEP faces and interprets engineering intent.
    """

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Read PDF as base64
    pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode()

    # Construct prompt
    prompt = f"""
You are analyzing a technical drawing (PDF) alongside precise 3D CAD measurements (STEP file data).

Your task:
1. Read the PDF drawing and identify all features (shafts, bores, holes, grooves, threads, etc.)
2. Match each PDF annotation to the corresponding STEP geometry face using diameter and z-position
3. Return structured JSON with EXACT measurements from STEP, annotated with engineering context from PDF

STEP geometry data (JSON):
```json
{json.dumps(step_geometry, indent=2)}
```

Instructions:
- Use STEP measurements for all dimensions (they are CAD-exact, more accurate than PDF text)
- Use PDF for feature LABELS (what is it?), TOLERANCES (H7, h6, ISO 2768), SURFACE FINISH (Ra), MATERIAL
- Match features by comparing PDF dimensions with STEP face diameters and z-positions
- If PDF shows "Ø27" and STEP has cylindrical face with diameter=27.003 at same z-position, they are the SAME feature
- For inner cylindrical faces (is_inner=true), check if PDF calls it "bore" or "hole"
- Threads are usually NOT in STEP geometry - extract from PDF only
- If you cannot match a PDF feature to STEP, note it in "notes" field

Example matching logic:
- PDF: "Ø27 main shaft, length 75mm, z=6 to z=81"
- STEP: cylindrical_face with diameter=27.003, z_min=6, z_max=81.5, is_inner=false
- Match: This is the main shaft, use STEP exact diameter 27.003

Return JSON following InterpretedRotationalPart schema.
"""

    # API call
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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "interpreted_part",
                "strict": True,
                "schema": InterpretedRotationalPart.model_json_schema()
            }
        }
    )

    # Parse and validate
    result_dict = json.loads(response.content[0].text)
    result = InterpretedRotationalPart(**result_dict)

    return result
```

**Output example:**
```json
{
  "part_number": "JR 810664",
  "part_type": "ROT",
  "main_shaft": {
    "step_face_id": 3,
    "diameter": 14.018,  // ← FROM STEP (exact!)
    "length": 40,        // ← FROM STEP
    "tolerance": "H7 (+0.018/0)",  // ← FROM PDF
    "label": "Ø14 H7"
  },
  "bore": null,  // No through bore
  "holes": [
    {
      "step_face_id": 5,
      "diameter": 5.0,  // ← FROM STEP
      "count": 2,       // ← FROM PDF (Claude counts from drawing)
      "depth": 10,      // ← FROM STEP
      "label": "M5 threaded holes"
    }
  ],
  "threads": [
    {
      "type": "M5",     // ← FROM PDF (not in STEP!)
      "depth": 6,
      "z_position": 15,
      "note": "Thread not visible in STEP geometry"
    }
  ],
  "material": "EN AW-6082 T6",  // ← FROM PDF
  "weight_kg": 0.07,            // ← FROM PDF
  "tolerance_general": "ISO 2768:1989-mK",
  "surface_finish": "Ra 3.2, Eloxiert farblos",
  "confidence": "high",
  "notes": [
    "Main shaft diameter matched to STEP face_id=3 with 0.018mm tolerance deviation (H7 fit)",
    "M5 threads extracted from PDF only - not present in STEP model"
  ]
}
```

---

### Fáze 3: Time Calculation (Using Interpreted Data)

```python
# app/services/machining_time_from_interpretation.py

def calculate_machining_time(interpreted_part: InterpretedRotationalPart) -> dict:
    """
    Calculate machining time using EXACT STEP measurements + PDF engineering context.
    """

    operations = []
    total_time_min = 0

    # Main shaft turning
    if interpreted_part.main_shaft:
        shaft = interpreted_part.main_shaft
        diameter = shaft["diameter"]  # EXACT from STEP
        length = shaft["length"]

        # Feedrate based on tolerance (from PDF)
        tolerance = shaft.get("tolerance", "general")
        if "H7" in tolerance or "h6" in tolerance:
            feedrate = 0.15  # mm/rev (precision)
            passes = 3
        else:
            feedrate = 0.25
            passes = 2

        # RPM based on diameter
        cutting_speed = 200  # m/min
        rpm = int((cutting_speed * 1000) / (3.14159 * diameter))
        rpm = min(rpm, 3000)

        time_min = (length * passes) / (feedrate * rpm)

        operations.append({
            "type": "OD_TURNING",
            "feature": "main_shaft",
            "diameter_mm": diameter,
            "length_mm": length,
            "tolerance": tolerance,
            "passes": passes,
            "time_min": round(time_min, 2)
        })

        total_time_min += time_min

    # Bore drilling/boring
    if interpreted_part.bore:
        bore = interpreted_part.bore
        diameter = bore["diameter"]
        depth = bore["depth"]

        # Drilling time
        feedrate = 0.2
        rpm = 800
        time_min = (depth * 2) / (feedrate * rpm)

        operations.append({
            "type": "BORING",
            "feature": "bore",
            "diameter_mm": diameter,
            "depth_mm": depth,
            "time_min": round(time_min, 2)
        })

        total_time_min += time_min

    # Holes (drilling)
    for hole in interpreted_part.holes:
        diameter = hole["diameter"]
        depth = hole["depth"]
        count = hole.get("count", 1)

        feedrate = 0.15
        rpm = 1200
        time_per_hole = (depth / (feedrate * rpm))
        time_total = time_per_hole * count

        operations.append({
            "type": "DRILLING",
            "feature": "radial_holes",
            "diameter_mm": diameter,
            "depth_mm": depth,
            "count": count,
            "time_min": round(time_total, 2)
        })

        total_time_min += time_total

    # Threading
    for thread in interpreted_part.threads:
        thread_type = thread["type"]  # e.g. "M5"
        depth = thread["depth"]

        # Extract pitch from thread designation (M5 = 0.8mm pitch)
        pitch_lookup = {"M5": 0.8, "M6": 1.0, "M8": 1.25, "M10": 1.5, "M30": 2.0}
        pitch = pitch_lookup.get(thread_type, 1.0)

        rpm = 300
        time_min = (depth / pitch / rpm) * 3  # 3 passes

        operations.append({
            "type": "THREADING",
            "feature": "thread",
            "thread_type": thread_type,
            "depth_mm": depth,
            "pitch_mm": pitch,
            "time_min": round(time_min, 2)
        })

        total_time_min += time_min

    return {
        "operations": operations,
        "total_time_min": round(total_time_min, 2),
        "source": "STEP_exact_measurements_with_PDF_context",
        "confidence": interpreted_part.confidence
    }
```

---

## ROUTER ENDPOINT

```python
# app/routers/feature_recognition_router.py

@router.post("/api/feature-recognition/interpret-pdf-step")
async def interpret_pdf_with_step(
    pdf_filename: str,
    step_filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Hybrid PDF + STEP interpretation.
    Returns exact STEP measurements annotated with PDF engineering context.
    """

    pdf_path = Path("uploads/drawings") / pdf_filename
    step_path = Path("uploads/drawings") / step_filename

    if not pdf_path.exists() or not step_path.exists():
        raise HTTPException(404, "PDF or STEP file not found")

    try:
        # Step 1: Extract raw STEP geometry (OCCT)
        step_geometry = extract_raw_step_geometry(step_path)

        # Step 2: Claude Vision interprets PDF + matches to STEP
        interpretation = await interpret_pdf_with_step_data(pdf_path, step_geometry)

        # Step 3: Calculate machining time
        time_estimate = calculate_machining_time(interpretation)

        return {
            "success": True,
            "pdf_filename": pdf_filename,
            "step_filename": step_filename,
            "step_raw_geometry": step_geometry,
            "interpretation": interpretation.model_dump(),
            "time_estimate": time_estimate
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

---

## VÝHODY TOHOTO PŘÍSTUPU

✅ **100% přesné rozměry** - Ze STEP (CAD exact), ne z PDF text recognition
✅ **Správná interpretace** - Claude Vision ví CO je který feature (PDF kontext)
✅ **Tolerance awareness** - H7, h6, Ra → ovlivňuje passes/feedrate
✅ **Thread detection** - Z PDF (STEP to nemá)
✅ **Material/weight** - Z PDF (ERP fallback)
✅ **Konzistence** - Pydantic schema garantuje strukturu
✅ **Validace** - Claude matchuje PDF ↔ STEP, flaguje discrepancies
✅ **No feature classification needed** - Claude dělá interpretaci, ne OCCT edge convexity heuristiky

---

## PŘÍKLAD MATCHOVÁNÍ

**PDF výkres říká:**
- "Ø27 main shaft, general tolerance"
- "Ø19 bore, depth 89mm"
- "2× Ø7 mounting holes"
- "M30×2 thread, depth 6mm"

**STEP data obsahuje:**
- Cylindrical face: diameter=27.003, z_min=6, z_max=81.5, is_inner=false
- Cylindrical face: diameter=19.01, z_min=0, z_max=89, is_inner=true
- Cylindrical face: diameter=7.0, z_min=70, z_max=80, is_inner=true (×2)

**Claude Vision matchuje:**
- PDF "Ø27" → STEP face diameter=27.003 → ✅ Main shaft (používá 27.003)
- PDF "Ø19 bore" → STEP face diameter=19.01, is_inner=true → ✅ Bore (používá 19.01)
- PDF "2× Ø7" → STEP face diameter=7.0 (nalezne 2 faces) → ✅ Holes (používá 7.0)
- PDF "M30×2 thread" → NENÍ v STEP → ⚠️ Note: "Thread extracted from PDF only"

---

## TESTOVACÍ SCÉNÁŘ

1. **JR 810664** (simple ROT part)
   - STEP extraction → cylindrical faces
   - PDF interpretation → match main shaft bore, holes, threads
   - Time calculation → based on exact STEP dimensions

2. **Validation:**
   - Porovnej PDF label "Ø14 H7" vs STEP measurement 14.018mm
   - Delta < 0.1mm → ✅ Match confident
   - Delta > 0.5mm → ⚠️ Flag discrepancy

---

## IMPLEMENTAČNÍ CHECKLIST

- [ ] Backend: `occt_raw_extractor.py` (STEP → raw geometry JSON)
- [ ] Backend: `vision_step_matcher.py` (Claude Vision + STEP data → interpretation)
- [ ] Backend: `machining_time_from_interpretation.py` (time calculation)
- [ ] Router: `POST /api/feature-recognition/interpret-pdf-step`
- [ ] Frontend: PdfStepInterpretationPanel.vue (display results)
- [ ] Test: JR 810664 (simple), DRM 90057637 (complex)

---

**Odhadovaný čas:** ~10 hours (backend OCCT + Vision API + frontend)

**Status:** READY TO IMPLEMENT

---

**Tohle je to, co jsi měl na mysli?** 🚀
