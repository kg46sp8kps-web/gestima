# Customizable Module Implementation Guide

**Version:** 1.0
**Date:** 2026-02-02
**Related:** [ADR-030: Universal Responsive Module Template](../ADR/030-universal-responsive-module-template.md)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Creating a Customizable Module](#creating-a-customizable-module)
4. [Creating Widgets](#creating-widgets)
5. [Layout Configuration](#layout-configuration)
6. [Responsive Design](#responsive-design)
7. [User Customization](#user-customization)
8. [Migration Guide](#migration-guide)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install vue-grid-layout
npm install vue-responsive-grid-layout
```

### 2. Define Module Config

```typescript
// frontend/src/config/layouts/my-module.ts
import type { ModuleLayoutConfig } from '@/types/layout'

export const myModuleConfig: ModuleLayoutConfig = {
  moduleKey: 'my-module',
  cols: 4,
  rowHeight: 80,
  widgets: [
    {
      id: 'info',
      type: 'info-card',
      title: 'Information',
      component: 'MyInfoWidget',
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 2,
      defaultHeight: 3,
      resizable: true,
      removable: false,
      required: true
    }
  ],
  defaultLayouts: {
    compact: [
      { i: 'info', x: 0, y: 0, w: 2, h: 3 }
    ],
    comfortable: [
      { i: 'info', x: 0, y: 0, w: 3, h: 4 }
    ]
  }
}
```

### 3. Create Widget Component

```vue
<!-- frontend/src/components/widgets/MyInfoWidget.vue -->
<script setup lang="ts">
interface Props {
  context?: {
    data: any
  }
}

const props = defineProps<Props>()
</script>

<template>
  <div class="my-widget">
    <h3>My Widget</h3>
    <p>{{ context?.data }}</p>
  </div>
</template>

<style scoped>
.my-widget {
  padding: var(--space-3);
}
</style>
```

### 4. Use CustomizableModule

```vue
<!-- frontend/src/components/modules/MyModule.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { myModuleConfig } from '@/config/layouts/my-module'

const data = ref({ message: 'Hello World' })

const context = computed(() => ({ data: data.value }))
</script>

<template>
  <CustomizableModule
    :config="myModuleConfig"
    :context="context"
  />
</template>
```

---

## Core Concepts

### Widget

A **widget** is a self-contained UI component that:
- Displays specific information or actions
- Can be moved, resized, shown/hidden by the user
- Communicates via props (receives `context`) and events
- Has consistent chrome (title bar, menu, drag handle)

**Example widgets:**
- Info Card (display part details)
- Action Bar (Material, Operations, Pricing buttons)
- Chart Widget (cost breakdown chart)
- Form Widget (edit mode form)

### Module Config

A **module config** defines:
- Available widgets for the module
- Default layouts (compact & comfortable density)
- Grid settings (columns, row height)

**Example:**
```typescript
const config: ModuleLayoutConfig = {
  moduleKey: 'part-detail',      // Unique module identifier
  cols: 4,                        // Number of grid columns
  rowHeight: 80,                  // Row height in px
  widgets: [...],                 // Available widget definitions
  defaultLayouts: {
    compact: [...],               // Default layout for compact mode
    comfortable: [...]            // Default layout for comfortable mode
  }
}
```

### Layout

A **layout** describes widget positions:
```typescript
const layout: WidgetLayout[] = [
  { i: 'info', x: 0, y: 0, w: 2, h: 3 },  // Info widget at (0,0), 2 cols × 3 rows
  { i: 'actions', x: 2, y: 0, w: 2, h: 1 } // Actions at (2,0), 2 cols × 1 row
]
```

Grid system:
- **x, y**: Position (0-indexed)
- **w, h**: Size in grid units (columns × rows)
- **static**: If true, cannot be moved/resized

---

## Creating a Customizable Module

### Step 1: Create Layout Config

```typescript
// frontend/src/config/layouts/part-detail.ts

import type { ModuleLayoutConfig } from '@/types/layout'

export const partDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'part-detail',
  cols: 4,
  rowHeight: 80,

  // Define available widgets
  widgets: [
    {
      id: 'part-info',
      type: 'info-card',
      title: 'Part Information',
      component: 'PartInfoCard',      // Component filename (without .vue)
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 2,
      defaultHeight: 3,
      resizable: true,
      removable: false,                // Cannot be removed (required)
      required: true
    },
    {
      id: 'part-actions',
      type: 'action-bar',
      title: 'Actions',
      component: 'PartActionsBar',
      minWidth: 2,
      minHeight: 1,
      defaultWidth: 2,
      defaultHeight: 1,
      resizable: false,                // Fixed size
      removable: false,
      required: true
    },
    {
      id: 'cost-chart',
      type: 'chart',
      title: 'Cost Breakdown',
      component: 'CostChartWidget',
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 4,
      defaultHeight: 3,
      resizable: true,
      removable: true,                 // User can remove this widget
      required: false
    }
  ],

  // Default layouts per density
  defaultLayouts: {
    compact: [
      { i: 'part-info', x: 0, y: 0, w: 2, h: 3 },
      { i: 'part-actions', x: 2, y: 0, w: 2, h: 1 },
      { i: 'cost-chart', x: 0, y: 3, w: 4, h: 3 }
    ],
    comfortable: [
      { i: 'part-info', x: 0, y: 0, w: 3, h: 4 },
      { i: 'part-actions', x: 3, y: 0, w: 1, h: 2 },
      { i: 'cost-chart', x: 0, y: 4, w: 4, h: 4 }
    ]
  }
}
```

### Step 2: Create Module Component

```vue
<!-- frontend/src/components/modules/PartDetailModule.vue -->

<script setup lang="ts">
import { computed } from 'vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { partDetailConfig } from '@/config/layouts/part-detail'
import type { Part } from '@/types/part'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
}>()

// Context passed to all widgets
const context = computed(() => ({
  part: props.part,
  linkingGroup: props.linkingGroup
}))

// Handle widget actions
function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  switch (action) {
    case 'open-material':
      emit('open-material')
      break
    case 'open-operations':
      emit('open-operations')
      break
    case 'open-pricing':
      emit('open-pricing')
      break
    case 'open-drawing':
      emit('open-drawing', payload)
      break
    default:
      console.warn('Unknown widget action:', action)
  }
}
</script>

<template>
  <CustomizableModule
    :config="partDetailConfig"
    :context="context"
    @widget-action="handleWidgetAction"
  />
</template>
```

### Step 3: With Optional Left Panel (Split-Pane)

```vue
<script setup lang="ts">
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import PartListPanel from './parts/PartListPanel.vue'
import { partDetailConfig } from '@/config/layouts/part-detail'

const selectedPart = ref<Part | null>(null)

const context = computed(() => ({
  part: selectedPart.value
}))
</script>

<template>
  <CustomizableModule
    :config="partDetailConfig"
    :context="context"
    :left-panel-component="PartListPanel"
    :left-panel-collapsible="true"
    @widget-action="handleWidgetAction"
  />
</template>
```

---

## Creating Widgets

### Widget Props Interface

All widgets receive:

```typescript
interface WidgetProps {
  context?: Record<string, any>     // Data from parent module
}
```

### Widget Events

Widgets emit:

```typescript
const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

// Usage in widget:
emit('action', 'open-material')
emit('action', 'open-drawing', { drawingId: 123 })
```

### Example: Info Card Widget

```vue
<!-- frontend/src/components/widgets/PartInfoCard.vue -->

<script setup lang="ts">
import { computed } from 'vue'
import type { Part } from '@/types/part'

interface Props {
  context?: {
    part?: Part
  }
}

const props = defineProps<Props>()

const part = computed(() => props.context?.part)

const fields = computed(() => [
  { label: 'Part Number', value: part.value?.part_number },
  { label: 'Article Number', value: part.value?.article_number },
  { label: 'Drawing Number', value: part.value?.drawing_number },
  { label: 'Name', value: part.value?.name },
  { label: 'Revision', value: part.value?.customer_revision }
])

function formatValue(value: any): string {
  return value ?? '—'
}
</script>

<template>
  <div class="info-card">
    <div v-if="!part" class="empty-state">
      <p>No part selected</p>
    </div>

    <div v-else class="fields">
      <div
        v-for="field in fields"
        :key="field.label"
        class="field"
      >
        <span class="field-label">{{ field.label }}:</span>
        <span class="field-value">{{ formatValue(field.value) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.info-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.field-value {
  font-size: var(--text-base);
  color: var(--text-body);
}
</style>
```

### Example: Action Bar Widget

```vue
<!-- frontend/src/components/widgets/PartActionsBar.vue -->

<script setup lang="ts">
import { Package, Settings, DollarSign, FileText } from 'lucide-vue-next'

interface Props {
  context?: {
    part?: any
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

const actions = [
  { id: 'material', label: 'Material', icon: Package, color: '#059669' },
  { id: 'operations', label: 'Operations', icon: Settings, color: '#2563eb' },
  { id: 'pricing', label: 'Pricing', icon: DollarSign, color: '#d97706' },
  { id: 'drawing', label: 'Drawing', icon: FileText, color: '#991b1b' }
]

function handleAction(actionId: string) {
  emit('action', `open-${actionId}`)
}
</script>

<template>
  <div class="action-bar">
    <button
      v-for="action in actions"
      :key="action.id"
      @click="handleAction(action.id)"
      class="action-button"
      :disabled="!context?.part"
    >
      <component :is="action.icon" :size="24" :color="action.color" />
      <span>{{ action.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.action-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: var(--space-2);
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
}

.action-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  transform: translateY(-1px);
}

.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-button span {
  font-size: var(--text-xs);
  color: var(--text-body);
}
</style>
```

---

## Layout Configuration

### Grid System

The grid uses a **12-column system** by default:

```typescript
cols: 12              // 12 columns
rowHeight: 60         // Each row is 60px tall

// Widget taking 3 columns × 2 rows:
{ i: 'widget-id', x: 0, y: 0, w: 3, h: 2 }
// Actual size: 3/12 width (25%) × 120px height
```

### Positioning Widgets

**X-axis (columns):**
```
0   1   2   3   4   5   6   7   8   9   10  11
|---|---|---|---|---|---|---|---|---|---|---|---|
```

**Example layouts:**

```typescript
// Full width widget
{ i: 'header', x: 0, y: 0, w: 12, h: 1 }

// Two half-width widgets side by side
{ i: 'left', x: 0, y: 0, w: 6, h: 2 },
{ i: 'right', x: 6, y: 0, w: 6, h: 2 }

// Three equal widgets
{ i: 'a', x: 0, y: 0, w: 4, h: 2 },
{ i: 'b', x: 4, y: 0, w: 4, h: 2 },
{ i: 'c', x: 8, y: 0, w: 4, h: 2 }
```

### Density-Aware Layouts

Different layouts for compact vs comfortable:

```typescript
defaultLayouts: {
  compact: [
    // Compact: More dense, smaller widgets
    { i: 'info', x: 0, y: 0, w: 6, h: 3 },
    { i: 'actions', x: 6, y: 0, w: 6, h: 2 }
  ],
  comfortable: [
    // Comfortable: More spacious, larger widgets
    { i: 'info', x: 0, y: 0, w: 8, h: 4 },
    { i: 'actions', x: 8, y: 0, w: 4, h: 3 }
  ]
}
```

The system automatically selects the correct layout based on `data-density` attribute.

---

## Responsive Design

### Container Queries

Widgets automatically adapt to their container size:

```css
/* In widget styles */
.widget-content {
  container-type: inline-size;
  container-name: widget;
}

/* Narrow: Stack vertically */
@container widget (max-width: 300px) {
  .widget-grid {
    grid-template-columns: 1fr;
  }
}

/* Wide: Multiple columns */
@container widget (min-width: 600px) {
  .widget-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

### Grid-Level Breakpoints

The grid system automatically adjusts columns:

| Container Width | Columns | Use Case |
|-----------------|---------|----------|
| < 400px | 1 | Narrow window |
| 400-600px | 2 | Tablet portrait |
| 600-900px | 3 | Tablet landscape |
| 900-1200px | 4 | Desktop |
| > 1200px | 6 | Ultrawide (max-width: 1600px) |

**Implementation:** Uses container queries in `_grid-layout.css`

---

## User Customization

### Features

Users can:
- **Drag** widgets to reposition
- **Resize** widgets (if `resizable: true`)
- **Add** widgets from palette (if `removable: true` on widget def)
- **Remove** widgets (if `removable: true`)
- **Reset** to default layout
- **Export** layout (JSON file)
- **Import** layout (JSON file)

### localStorage Persistence

Layouts are automatically saved:

```typescript
// Saved to localStorage:
localStorage.setItem('part-detail-grid-layout', JSON.stringify(layouts))

// Loaded on mount:
const saved = localStorage.getItem('part-detail-grid-layout')
if (saved) {
  layouts.value = JSON.parse(saved)
}
```

**Key format:** `${moduleKey}-grid-layout`

### Export/Import

```vue
<!-- In module toolbar -->
<button @click="exportLayout">
  Export Layout
</button>

<button @click="importLayout">
  Import Layout
</button>

<script>
function exportLayout() {
  const data = {
    moduleKey: 'part-detail',
    layouts: layouts.value,
    version: 1
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json'
  })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `part-detail-layout.json`
  a.click()
}

async function importLayout() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'

  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return

    const text = await file.text()
    const data = JSON.parse(text)

    updateLayout(data.layouts)
  }

  input.click()
}
</script>
```

---

## Migration Guide

### Migrating an Existing Module

**Example:** Migrate PartDetailPanel (454 LOC) to widget-based (< 100 LOC)

#### Step 1: Analyze Current Module

```vue
<!-- BEFORE: PartDetailPanel.vue (454 LOC) -->
<template>
  <div class="part-detail-panel">
    <!-- Part header (100 LOC) -->
    <div class="part-header">...</div>

    <!-- Action buttons (80 LOC) -->
    <div class="actions-grid">...</div>

    <!-- Modals (200 LOC) -->
    <DrawingsManagementModal ... />
    <CopyPartModal ... />
  </div>
</template>
```

**Identify widgets:**
1. Part header → `PartInfoCard.vue` widget (80 LOC)
2. Actions grid → `PartActionsBar.vue` widget (60 LOC)
3. Modals → Stay in module (not widgets)

#### Step 2: Create Widget Components

```bash
# Create widget files
touch frontend/src/components/widgets/PartInfoCard.vue
touch frontend/src/components/widgets/PartActionsBar.vue
```

Extract logic from original panel into widgets.

#### Step 3: Create Layout Config

```typescript
// frontend/src/config/layouts/part-detail.ts
export const partDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'part-detail',
  cols: 4,
  rowHeight: 80,
  widgets: [
    {
      id: 'part-info',
      type: 'info-card',
      title: 'Part Information',
      component: 'PartInfoCard',
      defaultWidth: 2,
      defaultHeight: 3,
      required: true
    },
    {
      id: 'part-actions',
      type: 'action-bar',
      title: 'Actions',
      component: 'PartActionsBar',
      defaultWidth: 2,
      defaultHeight: 1,
      required: true
    }
  ],
  defaultLayouts: {
    compact: [
      { i: 'part-info', x: 0, y: 0, w: 2, h: 3 },
      { i: 'part-actions', x: 2, y: 0, w: 2, h: 1 }
    ],
    comfortable: [
      { i: 'part-info', x: 0, y: 0, w: 3, h: 4 },
      { i: 'part-actions', x: 3, y: 0, w: 1, h: 2 }
    ]
  }
}
```

#### Step 4: Migrate Module

```vue
<!-- AFTER: PartDetailPanel.vue (< 100 LOC) -->
<script setup lang="ts">
import { computed } from 'vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { partDetailConfig } from '@/config/layouts/part-detail'
import type { Part } from '@/types/part'

interface Props {
  part: Part
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
}>()

const context = computed(() => ({
  part: props.part
}))

function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  switch (action) {
    case 'open-material': emit('open-material'); break
    case 'open-operations': emit('open-operations'); break
    case 'open-pricing': emit('open-pricing'); break
    case 'open-drawing': emit('open-drawing', payload); break
  }
}
</script>

<template>
  <CustomizableModule
    :config="partDetailConfig"
    :context="context"
    @widget-action="handleWidgetAction"
  />
</template>
```

**Result:** 454 LOC → 80 LOC (82% reduction!)

#### Step 5: Test Migration

```bash
# Run existing tests
npm run test -- PartDetailPanel.spec.ts

# Manual testing:
# ✓ Part info displayed correctly
# ✓ Action buttons work
# ✓ Widgets draggable
# ✓ Layout persists
```

---

## Best Practices

### 1. Widget Size Guidelines

- **Minimum width:** 2 columns (for readability)
- **Minimum height:** 1 row (for title bar)
- **Recommended:** 2-4 columns × 2-3 rows
- **Maximum:** Avoid full-width unless necessary

### 2. Widget Independence

```typescript
// ❌ BAD: Widget directly accesses store
const partsStore = usePartsStore()
const part = partsStore.parts[0]

// ✅ GOOD: Widget receives data via props
const props = defineProps<{ context?: { part: Part } }>()
const part = computed(() => props.context?.part)
```

### 3. Action Emitting

```typescript
// ❌ BAD: Widget calls module method directly
function openMaterial() {
  parent.openMaterialWindow() // Tight coupling!
}

// ✅ GOOD: Widget emits action
const emit = defineEmits<{ 'action': [string, any?] }>()
emit('action', 'open-material')
```

### 4. Responsive Design

```css
/* ✅ GOOD: Use container queries */
@container widget (max-width: 300px) {
  .widget-content { flex-direction: column; }
}

/* ❌ BAD: Use media queries */
@media (max-width: 768px) {
  .widget-content { flex-direction: column; }
}
```

### 5. Design Tokens

```css
/* ✅ GOOD: Use design tokens */
padding: var(--space-3);
color: var(--text-body);
border: 1px solid var(--border-default);

/* ❌ BAD: Hardcoded values */
padding: 12px;
color: #f5f5f5;
border: 1px solid #2a2a2a;
```

---

## Troubleshooting

### Layout Not Saving

**Problem:** User customization not persisting

**Solution:**
1. Check localStorage key: `${moduleKey}-grid-layout`
2. Verify `moduleKey` is unique
3. Check browser localStorage quota (5-10MB)
4. Ensure `updateLayout()` is called on drag/resize

### Widget Not Loading

**Problem:** "Widget not found" error

**Solution:**
1. Check component name matches `component` field in config
2. Verify widget file exists: `frontend/src/components/widgets/${component}.vue`
3. Check for typos in component name
4. Ensure widget is exported correctly

### Container Queries Not Working

**Problem:** Layout not responsive

**Solution:**
1. Check browser support (Chrome 105+, Firefox 110+)
2. Verify `container-type: inline-size` is set
3. Check `container-name` matches query
4. Inspect with DevTools → Container queries

### Drag & Drop Not Working

**Problem:** Cannot drag widgets

**Solution:**
1. Check `isDraggable` prop is true in GridLayout
2. Verify widget has `draggable` attribute
3. Check for CSS `pointer-events: none`
4. Ensure vue-grid-layout is installed

---

## Example: Complete Module Migration

See [MIGRATION-CHECKLIST.md](MIGRATION-CHECKLIST.md) for detailed step-by-step checklist.

---

**Next Steps:**
- Read [ADR-030](../ADR/030-universal-responsive-module-template.md) for architectural decisions
- Check [Widget API Reference](../reference/WIDGET-API.md) for full API docs
- Review [Migration Checklist](MIGRATION-CHECKLIST.md) for per-window guide

---

**Version:** 1.0
**Last Updated:** 2026-02-02
**Status:** ✅ Production Ready
