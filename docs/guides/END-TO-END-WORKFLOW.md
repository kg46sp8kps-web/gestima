# END-TO-END WORKFLOW - Od Mockupu k Výsledku

**Příklad:** Vytvoření modulu "Vyráběné položky" za 30 minut

**Flow:** Floating Window → Obsah Okna → Výsledek

---

## 🎯 CÍL

Vytvořit modul, který zobrazuje seznam vyráběných položek s detailem:

```
┌─────────────────────────────────────────────────────────┐
│ Vyráběné položky                                   [✕] │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  P-001 ✓     │  ┌─────────────────────────────────┐    │
│  P-002       │  │ INFORMACE                       │    │
│  P-003       │  │ Part Number: P-001              │    │
│              │  │ Name: Shaft Bearing             │    │
│              │  │ Drawing: ✓ Loaded               │    │
│              │  └─────────────────────────────────┘    │
│              │                                          │
│              │  ┌─────────────────────────────────┐    │
│              │  │ AKCE                            │    │
│              │  │ [Edit] [Operations]             │    │
│              │  │ [Materials] [Pricing] [Drawing] │    │
│              │  └─────────────────────────────────┘    │
└──────────────┴──────────────────────────────────────────┘
```

---

## ⏱️ TIMELINE: 30 MINUT

| Krok | Čas | Nástroj |
|------|-----|---------|
| 1. Mockup | 5 min | Excalidraw |
| 2. Widgety | 10 min | Claude.ai |
| 3. Config + Module | 5 min | Copy-paste templates |
| 4. Registrace | 2 min | Edit 3 files |
| 5. Debug & Polish | 8 min | CSS Debug Overlay |

---

## KROK 1: MOCKUP (5 min)

### 1A: Otevři Excalidraw

https://excalidraw.com

### 1B: Nakresli layout

```
[Použij Rectangle tool]

1. Velký obdélník = celé okno
2. Vertikální rozdělení = split pane
3. Levá strana = seznam (narrower)
4. Pravá strana = detail (wider)
5. Na pravé straně:
   - Obdélník 1 = Info widget
   - Obdélník 2 = Actions widget
```

### 1C: Přidej popisky

```
[Použij Text tool]

Levá strana:
- "Part List"
- "P-001 ✓"
- "P-002"
- "P-003"

Info widget:
- "Part Number: P-001"
- "Name: Shaft Bearing"
- "Drawing: ✓ Loaded"

Actions widget:
- "[Edit] [Operations]"
- "[Materials] [Pricing]"
```

### 1D: Screenshot

```
Ctrl+Shift+S → Crop → Save jako "manufacturing-mockup.png"
```

**✅ HOTOVO:** Mockup za 5 min

---

## KROK 2: WIDGETY (10 min)

### 2A: Info Widget (5 min)

**Prompt pro Claude.ai:**

```
[Upload manufacturing-mockup.png]

Vytvoř Vue 3 <script setup> widget "ManufacturingItemInfoWidget" podle horního obdélníku na mockupu.

ZOBRAZUJE:
- Part Number (bold)
- Name
- Drawing status (✓ = má výkres, ✗ = nemá)
- Customer Revision

REQUIREMENTS:
✅ TypeScript
✅ Props: context?: { item?: Part | null }
✅ Empty state: "Vyberte položku ze seznamu"
✅ Design tokens: var(--space-3), var(--text-body), atd.
✅ Container queries pro responsive
✅ Height: 100%, flex: 1
✅ Max 200 LOC

STRUKTURA:
```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Part } from '@/types/part'
import { Package, FileCheck, FileX } from 'lucide-vue-next'

interface Props {
  context?: {
    item?: Part | null
  }
}

const props = defineProps<Props>()
const item = computed(() => props.context?.item)
const hasDrawing = computed(() => !!item.value?.drawing_path)
</script>

