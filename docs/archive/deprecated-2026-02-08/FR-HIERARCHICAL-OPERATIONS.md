# Feature Recognition - Hierarchical Operations Display

**Status:** Components ready, integration pending
**Date:** 2026-02-05

## Overview

Replace flat operations table with hierarchical OP10/OP20 groups with expandable features.

## Components Created

1. `FeatureRow.vue` (158 LOC) - Single feature display with checkbox
2. `OperationGroupHeader.vue` (136 LOC) - Collapsible header for OP10, OP20, etc.
3. `OperationGroupsDisplay.vue` (252 LOC) - Container orchestrating groups + features

## Types Updated

`frontend/src/types/featureRecognition.ts`:
- Added `FeatureSuggestion` interface
- Added `OperationGroup` interface
- Added `operation_groups?: OperationGroup[]` to `FeatureRecognition`

## Integration Required

### 1. Update FeatureRecognitionModule.vue

**Add import (line ~27):**
```typescript
import OperationGroupsDisplay from './featureRecognition/OperationGroupsDisplay.vue'
```

**Add transfer handler (after `saveToPartViaPinia`, line ~336):**
```typescript
async function transferOperationToPart(group: OperationGroup, selectedFeatures: FeatureSuggestion[]) {
  if (!contextPartId.value) {
    uiStore.showWarning('Není nalinkovaný díl')
    return
  }

  saving.value = true
  try {
    await featureRecognitionApi.applyOperationToPart(contextPartId.value, {
      setup_id: group.setup_id,
      description: group.description,
      features: selectedFeatures
    })
    uiStore.showSuccess(`${group.setup_id} přeneseno (${selectedFeatures.length} features)`)
  } catch (err) {
    uiStore.showError('Přenos selhal')
  } finally {
    saving.value = false
  }
}
```

**Replace DataTable (lines 718-757):**
```vue
<!-- Hierarchical display if operation_groups exist -->
<OperationGroupsDisplay
  v-if="analysis.operation_groups?.length > 0"
  :groups="analysis.operation_groups"
  @transfer="transferOperationToPart"
/>

<!-- Flat table (backward compat) -->
<DataTable v-else :data="operations" ... />
```

### 2. Backend API Endpoint

**File:** `app/routers/feature_recognition_router.py`

**Add:**
```python
@router.post("/api/feature-recognition/apply-operation/{part_id}")
async def apply_operation_to_part(
    part_id: int,
    operation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Apply single operation group (OP10) to part - creates operations from features"""
    # Create operations from features in operation_data["features"]
    pass
```

### 3. Backend FR Service

Update `feature_recognition_ml_service.py` to return `operation_groups` from `setup_planner.py`.

## Expected UX

1. Upload STEP + PDF
2. Backend returns `operation_groups: [{setup_id: "OP10", features: [...]}]`
3. Frontend displays:
   - OP10 header (click to expand)
   - Features list with checkboxes
   - "Přenést do operací dílu (N)" button
4. User selects 3 features, clicks button
5. Backend creates 3 operations in Part

## Testing

```bash
# Upload test file
curl -F "step_file=@test.stp" -F "pdf_file=@test.pdf" /api/feature-recognition/analyze

# Verify response has operation_groups
# Verify frontend displays hierarchical UI
# Verify feature selection works
# Verify transfer creates operations
```

## Files

- `frontend/src/components/modules/featureRecognition/OperationGroupHeader.vue`
- `frontend/src/components/modules/featureRecognition/FeatureRow.vue`
- `frontend/src/components/modules/featureRecognition/OperationGroupsDisplay.vue`

## Next Steps

1. Apply template changes to FeatureRecognitionModule.vue
2. Implement backend `applyOperationToPart` endpoint
3. Update FR service to return `operation_groups`
4. E2E test

---

**Note:** FeatureRecognitionModule.vue is 1614 LOC. Consider splitting before further changes.
