# PHASE 2-6 HANDOFF PROMPT (for New Chat)

**Use this prompt to continue ML Time Estimation implementation in a new chat session.**

---

## 📋 COPY THIS PROMPT INTO NEW CHAT:

```
Pokračuji v implementaci ML Time Estimation systému — Phase 2-6.

PHASE 1 (HOTOVO v předchozím chatu):
✅ Feature Extraction Service (60+ geometric features from STEP files)
✅ GeometryFeatures Pydantic schema
✅ Tests passing (12/12)
✅ Documentation (FEATURE-EXTRACTION-DESIGN.md)

CO POTŘEBUJI TEĎKA (Phase 2-6):

PHASE 2: Database Models + Migration
- app/models/turning_estimation.py (60+ feature columns + estimates + ground truth)
- app/models/milling_estimation.py (same structure, part_type="PRI")
- Migration: alembic/versions/XXX_turning_milling_estimations.py
- Seed script: scripts/batch_extract_features_37_parts.py
  → Process 37 STEP files in uploads/drawings/
  → Auto-classify ROT (očekávám 16) vs PRI (očekávám 21) pomocí rotational_score
  → Insert do DB s extracted features

PHASE 3: Backend Router (API Endpoints)
- app/routers/estimation_router.py (6 endpoints):
  1. POST /api/estimation/extract-features/{filename}
  2. GET /api/estimation/pending-estimates?part_type=ROT
  3. PATCH /api/estimation/manual-estimate/{id}
  4. POST /api/estimation/import-actual-times (CSV import)
  5. GET /api/estimation/export-training-data?part_type=ROT
  6. GET /api/estimation/similar-parts/{id}?limit=5

PHASE 4: Frontend UI (Manual Estimation Module)
- ManualEstimationListModule.vue (split-pane: LEFT list, RIGHT details+form)
- Tabs: "Turning Parts" | "Milling Parts"
- Feature details panel (key features only, ne všech 60)
- Estimate form (input time → save)
- Similar parts list (top 3-5 by feature distance)
- Export training data button (CSV download)

PHASE 5: Batch Validation
- Spustit seed script na 37 souborech
- Validace: ROT/PRI klasifikace, volume conservation, extraction errors
- Report: processing time, error count, feature spot-check

PHASE 6: Documentation
- docs/ADR/041-ml-time-estimation-architecture.md
- docs/guides/MANUAL-ESTIMATION-GUIDE.md
- CHANGELOG.md update

CONTEXT FILES (přečti si PŘED začátkem):
- docs/phase1/PHASE1-COMPLETION-REPORT.md (co bylo hotovo v Phase 1)
- docs/phase1/FEATURE-EXTRACTION-DESIGN.md (feature engineering design)
- app/services/geometry_feature_extractor.py (existující service)
- app/schemas/geometry_features.py (existující schema)

KRITICKÉ POŽADAVKY:
1. Separate models pro turning vs milling (2 DB tables, 2 Pydantic schemas)
2. Auto-detection: rotational_score > 0.6 → TurningEstimation, else → MillingEstimation
3. L-008 compliance (try/except/rollback v routerech)
4. L-009 compliance (Pydantic Field() validation)
5. L-036 compliance (Vue komponenty <300 LOC)
6. Volume conservation validation (<1% error) v batch scriptu

ŠÉFÍK MODE:
Aktivuj ŠÉFÍKA pro multi-agent orchestraci:
- DevOps Agent: Phase 2 (DB models + migration + seed)
- Backend Agent: Phase 3 (router + endpoints)
- Frontend Agent: Phase 4 (UI module)
- QA Agent: Phase 5 (batch validation)
- Backend Agent: Phase 6 (documentation)

DELIVERABLES:
- 8+ nových souborů (models, router, Vue components, migration, seed, docs)
- ~2,000 LOC (backend + frontend)
- 37 DB records (features extracted, pending manual estimates)
- ADR-041 + estimation guide

ACCEPTANCE CRITERIA:
✅ 37 STEP files processed bez chyb
✅ 16 turning_estimations + 21 milling_estimations v DB
✅ All 60 feature columns populated
✅ Frontend UI shows 2 tabs (Turning | Milling)
✅ Manual estimate form funguje (save → DB update)
✅ Export CSV button → training data download
✅ Documentation complete (ADR + guide)

TOKEN ESTIMATE: 90k-110k (máš 200k available → OK)
TIME ESTIMATE: 3-4 hours

START s Phase 2 (Database Models). Ptej se, pokud něco není jasné.
```

