# Hybrid Layout Solution - Simple Guide

**Date:** 2026-02-02
**Status:** ✅ Final Solution
**Problem:** Widgety v Manufacturing Items modulu nevyplňují vertikální prostor

---

## 🔴 PROBLÉM

### Co nefunguje:

```
Manufacturing Items Detail:
┌─────────────────────┐
│ Info Widget         │ ← 360px FIXED
│ (6 rows × 60px)     │
├─────────────────────┤
│ Actions Widget      │ ← 240px FIXED
│ (4 rows × 60px)     │
└─────────────────────┘
     ↓
   PRÁZDNÉ MÍSTO!  ← Nevyplní zbytek!
```

**Uživatel chce:** Widgety mají vyplnit **CELOU výšku** v poměru 60%/40%, ne mít fixní výšku!

### Proč to nefunguje?

**GridStack.js používá FIXNÍ výšku řádků:**
```typescript
rowHeight: 60,  // Každý row = 60px FIXED
h: 6            // Widget = 6 rows = 360px FIXED
```

❌ Fixed rows NEMOHOU vyplnit dynamickou výšku okna!

### Co zkoušeli jsme:
1. ❌ `rowHeight: '10%'` → Katastrofa (Info widget zabral celou výšku)
2. ❌ `sizeToContent` → Zmenšuje widgety, ne zvětšuje!
3. ❌ Remove `height: 100%` → Widgety příliš malé
4. ❌ Dynamic cellHeight → Příliš složité, hack

**Zjištění:** GridStack je stavěný **POUZE** pro horizontal responsiveness, **NE** pro vertical fill!

---

## ✅ ŘEŠENÍ

### Hybrid Approach: Flexbox + GridStack

**Použij SPRÁVNÝ nástroj pro každý úkol:**

```typescript
// VERTICAL MODE (compact) → Flexbox
if (orientation === 'vertical') {
  use FlexLayoutArea  // Native CSS flex: 1 → vyplní prostor!
}

// HORIZONTAL MODE (comfortable) → GridStack
if (orientation === 'horizontal') {
  use GridLayoutArea  // Drag & drop funguje perfektně!
}
```

**Proč to funguje:**
- **Flexbox:** Perfektní pro vertical stacking s `flex: 1` (fill)
- **GridStack:** Perfektní pro horizontal drag & drop grid

---

## 📦 CO MÁME (Dependencies)

### Knihovny:
```json
{
  "gridstack": "^12.4.2",          // GridStack.js (MIT, 8.7k⭐)
  "lucide-vue-next": "^0.462.0",   // Lucide ikony
  "vue": "^3.5.13",                // Vue 3
  "pinia": "^2.2.6",               // State management
  "vue-router": "^4.5.0"           // Routing
}
```

### Komponenty (EXISTUJÍCÍ):
- ✅ `CustomizableModule.vue` - Module coordinator
- ✅ `GridLayoutArea.vue` - GridStack wrapper
- ✅ `WidgetWrapper.vue` - Widget chrome (header, border, etc.)
- ✅ `ManufacturingItemInfoWidget.vue` - Info widget
- ✅ `ManufacturingItemActionsWidget.vue` - Actions widget

### Ikony (Lucide):
```typescript
import { Package, Edit, Settings, DollarSign, FileText } from 'lucide-vue-next'
```

---

## 🛠️ CO POTŘEBUJEME (Implementace)

### 1. Nová komponenta: FlexLayoutArea.vue

**Účel:** Vertical stacking s flex ratios (místo GridStack fixed rows)

**Lokace:** `frontend/src/components/layout/FlexLayoutArea.vue`

**Funkce:**
- Display: `flex-direction: column`
- Widgets: `flex: 6` (60%), `flex: 4` (40%)
- Vyplní 100% výšky automaticky
- Jednoduchý, žádné složitosti

### 2. Update: CustomizableModule.vue

**Změna:** Switch mezi FlexLayoutArea (vertical) a GridLayoutArea (horizontal)

```vue
<template>
  <!-- VERTICAL MODE: Use Flexbox -->
  <FlexLayoutArea v-if="orientation === 'vertical'" ... />

  <!-- HORIZONTAL MODE: Use GridStack -->
  <GridLayoutArea v-else-if="orientation === 'horizontal'" ... />
</template>
```

