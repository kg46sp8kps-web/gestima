# BUDOUCÍ VÝVOJ: Vision + STEP Hybrid Intelligence

**Datum návrhu:** 2026-02-07
**Status:** FUTURE (neimplementováno)
**Priorita:** HIGH (po vyčištění OCCT kódu)

---

## KONCEPT

Kombinovat **STEP exact measurements** (OCCT) + **PDF engineering context** (Claude Vision) = 100% přesnost + správná interpretace

### Jak to funguje:

```
1. STEP file → OCCT → RAW geometry extraction
   Output: {
     cylindrical_faces: [
       {face_id: 0, diameter: 27.003, z_min: 6, z_max: 81.5, is_inner: false},
       {face_id: 1, diameter: 19.01, z_min: 0, z_max: 89, is_inner: true},
       ...
     ]
   }

2. PDF drawing + STEP JSON → Claude Vision API
   Prompt: "Matchuj PDF kóty s STEP faces, použij STEP rozměry"

3. Claude Vision output (Pydantic structured):
   {
     "main_shaft": {
       "step_face_id": 0,
       "diameter": 27.003,    ← ZE STEP (exact!)
       "length": 75.5,        ← ZE STEP
       "tolerance": "general", ← Z PDF
       "label": "Ø27"         ← Z PDF
     },
     "bore": {
       "step_face_id": 1,
       "diameter": 19.01,     ← ZE STEP (exact!)
       "tolerance": "H7",     ← Z PDF
       ...
     }
   }

4. Time calculation
   Používá STEP exact dimensions + PDF tolerance pro feedrate
```

---

## VÝHODY

✅ **100% přesné rozměry** - Ze STEP CAD modelu, ne z PDF OCR
✅ **Správná interpretace** - Claude Vision ví CO je který feature (z PDF kontextu)
✅ **Žádná feature classification heuristika** - Claude dělá matching, ne OCCT edge convexity
✅ **Tolerance awareness** - H7, h6 z PDF ovlivňuje passes/feedrate
✅ **Thread detection** - Z PDF (STEP to obvykle nemá)
✅ **Material/weight** - Z PDF nebo ERP
✅ **Konzistence** - Pydantic schema + Anthropic structured outputs

---

## PROČ TO NEDELÁME TEĎ

1. **OCCT experiments archived** - `docs/archive/OCCT-EXPERIMENTS-2026-02.md` dokumentuje neúspěšné edge convexity klasifikace
2. **Waterline 2D viewer bug** - Zigzag artifacts kvůli per-contour scaling
3. **Feature classification** - 50% false positives (bore vs fillet, shaft vs corner radius)
4. **Potřeba cleanup** - Vyčistit OCCT experimenty než buildujeme nový systém

---

## IMPLEMENTAČNÍ PLÁN (PRO BUDOUCNOST)

### Fáze 1: OCCT Raw Extractor (NO classification)
- `app/services/occt_raw_extractor.py`
- Extract cylindrical faces: diameter, z_min, z_max, is_inner
- Extract planar faces: z_position, area
- Extract holes: diameter, depth, position
- **ŽÁDNÁ interpretace** - jen RAW measurements

### Fáze 2: Vision API Matcher
- `app/services/vision_step_matcher.py`
- Send PDF image + STEP JSON to Claude Vision
- Pydantic schema: `InterpretedRotationalPart`, `InterpretedPrismaticPart`
- Claude matchuje PDF labels → STEP face_ids
- Structured outputs garantují konzistenci

### Fáze 3: Time Calculator
- `app/services/machining_time_from_interpretation.py`
- Use STEP exact dimensions
- Use PDF tolerance/surface for passes/feedrate
- Simple formulas (ne CAM simulation)

### Fáze 4: Frontend
- `PdfStepInterpretationPanel.vue`
- Display 3D STEP model (occt-import-js)
- Overlay PDF-matched features
- Show time estimate with confidence

---

## PŘÍKLAD MATCHOVÁNÍ

**PDF výkres:**
- "Ø27 main shaft, general tolerance"
- "Ø19 bore H7, depth 89mm"
- "2× Ø7 mounting holes"
- "M30×2 thread"