---

## 🔗 ADDITIONAL CONTEXT (for reference)

**Feature Schema Location:**
- File: `app/schemas/geometry_features.py`
- Model: `GeometryFeatures` (60+ fields)
- Import: `from app.schemas.geometry_features import GeometryFeatures`

**Feature Extractor Usage:**
```python
from app.services.geometry_feature_extractor import GeometryFeatureExtractor
from pathlib import Path

extractor = GeometryFeatureExtractor()
features = extractor.extract_features(
    step_path=Path("uploads/drawings/JR811181.step"),
    material_code="20910000"  # Ocel automatová
)

# features = GeometryFeatures instance (60+ fields)
# features.part_type = "ROT" or "PRI" (auto-detected)
# features.rotational_score = 0.0-1.0
# features.part_volume_mm3, features.surface_area_mm2, etc.
```

**Material Codes (from existing DB):**
```
20910000 - Ocel automatová
20910001 - Ocel konstrukční
20910002 - Ocel legovaná
20910003 - Ocel nástrojová
20910004 - Nerez
20910005 - Hliník
20910006 - Měď
20910007 - Mosaz
20910008 - Plasty
```

**STEP Files Location:**
```
/Users/lofas/Documents/__App_Claude/Gestima/uploads/drawings/
```

**37 STEP files (from batch):**
- Expected: 16 ROT parts, 21 PRI parts
- All files have PDF mappings (step_pdf_mapping.json)
- File format: mixed (*.step, *.stp, *.STEP)

**Database Models Pattern:**
```python
# Example structure (adapt for TurningEstimation):
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class TurningEstimation(Base):
    __tablename__ = "turning_estimations"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    part_type = Column(String, default="ROT")  # Fixed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # === 60 Feature Columns (from GeometryFeatures) ===
    part_volume_mm3 = Column(Float, nullable=False)
    stock_volume_mm3 = Column(Float, nullable=False)
    # ... (all 60 features)

    # === Manual Estimate ===
    estimated_time_min = Column(Float, nullable=True)
    estimated_by = Column(String, default="manual")
    estimated_at = Column(DateTime, nullable=True)

    # === Ground Truth ===
    actual_time_min = Column(Float, nullable=True)
    actual_time_source = Column(String, nullable=True)
    actual_time_recorded_at = Column(DateTime, nullable=True)

    # === ML Prediction (future) ===
    predicted_time_min = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    predicted_at = Column(DateTime, nullable=True)

    # === Relationships ===
    material_group_id = Column(Integer, ForeignKey("material_groups.id"))
```

**Router Pattern (L-008 compliant):**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.schemas.estimation import EstimationCreate, EstimationResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/estimation", tags=["estimation"])