### 3. Update: manufacturing-items-detail.ts config

**Přidat flex constraints:**
```typescript
widgets: [
  {
    id: 'manufacturing-item-info',
    flex: 6,           // 60% výšky
    minHeight: 120,    // Minimum 120px
    // ... rest
  },
  {
    id: 'manufacturing-item-actions',
    flex: 4,           // 40% výšky
    minHeight: 100,    // Minimum 100px
    // ... rest
  }
]
```

### 4. Update: widget.ts types

**Přidat flex support:**
```typescript
export interface WidgetLayout {
  i: string

  // Grid-based (GridStack)
  x?: number
  y?: number
  w?: number
  h?: number

  // Flex-based (Flexbox) - NEW!
  flex?: number        // Flex ratio
  minHeight?: number   // Min height in px
  maxHeight?: number   // Max height in px

  static?: boolean
}
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Step 1: Create FlexLayoutArea.vue (30 min)
```vue
<script setup lang="ts">
// Simple flex layout - no drag & drop, just vertical stack
const props = defineProps<{
  layouts: WidgetLayout[]
  gap?: number
}>()
</script>

<template>
  <div class="flex-layout" :style="{ gap: `${gap}px` }">
    <div
      v-for="layout in layouts"
      :key="layout.i"
      :style="{
        flex: `${layout.flex || 1} 1 auto`,
        minHeight: layout.minHeight ? `${layout.minHeight}px` : undefined
      }"
    >
      <slot name="widget" :widget="layout" />
    </div>
  </div>
</template>

<style scoped>
.flex-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: var(--space-3);
}
</style>
```

### Step 2: Update CustomizableModule.vue (15 min)
```vue
<script setup>
import FlexLayoutArea from './FlexLayoutArea.vue'  // NEW import

const useFlexLayout = computed(() => props.orientation === 'vertical')
const useGridLayout = computed(() => props.orientation === 'horizontal')
</script>

<template>
  <div class="customizable-module">
    <!-- Vertical: Flexbox -->
    <FlexLayoutArea v-if="useFlexLayout" ... />

    <!-- Horizontal: GridStack -->
    <GridLayoutArea v-else-if="useGridLayout" ... />
  </div>
