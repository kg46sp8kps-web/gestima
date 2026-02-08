# Deprecated Documentation - 2026-02-08

Tato dokumentace byla archivována po cleanup machining time systémů.

## Důvod archivace

**Rozhodnutí:** Ponechat pouze 1 systém počítání strojních časů - **Physics-Based MRR Model (ADR-040)**

**Smazané systémy:**
1. Feature-Based Time Calculator (`time_calculator.py`)
2. Batch Estimation Service (`batch_estimation_service.py`)
3. AI Feature Mapper (`ai_feature_mapper.py`)
4. Vision Feature Extractor (`vision_feature_extractor.py`)
5. Feature Recognition Pipeline (`fr_apply_service.py`)
6. G-code/Toolpath Generators
7. Setup Planner

**Důsledky:**
- Veškerá dokumentace k těmto systémům je nyní neaktuální
- Všechny guides pro Feature Recognition jsou deprecated
- Vision Hybrid Pipeline nebude implementován (ADR-039)

---

## Archivované dokumenty

### ADRs
- `ADR-039-vision-hybrid-pipeline.md` - Vision + STEP hybrid approach (IMPLEMENTED, ale nyní DEPRECATED)

### Guides
- `FEATURE-RECOGNITION-GUIDE.md` - API guide pro FR systém
- `CONSTRAINT-DETECTION-GUIDE.md` - Manufacturing constraints detection
- `FR-HIERARCHICAL-OPERATIONS.md` - Feature → Operation mapping

### Future Plans
- `FUTURE_VISION_STEP_HYBRID.md` - Budoucí plány (již neplatné)

---

## Co zůstalo

**JEDINÝ AKTIVNÍ SYSTÉM:**
- **ADR-040:** Physics-Based Machining Time Estimation
- **Guide:** `docs/guides/MACHINING-TIME-ESTIMATION.md`
- **Service:** `app/services/machining_time_estimation_service.py`

---

**Archivováno:** 2026-02-08
**Důvod:** Simplifikace - pouze 1 time calculation systém