@router.post("/extract-features/{filename}", response_model=EstimationResponse)
async def extract_features(
    filename: str,
    db: Session = Depends(get_db)
):
    try:
        # Extract features
        extractor = GeometryFeatureExtractor()
        features = extractor.extract_features(...)

        # Create DB record
        if features.part_type == "ROT":
            estimation = TurningEstimation(**features.dict())
        else:
            estimation = MillingEstimation(**features.dict())

        db.add(estimation)
        db.commit()
        db.refresh(estimation)

        return estimation

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        db.rollback()
        logger.error(f"Feature extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Frontend Module Pattern:**
```vue
<!-- ManualEstimationListModule.vue -->
<template>
  <div class="split-pane-container">
    <div class="left-pane">
      <ManualEstimationListPanel
        :estimations="estimations"
        :selected-id="selectedId"
        @select="handleSelect"
      />
    </div>
    <div class="right-pane">
      <ManualEstimationDetailPanel
        v-if="selectedEstimation"
        :estimation="selectedEstimation"
        @save="handleSaveEstimate"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEstimationStore } from '@/stores/estimation'

const estimationStore = useEstimationStore()
const selectedId = ref<number | null>(null)

const estimations = computed(() => estimationStore.pendingEstimations)
const selectedEstimation = computed(() =>
  estimations.value.find(e => e.id === selectedId.value)
)

onMounted(async () => {
  await estimationStore.fetchPendingEstimations('ROT')
})

function handleSelect(id: number) {
  selectedId.value = id
}

async function handleSaveEstimate(data: { id: number, time_min: number }) {
  await estimationStore.saveManualEstimate(data.id, data.time_min)
}
</script>
```

---

## ⚠️ IMPORTANT NOTES FOR PHASE 2-6

### **1. GeometryFeatures → DB Columns Mapping**

All 60+ fields from `GeometryFeatures` schema MUST become columns in `TurningEstimation` and `MillingEstimation` tables.

**Auto-generation tip:**
```python
# Generate column definitions from GeometryFeatures
from app.schemas.geometry_features import GeometryFeatures

for field_name, field_info in GeometryFeatures.model_fields.items():
    field_type = field_info.annotation
    # Convert Python type → SQLAlchemy Column
    # Example: float → Column(Float, nullable=False)
```

### **2. Batch Seed Script Structure**

```python
# scripts/batch_extract_features_37_parts.py

from pathlib import Path
from app.services.geometry_feature_extractor import GeometryFeatureExtractor
from app.models.turning_estimation import TurningEstimation
from app.models.milling_estimation import MillingEstimation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Sync DB session (OCCT is sync)
engine = create_engine("sqlite:///./gestima.db")
Session = sessionmaker(bind=engine)

drawings_dir = Path("uploads/drawings")
step_files = list(drawings_dir.glob("*.step")) + \
             list(drawings_dir.glob("*.stp")) + \
             list(drawings_dir.glob("*.STEP"))

extractor = GeometryFeatureExtractor()
session = Session()

for step_file in step_files:
    try:
        features = extractor.extract_features(step_file, "20910000")

        # Auto-classify
        if features.part_type == "ROT":
            estimation = TurningEstimation(**features.dict())
        else:
            estimation = MillingEstimation(**features.dict())

        session.add(estimation)
        session.commit()

        print(f"✅ {step_file.name} → {features.part_type}")
    except Exception as e:
        session.rollback()
        print(f"❌ {step_file.name} → ERROR: {e}")

session.close()
```

### **3. Similar Parts Algorithm**

**Euclidean distance in normalized feature space:**

```python
import numpy as np
from sklearn.preprocessing import StandardScaler

def find_similar_parts(target_id, estimations, limit=5):
    """
    Find similar parts based on feature distance.

    Features used for similarity (20 most important):
    - part_volume_mm3
    - removal_ratio
    - surface_area_mm2
    - cylindrical_surface_ratio
    - face_count
    - bbox_z_mm
    - ... (top 20 from feature importance)
    """
    # Extract feature vectors
    feature_names = [
        "part_volume_mm3", "removal_ratio", "surface_area_mm2",
        "cylindrical_surface_ratio", "face_count", "bbox_z_mm"
        # ... (add more)
    ]

    X = np.array([[getattr(e, f) for f in feature_names] for e in estimations])

    # Normalize
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(X)

    # Target vector
    target_idx = next(i for i, e in enumerate(estimations) if e.id == target_id)
    target_vec = X_norm[target_idx]

    # Euclidean distances
    distances = np.linalg.norm(X_norm - target_vec, axis=1)

    # Top K similar (excluding self)
    similar_indices = np.argsort(distances)[1:limit+1]

    return [
        {
            "estimation": estimations[i],
            "similarity_score": 1.0 / (1.0 + distances[i]),  # 0.0-1.0
            "distance": distances[i]
        }
        for i in similar_indices
    ]
```

### **4. Export Training Data CSV Format**

```csv
filename,part_type,part_volume_mm3,stock_volume_mm3,removal_ratio,surface_area_mm2,cylindrical_surface_ratio,rotational_score,face_count,edge_count,bbox_x_mm,bbox_y_mm,bbox_z_mm,material_group_code,estimated_time_min,actual_time_min
JR811181.step,ROT,8900.0,15000.0,0.58,3200.0,0.68,0.72,45,252,35.0,35.0,120.0,20910000,52.5,
3DM_90057637.step,ROT,12500.0,18000.0,0.31,2800.0,0.72,0.78,38,198,40.0,40.0,95.0,20910000,38.5,41.2
```

**Columns:**
- Metadata: filename, part_type
- Key features (20 most important, not all 60)
- Material: material_group_code
- Targets: estimated_time_min (manual), actual_time_min (ground truth)

**Usage:** This CSV is input for XGBoost training (Phase 7, future chat)

---

## 🎯 SUCCESS CRITERIA (Phase 2-6)

**When Phase 2-6 is COMPLETE, you should have:**

✅ **Database:**
- 2 tables: `turning_estimations` (16 rows), `milling_estimations` (21 rows)
- All 60 feature columns populated
- `estimated_time_min = NULL` (waiting for user input)

✅ **Backend:**
- 6 API endpoints functional
- Feature extraction endpoint works
- Manual estimate PATCH endpoint works
- Export CSV endpoint returns training data

✅ **Frontend:**
- ManualEstimationListModule visible in UI
- 2 tabs: Turning (16) | Milling (21)
- Click part → shows feature details
- Estimate form → saves to DB
- Export button → downloads CSV

✅ **Validation:**
- Batch script processes 37 files without errors
- ROT/PRI classification: 16/21 split (verify on complex parts)
- Volume conservation: all <1% error
- No extraction failures

✅ **Documentation:**
- ADR-041 complete (~400 lines)
- Manual estimation guide complete (~200 lines)
- CHANGELOG updated

---

## 📞 QUESTIONS TO ASK USER (during Phase 2-6)

**Before Phase 2 (DB Models):**
- "GeometryFeatures has 60+ fields. Should I create 60+ columns in DB, or store as JSONB?"
  - Recommendation: Individual columns (better for SQL queries, feature importance analysis)

**Before Phase 4 (Frontend UI):**
- "Which 10-15 features to show in detail panel? (All 60 is too much)"
  - Recommendation: part_volume, removal_ratio, surface_area, cylindrical_ratio, face_count, bbox dimensions, material

**Before Phase 6 (Documentation):**
- "Manual estimation guide — what time ranges are typical for your parts?"
  - User knows his domain, you don't (turning: 20-80 min? milling: 40-120 min?)

---

## 🔄 WHEN TO PAUSE FOR USER REVIEW

**Checkpoint 1: After Phase 2 (DB + Seed)**
- Show: "37 records created, 16 ROT, 21 PRI. Volume conservation: all <1% error. Continue to Phase 3?"

**Checkpoint 2: After Phase 4 (Frontend)**
- Show: Screenshot or description of UI
- "Frontend module complete. Manual estimation form works. Continue to Phase 5?"

**Checkpoint 3: After Phase 6 (Documentation)**
- Show: "All phases complete. Documentation ready. Ready to commit?"

---

**END OF HANDOFF PROMPT**

Copy the prompt above (from "Pokračuji v implementaci..." to "...Ready to commit?") into a new chat to continue Phase 2-6.