</template>
```

### Step 3: Update widget.ts types (10 min)
```typescript
// Add flex fields to WidgetLayout
export interface WidgetLayout {
  // ... existing fields
  flex?: number
  minHeight?: number
  maxHeight?: number
}
```

### Step 4: Update manufacturing-items-detail.ts (10 min)
```typescript
widgets: [
  {
    id: 'manufacturing-item-info',
    flex: 6,  // NEW
    minHeight: 120,  // NEW
    // ... rest unchanged
  }
]
```

### Step 5: Test (15 min)
1. Open Manufacturing Items window
2. Resize window height → widgets fill 100%
3. Switch to comfortable mode → GridStack works
4. No regressions

**TOTAL TIME: ~1.5 hours**

---

## ✅ SUCCESS CRITERIA

### Functional:
- [ ] Widgets fill 100% vertical space (no empty space below)
- [ ] Ratio: Info 60%, Actions 40%
- [ ] Responsive to window resize
- [ ] Borders always visible
- [ ] Switch to comfortable mode works (GridStack)

### Technical:
- [ ] FlexLayoutArea.vue < 100 LOC
- [ ] No GridStack dependency in vertical mode
- [ ] Type-safe (TypeScript)
- [ ] No regressions in existing modules

### Performance:
- [ ] Render time < 5ms
- [ ] 60fps smooth resize
- [ ] No layout shifts

---

## 🎯 SUMMARY

### Problem:
GridStack fixed rows don't fill vertical space

### Solution:
Use Flexbox for vertical (fills space), GridStack for horizontal (drag & drop)

### Implementation:
1. Create FlexLayoutArea.vue (simple flex column)
2. Update CustomizableModule (switch logic)
3. Update types (add flex fields)
4. Update config (add flex values)

### Time:
~1.5 hours

### Result:
Widgets fill 100% height proportionally ✅

---

**JEDNODUCHÉ. FUNKČNÍ. HOTOVO.**

---

## 🔍 DETAILNÍ HISTORIE (Co jsme zkoušeli)

### Pokus 1: Percentage-based rowHeight ❌
```typescript
rowHeight: '10%'  // Myšlenka: 10 rows × 10% = 100% výšky
```
**Výsledek:** KATASTROFA!
- Info widget zabral 100% výšky
- Actions widget kompletně mimo obrazovku (neviditelný)
- GridStack nepodporuje percentage row heights

### Pokus 2: sizeToContent feature ❌
```typescript
sizeToContent: true  // GridStack auto-resize feature
```
**Výsledek:** Špatný přístup!
- sizeToContent ZMENŠUJE widgety na obsah (shrink behavior)
- User chce ZVĚTŠIT widgety (fill behavior)
- Opačný problém než potřebujeme

### Pokus 3: Remove height: 100% ❌
```css
.widget-wrapper {
  /* height: 100%; REMOVED */
  min-height: 0;
}
```
**Výsledek:** Widgety příliš malé!
- Widgety se zmenšily na minimum
- Spodní border ořezán (overflow)
- Lepší než předtím, ale stále špatně

### Pokus 4: Dynamic cellHeight calculation ❌
```typescript
const cellHeight = containerHeight / totalRows
grid.cellHeight(cellHeight)
```
**Výsledek:** Příliš složité!
- Musíš watch container resize
- Recalculate při každé změně
- Bojuješ proti library design
- Hack, ne řešení

### Pokus 5: Trigger resize manually ❌
```typescript
watch(() => props.context, () => {
  nextTick(() => {
    gridRef.value?.triggerResize()
  })
}, { deep: true })
```
**Výsledek:** Neřeší problém!
- Resize trigger funguje pro sizeToContent
- Ale my chceme fill, ne shrink
- Chybí import nextTick (další bug)
- Špatný směr řešení

---

## 💡 KLÍČOVÉ ZJIŠTĚNÍ

### Proč TemplateModule fungoval?

```vue
<!-- TemplateModule.vue - BEZ GridStack! -->
<div class="split-layout" style="display: flex; flex-direction: column;">
  <div class="first-panel" :style="{ height: `${panelSize}px` }">
    <!-- Fixed height panel -->
  </div>
  <div class="second-panel" style="flex: 1;">
    <!-- FILLS REMAINING SPACE! Native CSS Flexbox! -->
  </div>
</div>
```

**Odpověď:** TemplateModule NEPOUŽÍVÁ GridStack! Používá **native CSS Flexbox**!

**Insight:** Flexbox má nativní `flex: 1` (fill remaining space), GridStack má fixed-height rows.

---

## 🎯 COMPLETE SOLUTION (All Phases)

### Phase 1: Basic Hybrid Layout (1.5 hours) - MUST HAVE

**Deliverables:**
1. ✅ FlexLayoutArea.vue component
2. ✅ CustomizableModule.vue hybrid logic
3. ✅ widget.ts type updates (flex fields)
4. ✅ manufacturing-items-detail.ts config updates

**Result:** Widgets fill 100% height proportionally (60%/40%)

---

### Phase 2: Visual Editor (3-4 hours) - NICE TO HAVE

**Features:**

#### 1. Edit Mode Toggle
```vue
<template>
  <div class="module-header">
    <h3>Manufacturing Items</h3>
    <button @click="toggleEditMode">
      {{ isEditMode ? '💾 Save' : '✏️ Edit Layout' }}
    </button>
  </div>
</template>
```

#### 2. Resize Handles (Drag to change ratio)
```vue
<!-- Between widgets in FlexLayoutArea.vue -->
<div
  v-if="isEditMode && index < layouts.length - 1"
  class="resize-handle"
  @mousedown="startResize(index, $event)"
>
  <div class="handle-bar">⋮⋮⋮</div>
  <div class="tooltip">Info: {{ ratios.info }}% | Actions: {{ ratios.actions }}%</div>
