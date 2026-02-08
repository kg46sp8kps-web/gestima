# Machining Time Estimation Module

UI components for displaying machining time estimation results from batch STEP file analysis.

## Components

### MachiningTimeEstimationModule.vue (150 LOC)
Main split-pane coordinator component.
- LEFT: BatchEstimationTable (sortable list)
- RIGHT: EstimationDetailPanel (selected result details)

**Usage:**
```vue
<MachiningTimeEstimationModule />
```

### BatchEstimationTable.vue (293 LOC)
Sortable table of batch estimation results.
- Sortable columns (filename, type, removal, times, constraints)
- Row selection with visual feedback
- Color-coded constraint badges

**Props:**
- `results: MachiningTimeEstimation[]` - Array of estimation results

**Events:**
- `@select: (result: MachiningTimeEstimation) => void`

### EstimationDetailPanel.vue (138 LOC)
Detail view for selected estimation result.
Composes 3 widget components:
- TimeBreakdownWidget
- GeometryInfoWidget
- ConstraintsWidget

**Props:**
- `result: MachiningTimeEstimation` - Selected estimation result

### Widget Components (< 140 LOC each)

#### TimeBreakdownWidget.vue (139 LOC)
Visual breakdown with progress bars:
- Roughing time (red)
- Finishing time (green)
- Setup time (yellow)

#### GeometryInfoWidget.vue (111 LOC)
Material and geometry information grid:
- Stock/part volume (cm³)
- Material removal (cm³ + %)
- Surface area (cm²)

#### ConstraintsWidget.vue (117 LOC)
Machining constraints display:
- Constraint multiplier badge (color-coded by severity)
- Formatted constraint list

## API Integration

### Composable: useMachiningTimeEstimation.ts (55 LOC)

```typescript
const {
  results,
  loading,
  error,
  fetchBatchResults,
  fetchSingleEstimation
} = useMachiningTimeEstimation()

await fetchBatchResults()
```

**Expected API Endpoints:**
- `GET /api/estimation/batch` → BatchEstimationResults
- `GET /api/estimation/:filename` → MachiningTimeEstimation

## Types (50 LOC)

```typescript
// frontend/src/types/estimation.ts

interface MachiningTimeEstimation {
  filename: string
  part_type: 'ROT' | 'PRI'
  roughing_time_min: number
  finishing_time_min: number
  setup_time_min: number
  total_time_min: number
  breakdown: EstimationBreakdown
}

interface EstimationBreakdown {
  material: string
  stock_volume_mm3: number
  part_volume_mm3: number
  material_to_remove_mm3: number
  material_removal_percent: number
  surface_area_mm2: number
  machining_strategy: MachiningStrategy
  critical_constraints: string[]
  constraint_multiplier: number
  pure_machining_time_min: number
}
```

## Design System Compliance

- All colors: CSS variables (`--color-primary`, `--color-success`, etc.)
- All spacing: Design tokens (`--space-4`, `--space-5`, etc.)
- Icons: Lucide + ICON_SIZE constants
- No hardcoded values
- Responsive grid layouts

## Testing

```bash
npm run test:unit useMachiningTimeEstimation
```

3 tests covering:
- Initial state
- Successful fetch
- Error handling

## LOC Summary

| Component | LOC | Status |
|-----------|-----|--------|
| MachiningTimeEstimationModule | 150 | < 300 |
| BatchEstimationTable | 293 | < 300 |
| EstimationDetailPanel | 138 | < 300 |
| TimeBreakdownWidget | 139 | < 300 |
| GeometryInfoWidget | 111 | < 300 |
| ConstraintsWidget | 117 | < 300 |
| useMachiningTimeEstimation | 55 | < 300 |
| Types | 50 | < 300 |
| **TOTAL** | **1053** | Generic-first |

All components pass L-036 validation (< 300 LOC).
