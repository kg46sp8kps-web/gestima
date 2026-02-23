# ADR-035: TimeVision Calibrated Time Estimation

**Status:** Accepted
**Date:** 2026-02-12
**Author:** AI + User

## Context

TimeVision modul odhaduje CNC strojni casy z PDF vykresu pomoci Claude API.
Puvodni single-shot pristup mel systematicke chyby:
- Material: zamenovani nazvu dilu za material (Palette → material)
- Rozmery: zamena detailovych kót za celkove
- Casy: masivni nadhodnoceni (6× na malych hliníkovych dilech)

## Decision

### 1. Structured Multi-Step Extraction (Call 1)

Namisto jednoho API call pouzivame **4-step tool use loop**:

1. `identify_drawing_content` — layout, pohledy, meritko
2. `extract_title_block` — material, cislo dilu (backend validace vs katalog)
3. `extract_dimensions` — celkove obalove rozmery (weight cross-check)
4. `extract_features` — vyrobni prvky, operace, complexity

Kazdy step ma backend handler ktery validuje a vraci feedback.
Claude muze self-correct na zaklade varování (⚠️).

### 2. Calibrated Time Estimation (Call 2)

Referencni tabulka v promptu kalibrována na realne vyrobni casy:

| Parametr | Pred | Po |
|----------|------|-----|
| PRI stredni medium (ocel) | 8-20 min | 6-12 min |
| ROT maly simple (ocel) | 2-4 min | 1-3 min |
| Material multiplikator Al | "×0.5-0.6" (vágní) | **×0.40** (presny) |
| Doplnkove casy dira | 0.3-0.5 min | 0.2-0.3 min |
| Instrukce pro breakdown | zadne | Kazda operace UZ zahrnuje multiplikator |

### 3. Kalibracni priklady

3 realne dily s overenymi casy primo v promptu:
- COMBINED ø59×21 Al = 3 min
- PRI 165×73×15 Al = max 10 min
- PRI 85×70×55 Al = 10-15 min

### 4. Complexity redefinice

```
simple  = do 5 prvku CELKEM, bez H7/IT6
medium  = 6-12 prvku, nebo H7, nebo zavity
complex = 13+ prvku, NEBO IT6 a tesnejsi, NEBO Ra<0.8, NEBO 3D kontury
```

## Results

Kalibracni test (4 vykresy, cold start bez similar parts):

| Vykres | Real | AI v1 | AI v4 | Ratio v4 |
|--------|------|-------|-------|----------|
| JR 810663 ø59×21 Al | 3 min | 18.5 min | 3.2 min | 1.07× GOOD |
| D00114455 165×73 Al | max 10 | 12.5 min | 4.2 min | 0.42× BAD |
| 90057637 85×58 Al | 10-15 | 28.5 min | 8.2 min | 0.66× OK |
| PDM-280739 ø280 | 30-45 | 65 min | 48 min | 1.28× GOOD |

Prumerny ratio: 0.86× (pred: ~2.5×)

## Known Limitations

1. **D00114455 podhodnocen** — L-profil s komplikovanym obrysem, multiplikator ×0.40 prilis agresivni
2. **PDM-280739 material None** — AI nedokazala precist material z vykresu, default ocel
3. **Cold start** — bez similar parts databaze jsou odhady mene presne
4. **Complexity** — AI obcas dava "complex" na jednoduche dily

## Calibration UI (2026-02-12)

Pridano v navazujici session:
- `PUT /estimations/{id}/calibrate` — editace complexity + actual_time dohromady
- `TimeVisionActualTimeForm` — select Simple/Medium/Complex + realny cas
- Tlacitko "Prepocitat vse" — batch reprocess vsech vykresu pres AI
- `scripts/import_calibration_to_db.py` — import v4 vysledku do DB

### Stav DB po importu v4

| ID | Vykres | Typ | Complexity | AI | Realny | Status |
|----|--------|-----|-----------|-----|--------|--------|
| 19 | JR 810663 | ROT | medium | 3.2 | 3.0 | verified |
| 20 | D00114455 | PRI | medium | 4.2 | 10.0 | verified |
| 21 | 90057637 | PRI | complex | 8.2 | 12.5 | verified |
| 22 | PDM-280739 | COMBINED | complex | 48.0 | 37.5 | verified |

## Next Steps

1. **Complexity detekce** — AI dava "medium" skoro vsude, potreba lepsich pravidel v extract_features toolu
2. Kalibrovat na zaklade vice realnych casu (similar parts DB)
3. Size-dependent multiplikator (male ×0.40, stredni ×0.50)
4. Napojeni norm prevodnik z masteradmin jako validacni tool
5. Doplnit materialove tabulky ze seedu

## Files

- `app/services/time_vision_tools.py` — tool definitions + backend handlers
- `app/services/time_vision_service.py` — multi-turn extraction loop
- `app/services/time_vision_prompts.py` — calibrated prompts (×0.40 Al)
- `app/services/material_coefficient_resolver.py` — material coefficient resolution
- `app/services/cutting_conditions_catalog.py` — cutting conditions catalog
- `app/routers/time_vision_router.py` — SSE streaming + calibrate endpoint
- `scripts/test_calibration.py` — calibration test script (bez DB)
- `scripts/import_calibration_to_db.py` — import vysledku do DB
- `frontend/src/components/modules/timevision/TimeVisionActualTimeForm.vue` — kalibracni formular