</div>
```

**Drag Logic:**
```typescript
function startResize(index: number, event: MouseEvent) {
  const startY = event.clientY
  const startRatios = [...currentRatios]

  function onMouseMove(e: MouseEvent) {
    const deltaY = e.clientY - startY
    const containerHeight = container.value.clientHeight
    const deltaRatio = (deltaY / containerHeight) * 100

    // Update ratios
    currentRatios[index] = Math.max(10, startRatios[index] + deltaRatio)
    currentRatios[index + 1] = Math.max(10, startRatios[index + 1] - deltaRatio)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', () => {
    document.removeEventListener('mousemove', onMouseMove)
    saveLayout()
  }, { once: true })
}
```

#### 3. Settings Panel (Click ⚙️ icon)
```vue
<template>
  <Teleport to="body">
    <div v-if="showSettings" class="settings-overlay" @click.self="showSettings = false">
      <div class="settings-panel">
        <h4>{{ selectedWidget.title }} Settings</h4>

        <!-- Flex Ratio -->
        <div class="setting-group">
          <label>Flex Ratio (Height %)</label>
          <input
            type="range"
            min="1"
            max="12"
            v-model.number="selectedWidget.flex"
          >
          <span>{{ (selectedWidget.flex / totalFlex * 100).toFixed(0) }}%</span>
        </div>

        <!-- Min Height -->
        <div class="setting-group">
          <label>Min Height (px)</label>
          <input type="number" v-model.number="selectedWidget.minHeight">
        </div>

        <!-- Max Height -->
        <div class="setting-group">
          <label>Max Height (px)</label>
          <input type="number" v-model.number="selectedWidget.maxHeight">
        </div>

        <!-- Padding -->
        <div class="setting-group">
          <label>Padding</label>
          <div class="padding-inputs">
            <input type="number" v-model.number="selectedWidget.padding.top" placeholder="Top">
            <input type="number" v-model.number="selectedWidget.padding.right" placeholder="Right">
            <input type="number" v-model.number="selectedWidget.padding.bottom" placeholder="Bottom">
            <input type="number" v-model.number="selectedWidget.padding.left" placeholder="Left">
          </div>
        </div>

        <div class="settings-actions">
          <button @click="applySettings">Apply</button>
          <button @click="resetToDefaults">Reset to Defaults</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
```

#### 4. Visual Feedback
```vue
<template>
  <!-- Show constraint indicators in edit mode -->
  <div v-if="isEditMode" class="constraint-overlay">
    <!-- Min height indicator -->
    <div
      v-if="widget.minHeight"
      class="constraint-line min-height"
      :style="{ height: `${widget.minHeight}px` }"
    >
      MIN: {{ widget.minHeight }}px
    </div>

    <!-- Max height indicator -->
    <div
      v-if="widget.maxHeight"
      class="constraint-line max-height"
      :style="{ height: `${widget.maxHeight}px` }"
    >
      MAX: {{ widget.maxHeight }}px
    </div>

    <!-- Current size -->
    <div class="size-indicator">
      {{ currentHeight }}px ({{ currentRatio }}%)
    </div>
  </div>
</template>
```

#### 5. Save to localStorage
```typescript
function saveLayout() {
  const layoutData = {
    layouts: currentLayouts.value,
    timestamp: Date.now()
  }

  localStorage.setItem(
    `gestima_layout_${config.moduleKey}`,
    JSON.stringify(layoutData)
  )

  toast.success('Layout saved!')
}