**STEP geometry:**
```json
{
  "cylindrical_faces": [
    {"face_id": 0, "diameter": 27.003, "z_min": 6, "z_max": 81.5, "is_inner": false},
    {"face_id": 1, "diameter": 19.01, "z_min": 0, "z_max": 89, "is_inner": true},
    {"face_id": 5, "diameter": 7.0, "z_min": 70, "z_max": 80, "is_inner": true},
    {"face_id": 6, "diameter": 7.0, "z_min": 70, "z_max": 80, "is_inner": true}
  ]
}
```

**Claude Vision matching:**
- PDF "Ø27" @ z=6-81 → STEP face_id=0 (diameter=27.003) → ✅ Main shaft
- PDF "Ø19 bore" @ z=0-89 → STEP face_id=1 (diameter=19.01, is_inner=true) → ✅ Bore
- PDF "2× Ø7" → STEP face_id=5,6 (diameter=7.0, count=2) → ✅ Holes
- PDF "M30×2 thread" → NOT in STEP → ⚠️ Extract from PDF only

**Result JSON:**
```json
{
  "main_shaft": {
    "step_face_id": 0,
    "diameter": 27.003,
    "length": 75.5,
    "tolerance": "general",
    "source": "STEP_measurement"
  },
  "bore": {
    "step_face_id": 1,
    "diameter": 19.01,
    "depth": 89,
    "tolerance": "H7",
    "source": "STEP_measurement"
  },
  "holes": [
    {
      "step_face_ids": [5, 6],
      "diameter": 7.0,
      "count": 2,
      "depth": 10,
      "source": "STEP_measurement"
    }
  ],
  "threads": [
    {
      "type": "M30×2",
      "depth": 6,
      "source": "PDF_only",
      "note": "Not visible in STEP geometry"
    }
  ]
}
```

---

## ODHADOVANÝ ČAS IMPLEMENTACE

- **OCCT raw extractor:** 3 hours
- **Vision API matcher:** 4 hours (Anthropic API + Pydantic schemas)
- **Time calculator:** 2 hours
- **Frontend UI:** 3 hours
- **Testing:** 2 hours
- **TOTAL:** ~14 hours (2 dev days)

---

## PREREQUISITES (CO MUSÍ BÝT HOTOVÉ PŘED IMPLEMENTACÍ)

1. ✅ Vyčištění OCCT kódu (smazáno, archivováno v `docs/archive/OCCT-EXPERIMENTS-2026-02.md`)
2. ✅ Odstranění edge convexity klasifikace (nefunguje)
3. ✅ Odstranění toolpath generation (nemáme CAM software)
4. ✅ Fix waterline 2D viewer (unified scaling)
5. ✅ Konzistentní STEP loading (jedna cesta, ne 3 různé)

---

## RISIKA

⚠️ **Multi-view PDF drawings** - Claude může zmást pohledy (validace STEP ↔ PDF odhalí)
⚠️ **API cost** - $0.05 per PDF × 1000 parts = $50/month
⚠️ **Rate limits** - Max 50 requests/min (batch processing needs throttling)
⚠️ **Complex parts** - PRI parts s curves/pockets mohou být těžší na matching

---

## ALTERNATIVNÍ PŘÍSTUP (SIMPLE FALLBACK)

Pokud Vision + STEP matching je příliš komplexní:

**Plan B: STEP measurements only + user manual labeling**
1. OCCT extract raw measurements
2. User jednou ručně označí "toto je main shaft", "toto je bore"
3. Systém si pamatuje labeling pro podobné díly
4. Machine learning z historical data

---

## REFERENCE

- **Anthropic Structured Outputs:** https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode
- **Pydantic schemas:** Pro garantovanou konzistenci JSON
- **OCCT BRepAdaptor_Surface:** Pro raw geometry extraction bez classification

---

## ROZHODNUTÍ

**ODLOŽENO DO BUDOUCNOSTI**

**Důvod:** Nejdřív vyčistit existující OCCT kód, odstranit nefunkční edge convexity klasifikaci.

**Status:** ✅ OCCT cleanup hotovo, Vision API integration ready to start

---

**Datum zápisu:** 2026-02-07
**Author:** User + Claude Code collaboration
**Status:** DOCUMENTED, NOT IMPLEMENTED
