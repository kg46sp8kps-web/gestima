"""PDF Vision Parser - Uses Claude Vision API to extract manufacturing data from technical drawings

This service is the PRIMARY data source for part classification, material, stock dimensions,
and manufacturing features. OCCT serves as fallback when Vision fails or has low confidence.
"""

import os
import base64
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from io import BytesIO

import anthropic
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)

# Note: .env is loaded in gestima.py main(), not here (to avoid blocking imports)


class PDFVisionParser:
    """Parse technical drawings using Claude Vision API (MASTER decision maker)"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4
        self.max_tokens = 2000

    def parse_drawing(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract manufacturing data from PDF drawing

        Returns:
            dict with keys:
                - part_type: "ROT" or "PRI"
                - material: {"code": "11 523", "name": "..."}
                - stock: {"type": "cylinder", "diameter": 50, "length": 120}
                - features: {"holes": [...], "threads": [...], ...}
                - confidence: 0-1 (Vision confidence score)
                - error: str (if parsing failed)
        """
        try:
            # 1. Convert PDF to image
            logger.info(f"Converting PDF to image: {pdf_path}")
            images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)

            if not images:
                return {"error": "PDF conversion failed - no images generated", "confidence": 0}

            # 2. Encode image to base64
            img_base64 = self._image_to_base64(images[0])

            # 3. Build extraction prompt
            prompt = self._build_extraction_prompt()

            # 4. Call Claude Vision API
            logger.info("Calling Claude Vision API...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # 5. Parse JSON response
            content_text = response.content[0].text

            # Extract JSON from response (might be wrapped in markdown)
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()

            result = json.loads(content_text)

            logger.info(f"Vision parsing successful - confidence: {result.get('confidence', 0):.0%}")
            return result

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return {"error": f"API error: {str(e)}", "confidence": 0}

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": f"Failed to parse JSON response: {str(e)}", "confidence": 0}

        except Exception as e:
            logger.error(f"Vision parsing failed: {e}")
            return {"error": str(e), "confidence": 0}

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')

    def _build_extraction_prompt(self) -> str:
        """Build OPTIMIZED feature extraction prompt for Vision API"""
        return """
You are a CNC machining expert reading a technical drawing (PDF). Your task is to extract ONLY the **geometric features and metadata** - do NOT calculate machining times.

---

## 📋 STEP-BY-STEP EXTRACTION GUIDE

### 1️⃣ LOCATE TITLE BLOCK (Bottom-right corner of drawing)
Look for a bordered table with these fields:
- **Material** (Materiál): Extract W.Nr code (e.g., "1.4305", "11 523") or common name ("Ocel", "Nerez", "Al")
- **Drawing Number** (Výkres č.): Alphanumeric code (e.g., "JR810669", "PDM-280739")
- **Scale** (Měřítko): e.g., "1:1", "2:1"
- **Part Name** (Název): Description of the part

**If material code is unclear:**
- Look for "W.Nr" or "Mat." prefix
- Common codes: 1.43xx/1.45xx = Stainless, 11xxx = Carbon steel, Al/EN AW = Aluminum
- If not found, use "unknown" and set confidence < 0.7

---

### 2️⃣ DETERMINE PART TYPE (ROT vs PRI)
**Check these indicators IN ORDER:**

**A) Text labels (highest priority):**
- "SOUSTRUŽENÍ" / "TURNING" → ROT
- "FRÉZOVÁNÍ" / "MILLING" → PRI

**B) View orientation (if no text):**
- **Circular cross-section** in front/side view + centerline → ROT
- **Rectangular cross-section** → PRI
- Multiple diameter dimensions (Ø symbols) → likely ROT
- Length/Width/Height dimensions (rectangular stock) → likely PRI

**C) Feature dominance:**
- Threads, grooves, tapers on cylindrical body → ROT
- Pockets, slots, holes in flat/rectangular body → PRI

---

### 3️⃣ EXTRACT STOCK DIMENSIONS (Polotovar / Raw Material)

**Look for:**
- "Polotovar" or "Tyč" label with dimensions
- Format examples:
  - "Tyč Ø50×120" → cylinder stock, diameter 50mm, length 120mm
  - "Polotovar 60×60×100" → box stock, 60×60mm cross-section, 100mm length
  - "Ø20×10.2" → cylinder Ø20mm × 10.2mm long

**Extract as:**
- `stock_type`: "cylinder" or "box"
- `stock_dims`: Keep original text (e.g., "Ø50×120mm")

**If not explicitly labeled:**
- ROT parts: Use largest diameter + overall length from front view
- PRI parts: Use bounding box dimensions (L×W×H)

---

### 4️⃣ IDENTIFY MACHINING FEATURES (What needs to be machined)

**Extract ONLY features visible on the drawing with dimensions. Do NOT invent features.**

#### **For TURNING (ROT) parts:**

**A) External turning:**
- **Roughing**: Large diameter reduction (>2mm radial)
  - Example: Ø50 → Ø40 over 80mm length
  - Extract: `diameter_start`, `diameter_end`, `length`

- **Finishing**: Final diameter with tolerance
  - Example: Ø15 h6 or Ø15 ±0.02
  - Extract: `diameter_end`, `length`, `tolerance`

**B) Facing (end faces):**
- Flat surface perpendicular to axis
- Extract: `diameter` (of face)

**C) Grooves / Undercuts:**
- Recessed area in cylindrical surface
- Extract: `width`, `depth`, `diameter` (at groove bottom)

**D) Threading:**
- Look for thread symbol (helical lines) or text like "M8×1.25"
  - Extract: `thread_spec` (e.g., "M8×1.25"), `length`

**E) Drilling (axial holes):**
- Hole along centerline or radial
- Extract: `diameter`, `depth` (use "through" if goes through part)

**F) Chamfers:**
- Look for "0.5×45°" dimension on edges
- Extract: `size`, `angle`, `count` (how many edges)

#### **For MILLING (PRI) parts:**

**A) Face milling:**
- Large flat surface (top/bottom of part)
- Extract: `length`, `width` (area to be milled)

**B) Pockets:**
- Recessed rectangular area
- Extract: `length`, `width`, `depth`

**C) Slots:**
- Long narrow recess
- Extract: `length`, `width`, `depth`

**D) Drilling:**
- Circular holes
- Extract: `diameter`, `depth`, `count` (if pattern)

**E) Chamfers/Fillets:**
- Edge breaks
- Extract: `size`, `angle` or `radius`

---

### 5️⃣ READ TOLERANCES & SURFACE FINISH

**Tolerances:**
- Look for: "±0.02", "h6", "H7", "IT7"
- ISO tolerance zones: h6, h7 = shaft (tight), H7 = hole (loose)
- Extract AS TEXT (e.g., "±0.02", "h6")

**Surface Finish:**
- Look for: "Ra 3.2", "Ra 1.6", "Ra 0.8" (roughness in µm)
- Triangular symbol ▽ with number = roughness
- Extract AS TEXT (e.g., "Ra 3.2")

---

## 📤 OUTPUT JSON FORMAT

```json
{
  "part_type": "ROT",
  "material_code": "1.4305",
  "stock_type": "cylinder",
  "stock_dims": "Ø50×120mm",
  "confidence": 0.9,
  "operations": [
    {
      "step": 1,
      "type": "roughing_turn",
      "description": "Reduce diameter Ø50 → Ø40",
      "diameter_start": 50.0,
      "diameter_end": 40.0,
      "length": 80.0
    },
    {
      "step": 2,
      "type": "finishing_turn",
      "description": "Final turn to Ø15 h6",
      "diameter_end": 15.0,
      "length": 40.0,
      "tolerance": "h6",
      "surface_finish": "Ra 3.2"
    },
    {
      "step": 3,
      "type": "drilling",
      "description": "Drill Ø6.6 through",
      "diameter": 6.6,
      "depth": "through"
    },
    {
      "step": 4,
      "type": "threading",
      "description": "Thread M8×1.25",
      "thread_spec": "M8×1.25",
      "length": 15.0
    },
    {
      "step": 5,
      "type": "chamfering",
      "description": "Chamfer 0.5×45° on both ends",
      "size": 0.5,
      "angle": 45,
      "count": 2
    }
  ],
  "notes": "Stainless steel bushing with tight tolerance h6 on main diameter"
}
```

---

## ⚠️ CRITICAL RULES

1. **Return ONLY valid JSON** - no markdown code blocks, no explanations outside JSON
2. **Extract only VISIBLE dimensions** - do not guess or calculate
3. **Use EXACT values from drawing** - if Ø15.0, write 15.0, not 15
4. **Confidence scoring:**
   - 0.9-1.0: All critical data clear (material, part type, key dimensions)
   - 0.7-0.9: Minor assumptions (e.g., stock estimated from part dims)
   - <0.7: Significant unknowns (material unclear, dimensions illegible)
5. **Do NOT calculate:**
   - Machining times
   - Number of passes (app will calculate from radial_depth)
   - Cutting speeds or feeds
   - Tool sizes (unless explicitly dimensioned)
6. **If unsure, write null** - better to return null than wrong data
7. **Notes field**: Brief summary of part type, critical features, any assumptions made

---

## 🎯 QUALITY CHECKLIST BEFORE SUBMITTING

- [ ] Material code extracted from title block (or "unknown")
- [ ] Part type (ROT/PRI) determined with clear reasoning
- [ ] Stock dimensions extracted (or estimated from part dims)
- [ ] All visible features extracted with dimensions
- [ ] Tolerances and surface finishes captured where specified
- [ ] Confidence score reflects data quality
- [ ] JSON is valid (test with a parser)
- [ ] No time estimates included

**Return the JSON now.**
"""