function loadLayout() {
  const saved = localStorage.getItem(`gestima_layout_${config.moduleKey}`)
  if (saved) {
    const { layouts } = JSON.parse(saved)
    currentLayouts.value = layouts
  }
}
```

---

### Phase 3: Config Export + Presets (2-3 hours) - ADVANCED

#### 1. Export to TypeScript Config File
```typescript
function exportToConfig() {
  const configCode = `
// Generated by Layout Editor - ${new Date().toISOString()}
export const ${config.moduleKey}Config: ModuleLayoutConfig = {
  moduleKey: '${config.moduleKey}',

  widgets: [
${config.widgets.map(w => `    {
      id: '${w.id}',
      flex: ${w.flex},
      minHeight: ${w.minHeight},
      maxHeight: ${w.maxHeight},
      padding: {
        top: ${w.padding.top},
        right: ${w.padding.right},
        bottom: ${w.padding.bottom},
        left: ${w.padding.left}
      }
    }`).join(',\n')}
  ]
}
`

  // Download as .ts file
  const blob = new Blob([configCode], { type: 'text/typescript' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${config.moduleKey}-layout.ts`
  a.click()
}
```

#### 2. Spacing Presets
```typescript
const spacingPresets = {
  compact: {
    containerPadding: 8,
    widgetGap: 8,
    widgetPadding: 12,
    contentGap: 8
  },
  comfortable: {
    containerPadding: 16,
    widgetGap: 12,
    widgetPadding: 16,
    contentGap: 12
  },
  spacious: {
    containerPadding: 24,
    widgetGap: 16,
    widgetPadding: 20,
    contentGap: 16
  }
}

function applyPreset(presetName: keyof typeof spacingPresets) {
  const preset = spacingPresets[presetName]

  // Apply to all widgets
  currentLayouts.value.forEach(layout => {
    layout.padding = {
      top: preset.widgetPadding,
      right: preset.widgetPadding,
      bottom: preset.widgetPadding,
      left: preset.widgetPadding
    }
  })

  // Apply container settings
  containerPadding.value = preset.containerPadding
  widgetGap.value = preset.widgetGap

  saveLayout()
}
```

#### 3. Import/Export JSON
```typescript
function exportLayoutJSON() {
  const layoutExport = {
    moduleKey: config.moduleKey,
    layouts: currentLayouts.value,
    spacing: {
      containerPadding: containerPadding.value,
      widgetGap: widgetGap.value
    },
    version: 1,
    exportedAt: new Date().toISOString(),
    metadata: {
      name: layoutName.value || 'Custom Layout',
      description: layoutDescription.value
    }
  }

  const json = JSON.stringify(layoutExport, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${config.moduleKey}-layout.json`
  a.click()
}

function importLayoutJSON(file: File) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const layoutData = JSON.parse(e.target.result as string)

    // Validate module key matches
    if (layoutData.moduleKey !== config.moduleKey) {
      toast.error('Layout is for different module!')
      return
    }

    // Apply imported layout
    currentLayouts.value = layoutData.layouts
    containerPadding.value = layoutData.spacing.containerPadding
    widgetGap.value = layoutData.spacing.widgetGap

    saveLayout()
    toast.success('Layout imported!')
  }
  reader.readAsText(file)
}
```

---

## 🎨 FULL CONSTRAINT SYSTEM

### Complete Type Definition

```typescript
// frontend/src/types/widget.ts

export interface WidgetConstraints {
  // === SIZING ===
  flex?: number              // Flex ratio (6 = 60%, 4 = 40% if total is 10)
  minWidth?: number          // Min width (px)
  maxWidth?: number          // Max width (px)
  minHeight?: number         // Min height (px)
  maxHeight?: number         // Max height (px)
  grow?: boolean             // Can grow beyond default?
  shrink?: boolean           // Can shrink below default?

  // === SPACING ===
  padding?: {
    top: number
    right: number
    bottom: number
    left: number
  }
  margin?: {
    top: number
    right: number
    bottom: number
    left: number
  }
  gap?: number               // Gap between child elements

  // === POSITIONING ===
  glue?: {
    top?: boolean            // Stick to top edge
    right?: boolean          // Stick to right edge
    bottom?: boolean         // Stick to bottom edge
    left?: boolean           // Stick to left edge
  }
  glueOffset?: {
    top?: number             // Offset from edge when glued
    right?: number
    bottom?: number
    left?: number
  }
  alignment?: 'start' | 'center' | 'end' | 'stretch'

  // === RESPONSIVE ===
  responsive?: {
    mobile?: Partial<WidgetConstraints>
    tablet?: Partial<WidgetConstraints>
    desktop?: Partial<WidgetConstraints>
  }
}

export interface WidgetLayout extends WidgetConstraints {
  i: string

  // Grid-based (for GridStack horizontal mode)
  x?: number
  y?: number
  w?: number
  h?: number

  static?: boolean
  sizeToContent?: boolean | number
}
```

---

## 📚 KOMPLETNÍ PŘÍKLAD (Manufacturing Items)

```typescript
// frontend/src/config/layouts/manufacturing-items-detail.ts