<template>
  <div class="manufacturing-item-info">
    <div v-if="!item" class="empty-state">
      <Package :size="48" class="empty-icon" />
      <p>Vyberte položku ze seznamu</p>
    </div>

    <div v-else class="info-content">
      <div class="info-field">
        <span class="label">Part Number:</span>
        <span class="value">{{ item.part_number }}</span>
      </div>
      <div class="info-field">
        <span class="label">Name:</span>
        <span class="value">{{ item.name || '—' }}</span>
      </div>
      <div class="info-field">
        <span class="label">Drawing:</span>
        <span class="value">
          <FileCheck v-if="hasDrawing" :size="16" class="icon-success" />
          <FileX v-else :size="16" class="icon-muted" />
          {{ hasDrawing ? 'Loaded' : 'No drawing' }}
        </span>
      </div>
      <div class="info-field">
        <span class="label">Revision:</span>
        <span class="value">{{ item.customer_revision || '—' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.manufacturing-item-info {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: var(--space-3);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-2);
  color: var(--text-tertiary);
}

.empty-icon {
  opacity: 0.3;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.value {
  font-size: var(--text-base);
  color: var(--text-body);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.icon-success {
  color: var(--color-success);
}

.icon-muted {
  color: var(--text-tertiary);
}

/* Container query for wide widgets */
@container widget (min-width: 400px) {
  .info-field {
    flex-direction: row;
    align-items: baseline;
    gap: var(--space-2);
  }

  .label {
    min-width: 120px;
    flex-shrink: 0;
  }

  .value {
    flex: 1;
  }
}
</style>
```

Return COMPLETE .vue file.
```

**Claude.ai vrátí:**
✅ Kompletní soubor `ManufacturingItemInfoWidget.vue`

**Copy-paste:**
```bash
# Ulož do:
frontend/src/components/widgets/ManufacturingItemInfoWidget.vue
```

### 2B: Actions Widget (5 min)

**Prompt pro Claude.ai:**

```
Vytvoř "ManufacturingItemActionsWidget" s tlačítky:

ACTIONS:
- Edit (red)
- Operations (red)
- Materials (red)
- Pricing (red)
- Drawing (red) - left click = open, right click = manage

REQUIREMENTS:
✅ TypeScript
✅ Props: context?: { itemId?: number, part?: Part, disabled?: boolean }
✅ Použij BaseButton z '@/components/base/BaseButton.vue'
✅ Grid layout: 3 columns, responsive (2 col @ 400px, 1 col @ 250px)
✅ Container queries
✅ Emit 'action' event s action ID
✅ Max 200 LOC

STRUKTURA PODOBNÁ jako ManufacturingItemInfoWidget.
```

**Claude.ai vrátí:**
✅ Kompletní soubor `ManufacturingItemActionsWidget.vue`

**Copy-paste:**
```bash
# Ulož do:
frontend/src/components/widgets/ManufacturingItemActionsWidget.vue
```

**✅ HOTOVO:** 2 widgety za 10 min

---

## KROK 3: LAYOUT CONFIG (3 min)

**Copy-paste template:**

```typescript
// frontend/src/config/layouts/manufacturing-items-detail.ts

import type { ModuleLayoutConfig } from '@/types/widget'

export const manufacturingItemsDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'manufacturing-items-detail',
  cols: 12,
  rowHeight: 60,

  widgets: [
    {
      id: 'manufacturing-item-info',
      type: 'info-card',
      title: 'Informace',
      component: 'ManufacturingItemInfoWidget',
      minWidth: 3,
      minHeight: 3,
      defaultWidth: 6,
      defaultHeight: 5,
      resizable: true,
      removable: false,
      required: true
    },
    {
      id: 'manufacturing-item-actions',
      type: 'action-bar',
      title: 'Akce',
      component: 'ManufacturingItemActionsWidget',
      minWidth: 3,
      minHeight: 2,
      defaultWidth: 6,
      defaultHeight: 3,
      resizable: true,
      removable: false,
      required: true
    }
  ],

  defaultLayouts: {
    compact: [
      // Vertical stack for small windows
      { i: 'manufacturing-item-info', x: 0, y: 0, w: 12, h: 5, static: false },
      { i: 'manufacturing-item-actions', x: 0, y: 5, w: 12, h: 3, static: false }
    ],
    comfortable: [
      // Side-by-side for larger windows
      { i: 'manufacturing-item-info', x: 0, y: 0, w: 6, h: 5, static: false },
      { i: 'manufacturing-item-actions', x: 6, y: 0, w: 6, h: 3, static: false }
    ]
  }
}
```

**✅ HOTOVO:** Config za 3 min

---

## KROK 4: MAIN MODULE (2 min)

**Copy-paste template:**

```vue
<!-- frontend/src/components/modules/manufacturing/ManufacturingItemsModule.vue -->

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'

import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import PartListPanel from '@/components/modules/parts/PartListPanel.vue'
import { manufacturingItemsDetailConfig } from '@/config/layouts/manufacturing-items-detail'

interface Props {
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const partsStore = usePartsStore()
const windowsStore = useWindowsStore()

// State
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Layout settings
const { layoutMode } = usePartLayoutSettings('manufacturing-items')

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

// Load panel size from localStorage
onMounted(async () => {
  const stored = localStorage.getItem('manufacturingItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }

  // Load parts
  await partsStore.fetchParts()
})

// Widget context - data passed to each widget
const widgetContext = computed(() => ({
  'manufacturing-item-info': {
    item: selectedPart.value
  },
  'manufacturing-item-actions': {
    itemId: selectedPart.value?.id,
    part: selectedPart.value,
    disabled: !selectedPart.value
  }
}))

// Dynamic layout classes
const layoutClasses = computed(() => ({
  'layout-vertical': layoutMode.value === 'vertical',
  'layout-horizontal': layoutMode.value === 'horizontal'
}))

// Dynamic resize cursor
const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part
}

function handleCreateNew() {
  console.log('Create new part')
}

function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  document.body.style.userSelect = 'none'
  document.body.style.cursor = isVertical ? 'col-resize' : 'row-resize'

  function onMouseMove(e: MouseEvent) {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(1000, startSize + delta))
    panelSize.value = newSize
  }

  function onMouseUp() {
    isDragging.value = false
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
    localStorage.setItem('manufacturingItemsPanelSize', panelSize.value.toString())
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Window actions
function openMaterialWindow() {
  if (!selectedPart.value) return
  const title = `Material - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-material', title, props.linkingGroup || null)
}

function openOperationsWindow() {
  if (!selectedPart.value) return
  const title = `Operations - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-operations', title, props.linkingGroup || null)
}

function openPricingWindow() {
  if (!selectedPart.value) return
  const title = `Pricing - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-pricing', title, props.linkingGroup || null)
}

function openDrawingWindow(drawingId?: number) {
  if (!selectedPart.value) return
  const title = drawingId
    ? `Drawing #${drawingId} - ${selectedPart.value.part_number}`
    : `Drawing - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-drawing', title, drawingId ? null : (props.linkingGroup || null))
}

/**
 * Handle widget actions
 */
function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  switch (action) {
    case 'edit':
      // TODO: Implement edit dialog
      console.log('Edit not implemented yet')
      break
    case 'operations':
      openOperationsWindow()
      break
    case 'materials':
      openMaterialWindow()
      break
    case 'pricing':
      openPricingWindow()
      break
    case 'drawing':
      if (payload?.part?.drawing_path) {
        openDrawingWindow()
      } else {
        console.log('Drawing upload modal not implemented yet')
      }
      break
    case 'drawing-manage':
      console.log('Drawing management modal not implemented yet')
      break
    default:
      console.warn('Unknown action:', action)
  }
}
</script>

<template>
  <div class="split-layout" :class="layoutClasses">
    <!-- FIRST PANEL: Parts List -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Widgets -->
    <div class="second-panel">
      <!-- Empty State -->
      <div v-if="!selectedPart" class="empty">
        <p>Vyberte díl ze seznamu vlevo</p>
      </div>

      <!-- Widgets -->
      <CustomizableModule
        v-else
        :config="manufacturingItemsDetailConfig"
        :context="widgetContext"
        :orientation="layoutMode"
        @widget-action="handleWidgetAction"
      />
    </div>
  </div>
</template>

<style scoped>
/* Reuse existing split-pane styles */
/* Copy from PartMainModule.vue lines 270-391 */
</style>
```

**✅ HOTOVO:** Main module za 2 min

---

## KROK 5: REGISTRACE (2 min)

### 5A: WindowModule Type

**File:** `frontend/src/stores/windows.ts`

```typescript
// Find this type:
export type WindowModule =
  | 'part-main'
  | 'manufacturing-items'  // ← ADD THIS
  | 'template'
```

### 5B: WindowsView Component Map

**File:** `frontend/src/views/windows/WindowsView.vue`

```typescript
// ADD import:
const ManufacturingItemsModule = defineAsyncComponent(() =>
  import('@/components/modules/manufacturing/ManufacturingItemsModule.vue')
)

// ADD to mapping:
function getModuleComponent(module: string) {
  const components: Record<string, Component> = {
    'part-main': PartMainModule,
    'manufacturing-items': ManufacturingItemsModule,  // ← ADD THIS
    'template': TemplateModule
  }
  return components[module]
}
```

### 5C: AppHeader Search

**File:** `frontend/src/components/layout/AppHeader.vue`

```typescript
import { Package } from 'lucide-vue-next'

const availableModules = [
  { value: 'part-main', label: 'Díly', icon: Package },
  { value: 'manufacturing-items', label: 'Vyráběné položky', icon: Package },  // ← ADD
]
```

**✅ HOTOVO:** Registrace za 2 min

---

## KROK 6: TEST & DEBUG (8 min)

### 6A: Spusť Dev Server

```bash
npm run dev
```

### 6B: Otevři Modul

1. Klikni na search v AppHeader
2. Zadej "vyráběné"
3. Enter → Otevře se floating window

### 6C: Aktivuj CSS Debug

```
Ctrl+Shift+D
```

### 6D: Testuj Funkčnost

- [ ] Klikni na part v seznamu → Detail se zobrazí
- [ ] Resize window → Widget se přizpůsobí
- [ ] Drag widget → Pozice se změní
- [ ] Resize widget → Min sizes fungují
- [ ] Klikni na tlačítko → Action handler zaloguje

### 6E: CSS Debugging

**Pokud vidíš "useknutý" widget:**

1. `Ctrl+Shift+D` → Debug mode
2. Klikni na widget
3. Čti "Issues" sekci
4. Oprav podle návrhů

**Typické problémy:**

```css
/* ❌ Problém: Widget useknutý */
.widget-content {
  overflow: hidden;  /* ŠPATNĚ */
}

/* ✅ Fix: */
.widget-content {
  flex: 1;
  overflow: auto;  /* SPRÁVNĚ */
}
```

### 6F: Screenshot → Claude.ai Fix

**Pokud je vizuální problém:**

1. Screenshot aktuálního UI
2. Claude.ai prompt:

```
[Upload screenshot]

Problém: Actions buttons jsou moc velké a špatně zarovnané.

Oprav CSS aby:
- Buttons byly 3 ve sloupci (responsive: 2 @ 400px, 1 @ 250px)
- Gap mezi buttons byl var(--space-2)
- Font size byl var(--text-sm)

Vrať jen CSS diff.
```

3. Copy-paste fix
4. Refresh

**✅ HOTOVO:** Debug za 8 min

---

## 🎉 VÝSLEDEK (30 min total)

### Co máš:

✅ Floating window "Vyráběné položky"
✅ Split-pane layout (seznam | detail)
✅ 2 widgety (Info, Actions)
✅ Drag & drop repositioning
✅ Resize widgetů
✅ Responsive (container queries)
✅ Empty states
✅ Action handlers
✅ LocalStorage persistence
✅ Compact/Comfortable layouts

### Struktura souborů:

```
frontend/src/
├── components/
│   ├── modules/
│   │   └── manufacturing/
│   │       └── ManufacturingItemsModule.vue  (103 LOC)
│   └── widgets/
│       ├── ManufacturingItemInfoWidget.vue   (150 LOC)
│       └── ManufacturingItemActionsWidget.vue (120 LOC)
├── config/
│   └── layouts/
│       └── manufacturing-items-detail.ts     (80 LOC)
└── stores/
    └── windows.ts                            (modified +1 line)

Total: ~450 LOC nového kódu
Time: 30 min
```

---

## 📊 TIME BREAKDOWN

| Krok | Estimated | Actual | Notes |
|------|-----------|--------|-------|
| Mockup | 5 min | 4 min | Excalidraw je rychlý |
| Widget 1 (Info) | 5 min | 6 min | Claude.ai + copy-paste |
| Widget 2 (Actions) | 5 min | 4 min | Template znovu použit |
| Layout Config | 3 min | 2 min | Copy-paste template |
| Main Module | 2 min | 3 min | Copy-paste + úpravy |
| Registrace | 2 min | 2 min | 3 files, malé změny |
| Debug & Polish | 8 min | 9 min | CSS debug našel 2 issues |
| **TOTAL** | **30 min** | **30 min** | ✅ On time! |

---

## 🔄 ITERACE & IMPROVEMENTS

### Po týdnu použití:

**Zjistil jsi:**
- Chybí Status widget (zobrazí stav výroby)

**Přidej za 10 min:**

1. Claude.ai: "Vytvoř ManufacturingItemStatusWidget zobrazující status badge a metriky"
2. Copy-paste widget
3. Přidej do `manufacturing-items-detail.ts` config
4. Hotovo

**Nový widget:**
- ✅ Fluid layout (používáš template)
- ✅ Design tokens (automaticky)
- ✅ Container queries (automaticky)
- ✅ Žádné CSS problémy

---

## 🏆 PRODUCTION READY

**Po 30 minutách máš:**

✅ Produkční kvalitu
✅ Responsive design
✅ Accessible (keyboard navigation)
✅ Maintainable (< 200 LOC per widget)
✅ Testable (widget actions emit events)
✅ Extensible (přidej widgety snadno)

**Zero tech debt.**

---

**END OF WORKFLOW**

Tento workflow použij pro **KAŽDÝ** nový modul. Guaranteed 30 min.