export const manufacturingItemsDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'manufacturing-items-detail',

  // Grid settings (for horizontal mode)
  cols: 12,
  rowHeight: 60,

  // Global spacing
  spacing: {
    containerPadding: 16,
    widgetGap: 12,
    presets: {
      compact: { padding: 8, gap: 8 },
      comfortable: { padding: 16, gap: 12 },
      spacious: { padding: 24, gap: 16 }
    }
  },

  // Widgets with FULL constraints
  widgets: [
    {
      id: 'manufacturing-item-info',
      type: 'info-card',
      title: 'Informace',
      component: 'ManufacturingItemInfoWidget',

      // Grid constraints (horizontal mode)
      minWidth: 3,
      minHeight: 2,
      defaultWidth: 6,
      defaultHeight: 3,

      // Flex constraints (vertical mode)
      flex: 6,              // 60% height
      minHeight: 120,       // Min 120px
      maxHeight: 500,       // Max 500px
      grow: true,           // Can grow
      shrink: true,         // Can shrink

      // Spacing
      padding: {
        top: 16,
        right: 16,
        bottom: 16,
        left: 16
      },
      gap: 12,              // Gap between info fields

      // Positioning
      glue: {
        top: true,          // Stick to top
        left: true,         // Stick to left
        right: true         // Stick to right
      },

      // Responsive
      responsive: {
        mobile: {
          flex: 12,         // Full width on mobile
          padding: { top: 8, right: 8, bottom: 8, left: 8 }
        }
      },

      resizable: true,
      removable: false,
      required: true
    },
    {
      id: 'manufacturing-item-actions',
      type: 'action-bar',
      title: 'Akce',
      component: 'ManufacturingItemActionsWidget',

      // Grid constraints
      minWidth: 3,
      minHeight: 1,
      defaultWidth: 6,
      defaultHeight: 2,

      // Flex constraints
      flex: 4,              // 40% height
      minHeight: 100,
      maxHeight: 300,
      grow: true,
      shrink: true,

      // Spacing
      padding: {
        top: 16,
        right: 16,
        bottom: 16,
        left: 16
      },
      gap: 8,               // Gap between buttons

      // Positioning
      glue: {
        bottom: true,       // Stick to bottom
        left: true,
        right: true
      },

      resizable: true,
      removable: false,
      required: true
    }
  ],

  // Default layouts
  defaultLayouts: {
    // Compact: Vertical stack (uses FlexLayoutArea)
    compact: [
      {
        i: 'manufacturing-item-info',
        flex: 6,
        minHeight: 120,
        padding: { top: 16, right: 16, bottom: 16, left: 16 }
      },
      {
        i: 'manufacturing-item-actions',
        flex: 4,
        minHeight: 100,
        padding: { top: 16, right: 16, bottom: 16, left: 16 }
      }
    ],

    // Comfortable: Side-by-side (uses GridLayoutArea)
    comfortable: [
      {
        i: 'manufacturing-item-info',
        x: 0, y: 0, w: 6, h: 10
      },
      {
        i: 'manufacturing-item-actions',
        x: 6, y: 0, w: 6, h: 10
      }
    ]
  }
}
```

---

## ⏱️ COMPLETE TIMELINE

| Phase | Features | Time | Priority |
|-------|----------|------|----------|
| **Phase 1** | Basic hybrid layout | 1.5h | 🔴 MUST |
| **Phase 2** | Visual editor | 3-4h | 🟡 NICE |
| **Phase 3** | Config export + presets | 2-3h | 🟢 LATER |
| **TOTAL** | Full solution | 7-10h | |

---

## 🎯 ZÁVĚR

### Co jsme zjistili:
- GridStack ❌ vertical fill (fixed rows)
- Flexbox ✅ vertical fill (`flex: 1`)
- TemplateModule = Flexbox (proto funguje!)

### Řešení:
- Vertical → Flexbox (vyplní prostor)
- Horizontal → GridStack (drag & drop)

### Implementace:
- Phase 1: Základní layout (1.5h) ← START HERE!
- Phase 2: Visual editor (3-4h)
- Phase 3: Advanced (2-3h)

### Result:
**Widgety vyplní 100% výšky proporcionálně. FUNGUJE! ✅**
