# UI BIBLE V8.2 - KOMPLETNÍ STAVEBNÍ PRŮVODCE

**Verze:** 8.2
**Datum:** 2026-02-02
**Status:** 🔒 **PRODUCTION READY** - Konsolidovaná dokumentace všech UI vzorů

**Cíl:** Vytvořit konzistentní, profesionální UI v rekordním čase s garantovanou kvalitou.

---

## 📖 OBSAH

1. [Design System](#design-system)
2. [Module Patterns](#module-patterns)
3. [Component Library](#component-library)
4. [Layout Patterns](#layout-patterns)
5. [Window System](#window-system)
6. [Best Practices](#best-practices)
7. [Anti-Patterns](#anti-patterns)
8. [Quick Reference](#quick-reference)

---

## 🎨 DESIGN SYSTEM

### Design Tokens (VŽDY POUŽIJ)

```css
/* === SPACING === 4pt grid system */
--space-1: 4px    /* Tiny gaps, icon spacing */
--space-2: 6px    /* Base gap for tight layouts */
--space-3: 8px    /* Base padding for cards */
--space-4: 12px   /* Section spacing */
--space-5: 16px   /* Card/panel padding */
--space-6: 20px   /* Large section margins */

/* === TYPOGRAPHY === */
--text-xs: 10px   /* Labels (uppercase), badges */
--text-sm: 11px   /* Secondary text, buttons */
--text-base: 12px /* Body text (BASE) */
--text-lg: 13px   /* Subheadings */
--text-xl: 14px   /* Headings, emphasis */

--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700

/* === ICONS === */
--icon-size: 15px /* Lucide icon size (STANDARD) */

/* === COLORS === */
--color-primary: #991b1b       /* Red - primary actions */
--color-primary-hover: #7f1d1d /* Darker red on hover */
--color-success: #059669       /* Green - success states */
--color-danger: #ef4444        /* Red - danger/delete */
--color-info: #2563eb          /* Blue - info states */

/* Text colors */
--text-primary: #ffffff        /* Headings, important text */
--text-body: #f5f5f5          /* Body text (most used) */
--text-secondary: #a3a3a3     /* Labels, secondary info */
--text-tertiary: #737373      /* Disabled, de-emphasized */

/* Background colors */
--bg-base: #0a0a0a            /* App background */
--bg-surface: #141414         /* Cards, panels */
--bg-raised: #1a1a1a          /* Elevated elements */
--bg-input: #1a1a1a           /* Form inputs */
--bg-hover: #1f1f1f           /* Hover states */

/* Border colors */
--border-color: #2a2a2a       /* Default borders */
--border-default: #2a2a2a     /* Alias */
--border-strong: #404040      /* Emphasized borders */

/* State colors */
--state-hover: #1f1f1f
--state-focus-bg: #1a1a1a
--state-focus-border: #2563eb
--state-selected: rgba(153, 27, 27, 0.2)

/* === RADIUS === */
--radius-sm: 4px
--radius-md: 6px
--radius-lg: 8px
--radius-xl: 12px

/* === SHADOWS === */
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05)
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1)
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1)
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1)

/* === TRANSITIONS === */
--duration-fast: 150ms
--duration-normal: 200ms
--duration-slow: 300ms
--ease-out: cubic-bezier(0.4, 0, 0.2, 1)
--transition-fast: all 150ms cubic-bezier(0.4, 0, 0.2, 1)
--transition-normal: all 200ms cubic-bezier(0.4, 0, 0.2, 1)
```

### Usage Examples

```css
/* ❌ NIKDY */
padding: 8px;
font-size: 12px;
color: #f5f5f5;
border: 1px solid #2a2a2a;

/* ✅ VŽDY */
padding: var(--space-3);
font-size: var(--text-base);
color: var(--text-body);
border: 1px solid var(--border-color);
```

---

## 🏗️ MODULE PATTERNS

### Pattern 1: Split-Pane Module (Manufacturing Items)

**Použití:** Moduly s master-detail layoutem (seznam + detail)

**Struktura:**
```
┌─────────────────────────────────────┐
│  LEFT PANEL      │  RIGHT PANEL     │
│  (List)          │  (Detail)        │
│  - PartList      │  - Info Ribbon   │
│  - Search        │  - Actions       │
│  - Create btn    │  - Modals        │
└─────────────────────────────────────┘
```

**Template:**

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import PartListPanel from '@/components/modules/parts/PartListPanel.vue'
import type { Part, PartUpdate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { Edit, Copy, Trash2, Save, X } from 'lucide-vue-next'

interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'select-part': [partNumber: string] }>()

// Stores
const partsStore = usePartsStore()
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// Layout settings
const { layoutMode } = usePartLayoutSettings('my-module')

// Panel state
const panelSize = ref(320)
const isDragging = ref(false)
const selectedPart = ref<Part | null>(null)
const isEditing = ref(false)

// Handle part selection
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // KRITICKÉ: Update window context pro linkování
  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,
      part.id,
      part.part_number,
      part.article_number
    )
  }

  emit('select-part', part.part_number)
}

// Resize handler
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  const handleMove = (e: MouseEvent) => {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(1000, startSize + delta))
    panelSize.value = newSize
  }

  const handleUp = () => {
    isDragging.value = false
    localStorage.setItem('myModulePanelSize', String(panelSize.value))
    document.removeEventListener('mousemove', handleMove)
    document.removeEventListener('mouseup', handleUp)
  }

  document.addEventListener('mousemove', handleMove)
  document.addEventListener('mouseup', handleUp)
}

const panelStyle = computed(() => {
  const size = `${panelSize.value}px`
  return layoutMode.value === 'vertical'
    ? { width: size }
    : { height: size }
})

const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)
</script>

<template>
  <div
    class="split-layout"
    :class="`layout-${layoutMode}`"
  >
    <!-- FIRST PANEL: List -->
    <div class="first-panel" :style="panelStyle">
      <PartListPanel
        :linking-group="linkingGroup"
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

    <!-- SECOND PANEL: Detail -->
    <div v-if="selectedPart" class="second-panel">
      <!-- INFO RIBBON -->
      <div class="info-ribbon" :class="{ 'editing': isEditing }">
        <!-- Content zde -->
      </div>

      <!-- ACTIONS -->
      <div class="actions-section">
        <!-- Actions zde -->
      </div>
    </div>

    <!-- EMPTY STATE -->
    <div v-else class="empty">
      <p>Select an item from the list</p>
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.layout-horizontal {
  flex-direction: column;
}

.layout-vertical {
  flex-direction: row;
}

/* === PANELS === */
.first-panel,
.second-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.first-panel {
  flex-shrink: 0; /* KRITICKÉ: panel má fixed size */
}

.second-panel {
  flex: 1; /* KRITICKÉ: zabere zbytek prostoru */
  padding: var(--space-5);
  overflow-y: auto;
  container-type: inline-size;
  container-name: second-panel;
}

/* === RESIZE HANDLE === */
.resize-handle {
  flex-shrink: 0;
  background: var(--border-color);
  transition: background var(--duration-fast);
  position: relative;
  z-index: 10;
}

.layout-vertical .resize-handle {
  width: 4px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle {
  height: 4px;
  cursor: row-resize;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
}

/* === EMPTY STATE === */
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
}
</style>
```

---

### Pattern 2: Info Ribbon s Icon Toolbar

**Použití:** Zobrazení detail informací s editací + management akcemi

**Vizuální Design:**
```
┌───────────────────────────────────────────┐
│  Field 1    Field 2    Field 3    Field 4 │
│  value      value      value      value    │
│  Field 5    Field 6    Field 7    Field 8 │
│  value      value      value      value    │
│                                            │
│  ─────────────────────────────────────    │ ← 1px separator
│       🖊️ Edit    📋 Copy    🗑️ Delete       │ ← Centered icons
└───────────────────────────────────────────┘
```

**Key Features:**
- Responzivní grid (auto-fit)
- Editovatelná pole (inline)
- Minimální spacing (1-2px) u icon toolbar
- Negativní margin pro přesné umístění

**Template:**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { Edit, Copy, Trash2 } from 'lucide-vue-next'

const isEditing = ref(false)
const editForm = ref({
  field1: '',
  field2: '',
  // ...
})

function startEdit() {
  // Copy current values
  editForm.value = { ...currentData }
  isEditing.value = true
}

async function saveEdit() {
  // Save logic
  isEditing.value = false
}
</script>

<template>
  <div class="info-ribbon" :class="{ 'editing': isEditing }">
    <!-- INFO GRID -->
    <div class="info-grid">
      <div class="info-card">
        <label>Field Label</label>
        <input v-if="isEditing" v-model="editForm.field1" class="edit-input" />
        <span v-else class="value">{{ data.field1 || '-' }}</span>
      </div>
      <!-- Repeat for other fields -->
    </div>

    <!-- DESCRIPTION (optional) -->
    <div v-if="data.description || isEditing" class="description">
      <label>Popis</label>
      <textarea
        v-if="isEditing"
        v-model="editForm.description"
        class="edit-textarea"
        rows="3"
      ></textarea>
      <p v-else>{{ data.description || '-' }}</p>
    </div>

    <!-- ICON TOOLBAR -->
    <div v-if="!isEditing" class="icon-toolbar">
      <button class="icon-btn" @click="startEdit" title="Upravit">
        <Edit :size="15" />
      </button>
      <button class="icon-btn" @click="handleCopy" title="Kopírovat">
        <Copy :size="15" />
      </button>
      <button class="icon-btn icon-btn-danger" @click="handleDelete" title="Smazat">
        <Trash2 :size="15" />
      </button>
    </div>
  </div>
</template>

<style scoped>
/* === INFO RIBBON === */
.info-ribbon {
  position: relative;
  padding: var(--space-5);
  background: var(--bg-surface);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
  transition: all var(--duration-normal);
}

.info-ribbon.editing {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

/* === ICON TOOLBAR ===
   KRITICKÉ: Negativní margin kompenzuje ribbon padding
   pro přesné umístění na dolní hranu */
.icon-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  margin-bottom: calc(-1 * var(--space-5) + 2px); /* KRITICKÉ */
  padding-top: 2px;
  padding-bottom: 2px;
  border-top: 1px solid var(--border-color);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.icon-btn:hover {
  color: var(--color-primary);
  transform: scale(1.1);
}

.icon-btn-danger:hover {
  color: #ef4444;
}

/* === INFO GRID === */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
}

.info-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-card label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-card .value {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

/* === DESCRIPTION === */
.description {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.description label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-2);
}

.description p {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: 1.6;
}

/* === EDIT INPUTS === */
.edit-input,
.edit-textarea {
  width: 100%;
  padding: var(--space-2);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.edit-input:focus,
.edit-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

.edit-textarea {
  resize: vertical;
  font-weight: 400;
  line-height: 1.6;
}
</style>
```

---

### Pattern 3: Action Buttons Grid

**Použití:** Action buttons pro otevírání souvisejících oken (Material, Operations, Pricing, Drawing)

**Vizuální Design:**
```
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│  📦  │ │  ⚙️  │ │  💰  │ │  📄  │
│Mater │ │Opera │ │Pricn │ │Drawg │
└──────┘ └──────┘ └──────┘ └──────┘
    4 columns on desktop

┌──────┐ ┌──────┐
│  📦  │ │  ⚙️  │
│Mater │ │Opera │
│  💰  │ │  📄  │
│Pricn │ │Drawg │
└──────┘ └──────┘
    2 columns on mobile
```

**Template:**

```vue
<script setup lang="ts">
import { Package, Settings, DollarSign, FileText } from 'lucide-vue-next'
import { useWindowsStore } from '@/stores/windows'
import type { LinkingGroup } from '@/stores/windows'

interface Props {
  linkingGroup?: LinkingGroup
  selectedItem?: any
}

const props = defineProps<Props>()
const windowsStore = useWindowsStore()

function openMaterialWindow() {
  if (!props.selectedItem) return
  const title = `Material - ${props.selectedItem.part_number}`
  windowsStore.openWindow('part-material', title, props.linkingGroup || null)
}

// Similar for other windows...
</script>

<template>
  <div class="actions-section">
    <h4>Actions</h4>

    <div class="actions-grid">
      <button class="action-button" @click="openMaterialWindow" title="Materiál">
        <Package :size="32" class="action-icon" />
        <span class="action-label">Materiál</span>
      </button>

      <button class="action-button" @click="openOperationsWindow" title="Operace">
        <Settings :size="32" class="action-icon" />
        <span class="action-label">Operace</span>
      </button>

      <button class="action-button" @click="openPricingWindow" title="Ceny">
        <DollarSign :size="32" class="action-icon" />
        <span class="action-label">Ceny</span>
      </button>

      <button
        class="action-button"
        @click="handleDrawingClick"
        @contextmenu="handleDrawingRightClick"
        title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
      >
        <FileText :size="32" class="action-icon" />
        <span class="action-label">Výkres</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* === ACTIONS SECTION === */
.actions-section {
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 2px solid var(--border-color);
}

.actions-section h4 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
  font-weight: 600;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  align-content: start;
}

/* Responsive: 2 columns na úzkých containerech */
@container second-panel (max-width: 500px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* === ACTION BUTTONS === */
.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal);
}

.action-button:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  color: var(--color-primary);
}

.action-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

/* Primary action (Save) */
.action-button-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.action-button-primary .action-icon,
.action-button-primary .action-label {
  color: white;
}

.action-button-primary:hover {
  background: #7f1d1d;
  border-color: #7f1d1d;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(153, 27, 27, 0.3);
}

/* Secondary action (Cancel) */
.action-button-secondary .action-icon {
  color: var(--text-secondary);
}

.action-button-secondary:hover {
  border-color: var(--text-secondary);
}
</style>
```

---

## 🪟 WINDOW SYSTEM

### Window Linking

**Koncept:** Více oken sdílí stejný context (např. vybraný part)

```typescript
// V parent modulu (Manufacturing Items)
import { useWindowContextStore } from '@/stores/windowContext'

const contextStore = useWindowContextStore()

function handleSelectPart(part: Part) {
  selectedPart.value = part

  // KRITICKÉ: Nastaví context pro všechna linked okna
  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,    // např. 'group-1'
      part.id,               // part ID
      part.part_number,      // part number
      part.article_number    // article number
    )
  }
}

// Při otevírání linked okna
function openMaterialWindow() {
  const title = `Material - ${selectedPart.value.part_number}`
  windowsStore.openWindow(
    'part-material',         // module type
    title,                   // window title
    props.linkingGroup       // linking group (KRITICKÉ)
  )
}
```

**V child modulu (Material, Operations, etc.):**

```typescript
// Material modul automaticky dostane context přes props
interface Props {
  linkingGroup?: LinkingGroup
}

// Context se načte automaticky z contextStore
watch(() => props.linkingGroup, async (newGroup) => {
  if (newGroup) {
    const ctx = contextStore.getContext(newGroup)
    if (ctx?.partId) {
      await loadMaterialData(ctx.partId)
    }
  }
}, { immediate: true })
```

---

## 📚 COMPONENT LIBRARY

### Existing Components (POUŽIJ TYTO)

#### PartListPanel.vue
- List s vyhledáváním + column chooser
- Selection state
- Sort functionality
- Create button

```vue
<PartListPanel
  :linking-group="linkingGroup"
  @select-part="handleSelectPart"
  @create-new="handleCreateNew"
/>
```

#### CopyPartModal.vue
- Modal pro kopírování dílu
- Volba co kopírovat (operations, material, batches)
- Input pro nový artikl

```vue
<CopyPartModal
  v-model="showCopyModal"
  :part-number="selectedPart.part_number"
  :source-part="selectedPart"
  @success="handleCopySuccess"
/>
```

#### DrawingsManagementModal.vue
- Správa výkresů dílu
- Nahrávání nových
- Otevírání existujících
- Nastavení primárního

```vue
<DrawingsManagementModal
  v-model="showDrawingsModal"
  :part-number="selectedPart.part_number"
  @refresh="handleDrawingRefresh"
  @open-drawing="handleOpenDrawing"
/>
```

#### DataTable.vue
- Universal data table s řazením
- Column visibility toggle
- Row selection
- Custom cell templates

```vue
<DataTable
  :data="items"
  :columns="columns"
  :loading="isLoading"
  :rowClickable="true"
  :selected="selectedItems"
  @row-click="handleRowClick"
  @sort="handleSort"
>
  <template #cell-article_number="{ value }">
    <span class="article-number">{{ value }}</span>
  </template>
</DataTable>
```

---

## ✅ BEST PRACTICES

### 1. Spacing

```css
/* ❌ NIKDY */
margin: 16px;
padding: 8px 12px;
gap: 6px;

/* ✅ VŽDY */
margin: var(--space-5);
padding: var(--space-3) var(--space-4);
gap: var(--space-2);
```

### 2. Negativní Margins pro Přesné Umístění

```css
/* Použití: Když potřebuješ kompenzovat padding parenta */
.icon-toolbar {
  /* Neguje padding ribbonu (--space-5) a přidá zpět 2px */
  margin-bottom: calc(-1 * var(--space-5) + 2px);
  padding-bottom: 2px;
}

/* Výsledek: Přesné 2px od spodní hrany ribbonu */
```

### 3. Container Queries (NE Media Queries)

```css
/* ❌ ŠPATNĚ - Media query */
@media (max-width: 600px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ✅ SPRÁVNĚ - Container query */
@container second-panel (max-width: 500px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

### 4. Fluid Heights

```css
/* ❌ ŠPATNĚ - Fixed height */
.panel {
  height: 400px;
}

/* ✅ SPRÁVNĚ - Fluid height */
.panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.content {
  flex: 1;
  overflow: auto;
}
```

### 5. Window Linking Pattern

```typescript
// ✅ SPRÁVNĚ - Vždy nastav context při selekci
function handleSelectPart(part: Part) {
  selectedPart.value = part

  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,
      part.id,
      part.part_number,
      part.article_number
    )
  }
}

// ✅ SPRÁVNĚ - Předej linkingGroup při otevírání oken
function openMaterialWindow() {
  windowsStore.openWindow(
    'part-material',
    title,
    props.linkingGroup  // KRITICKÉ
  )
}
```

---

## ❌ ANTI-PATTERNS

### 1. Hardcoded Values

```css
/* ❌ ZAKÁZÁNO */
padding: 8px;
color: #f5f5f5;
font-size: 12px;
border-radius: 6px;

/* ✅ POVOLENO */
padding: var(--space-3);
color: var(--text-body);
font-size: var(--text-base);
border-radius: var(--radius-md);
```

### 2. Fixed Heights

```css
/* ❌ ZAKÁZÁNO */
.widget {
  height: 300px;
  min-height: 200px;
}

/* ✅ POVOLENO */
.widget {
  height: 100%;
  display: flex;
  flex-direction: column;
}
```

### 3. Media Queries místo Container Queries

```css
/* ❌ ZAKÁZÁNO */
@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

/* ✅ POVOLENO */
@container widget (max-width: 400px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
```

### 4. Zapomenuté Window Linking

```typescript
// ❌ ŠPATNĚ - Context není nastaven
function handleSelectPart(part: Part) {
  selectedPart.value = part
  // Linked okna nedostanou context!
}

// ✅ SPRÁVNĚ - Context je nastaven
function handleSelectPart(part: Part) {
  selectedPart.value = part
  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,
      part.id,
      part.part_number,
      part.article_number
    )
  }
}
```

---

### Pattern 4: Context Ribbon pro Linked Moduly

**Použití:** Linked moduly otevřené z Manufacturing Items (Material, Operations, Pricing)

**Vizuální Design:**
```
┌─────────────────────────────────────────┐
│ Materiál | 10xxxxxx | artikl | název    │ ← Subtilní 1-řádkový context
└─────────────────────────────────────────┘
```

**Key Features:**
- Zobrazuje se pouze když je modul linked (`v-if="linkingGroup && selectedPart"`)
- Jeden řádek s kontextovými informacemi
- Label modulu (Materiál/Operace/Ceny) + internal number + artikl + název
- Design tokens pro konzistenci

**Template:**

```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'

interface Props {
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()

const partsStore = usePartsStore()
const contextStore = useWindowContextStore()
const selectedPart = ref<Part | null>(null)

// Get partId from context
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

// Watch context changes
watch(contextPartId, (newPartId) => {
  if (newPartId) {
    const part = partsStore.parts.find(p => p.id === newPartId)
    if (part) {
      selectedPart.value = part
      // Load module-specific data here
    }
  }
}, { immediate: true })
</script>

<template>
  <div class="module-layout">
    <!-- LEFT PANEL: Conditional - only when standalone -->
    <div v-if="!linkingGroup" class="left-panel">
      <PartListPanel @select-part="handleSelectPart" />
    </div>

    <!-- RESIZE HANDLE: Conditional - only when standalone -->
    <div v-if="!linkingGroup" class="resize-handle"></div>

    <!-- RIGHT PANEL: Always visible -->
    <div class="right-panel" :class="{ 'full-width': linkingGroup }">
      <!-- CONTEXT RIBBON: Only when linked -->
      <div v-if="linkingGroup && selectedPart" class="context-ribbon">
        <span class="context-label">Materiál</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.part_number }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.article_number || '-' }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.name || '-' }}</span>
      </div>

      <!-- Module content -->
      <div class="module-content">
        <!-- Your module UI here -->
      </div>
    </div>
  </div>
</template>

<style scoped>
.module-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.left-panel {
  flex-shrink: 0;
  width: 320px;
}

.resize-handle {
  width: 4px;
  background: var(--border-default);
  cursor: col-resize;
  flex-shrink: 0;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  container-type: inline-size;
  container-name: right-panel;
}

.right-panel.full-width {
  width: 100%;
}

/* === CONTEXT RIBBON === */
.context-ribbon {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.context-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-divider {
  color: var(--border-default);
  font-weight: 300;
}

.context-value {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.module-content {
  flex: 1;
  overflow: auto;
  padding: var(--space-5);
}
</style>
```

**Klíčové vlastnosti:**
- `v-if="!linkingGroup"` na LEFT panel a resize handle
- `v-if="linkingGroup && selectedPart"` na context ribbon
- `:class="{ 'full-width': linkingGroup }"` na RIGHT panel
- Watch `contextPartId` pro reaktivní loading dat
- Subtilní styling s design tokeny

---

### Pattern 5: Icon-Only Buttons (STANDARD)

**Použití:** VŠECHNY buttony v aplikaci (header, toolbar, actions)

**KRITICKÉ PRAVIDLO:**
```
❌ NIKDY: <button>Text</button> nebo <button><Icon />Text</button>
✅ VŽDY:  <button title="Text"><Icon :size="15" /></button>

POZNÁMKA: V CSS existuje --icon-size: 15px pro budoucí použití
```

**Vizuální Design:**
```
┌─────────────────────────────┐
│  📋  ➕  🗑️  💾  ✏️         │ ← Jen ikony, bez textu
└─────────────────────────────┘
    24px × 24px, ikona 15px
```

**Template:**

```vue
<script setup lang="ts">
import { Plus, Edit, Trash2, Save, X } from 'lucide-vue-next'

function handleCreate() {
  // Create logic
}

function handleEdit() {
  // Edit logic
}

function handleDelete() {
  // Delete logic
}
</script>

<template>
  <div class="actions-toolbar">
    <button class="btn-icon" @click="handleCreate" title="Vytvořit nový">
      <Plus :size="15" />
    </button>
    <button class="btn-icon" @click="handleEdit" title="Upravit">
      <Edit :size="15" />
    </button>
    <button class="btn-icon btn-icon-danger" @click="handleDelete" title="Smazat">
      <Trash2 :size="15" />
    </button>
  </div>
</template>

<style scoped>
.actions-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: flex-end;
  padding: var(--space-2) 0;
  border-top: 1px solid var(--border-color);
}

/* === ICON-ONLY BUTTON === */
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-icon:hover:not(:disabled) {
  color: var(--color-primary);
  transform: scale(1.15);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Primary variant (pro hlavní akce) */
.btn-icon-primary {
  color: var(--color-primary);
}

.btn-icon-primary:hover:not(:disabled) {
  color: var(--color-primary-hover);
  transform: scale(1.15);
}

/* Danger variant (pro destruktivní akce) */
.btn-icon-danger:hover:not(:disabled) {
  color: var(--color-danger);
  transform: scale(1.15);
}
</style>
```

**Kdy použít varianty:**

| Varianta | Použití | Příklad |
|----------|---------|---------|
| `.btn-icon` (default) | Standardní akce | Edit, Copy |
| `.btn-icon-primary` | Hlavní akce | Save, Confirm |
| `.btn-icon-danger` | Destruktivní akce | Delete, Remove |

**Výhody:**
- ✅ Kompaktní UI (24px místo 80px+)
- ✅ Mezinárodní (ikony = univerzální jazyk)
- ✅ Konzistentní velikost a chování
- ✅ Tooltip poskytuje kontext

**ZAKÁZÁNO:**
```vue
<!-- ❌ NIKDY toto nedělej -->
<button class="btn-large">
  <Icon />
  Dlouhý text
</button>

<!-- ✅ SPRÁVNĚ -->
<button class="btn-icon" title="Dlouhý text">
  <Icon :size="15" />
</button>
```

---

## 🛠️ TOOLING & WORKFLOW

### CSS Debug Overlay

**Aktivace:** `Ctrl+Shift+D` (v Dev režimu)

**Použití:**
1. Stiskni `Ctrl+Shift+D` → Zapne debug mode
2. Klikni na problémový widget → Zobrazí CSS issues
3. Čti "Issues" sekci → Návody na opravu
4. Oprav podle návrhů

**Časté problémy:**

| Problém | Příčina | Fix |
|---------|---------|-----|
| Widget useknutý | `overflow: hidden` + content přetéká | `overflow: auto` |
| Widget malý | Fixed height | `height: 100%; flex: 1` |
| Velký spacing | Hardcoded padding | `padding: var(--space-3)` |
| Špatné zarovnání | Chybí flex | `display: flex; flex-direction: column` |

### Claude.ai Prompt Template

**Pro generování nových widgetů:**

```
[Upload mockup screenshot]

Vytvoř Vue 3 <script setup> widget podle tohoto designu.

REQUIREMENTS:
✅ TypeScript
✅ Props: context?: { data?: YourType | null }
✅ Empty state: "No data"
✅ Design tokens: var(--space-3), var(--text-body), var(--color-primary)
✅ Container queries (NE @media)
✅ Fluid layout: height: 100%, flex: 1
✅ Base components z '@/components/base/'
✅ Max 200 LOC

ANTI-PATTERNS (NIKDY):
❌ height: 80px (žádné fixed heights)
❌ padding: 8px (jen design tokens)
❌ color: #fff (jen design tokens)
❌ @media queries (jen container queries)

Return COMPLETE .vue file ready to copy-paste.
```

**Pro CSS fixes:**

```
[Upload screenshot aktuálního UI]

Problém: [popis problému, např. "Widget má useknutý spodek"]

Oprav CSS podle těchto pravidel:
- height: 100% na root
- flex: 1 na content
- overflow: auto na scrollable části
- Žádné fixed heights
- Design tokens (var(--space-X))
- Container queries (NE @media)

Vrať jen CSS fix (ne celý soubor).
```

---

## 🚀 QUICK REFERENCE

### Checklist pro Nový Modul

```
□ Použij design tokens (var(--space-X))
□ Split-pane layout s resizable handlerem
□ Info ribbon s responzivním gridem
□ Icon toolbar s minimálním spacingem (1-2px)
□ Action buttons grid (4 cols → 2 cols responsive)
□ Window linking (contextStore.setContext)
□ Edit mode s inline forms
□ Modal integration (Copy, Delete)
□ Empty states
□ Container queries (NE media queries)
□ Fluid heights (height: 100%, flex: 1)
□ Žádné hardcoded hodnoty
```

### Rychlé Příkazy

```bash
# Najdi anti-patterns
grep -r "height: [0-9]" frontend/src/components/
grep -r "padding: [0-9]" frontend/src/components/
grep -r "@media" frontend/src/components/

# Dev server
python gestima.py run

# Tests
python gestima.py test
```

### Rychlé Copy-Paste Templates

**Split-Pane Module:**
```
frontend/src/components/modules/manufacturing/ManufacturingItemsModule.vue
```

**Info Ribbon:**
```vue
<!-- Viz Pattern 2 výše -->
```

**Action Buttons:**
```vue
<!-- Viz Pattern 3 výše -->
```

---

## 📝 CHANGELOG

### V8.2 (2026-02-03)
- ✅ **BREAKING:** Změna velikosti ikon z 14px na 15px (všechny Lucide ikony)
- ✅ Aktualizace CSS proměnné: --icon-size: 15px
- ✅ Hromadná změna 78 výskytů :size="14" → :size="15" napříč celou aplikací

### V8.2 (2026-02-02)
- ✅ **BREAKING:** Přidán Pattern 5: Icon-Only Buttons (STANDARD)
- ✅ ZAKÁZÁNO: Buttony s textem - POUZE ikony + tooltip
- ✅ Standardní velikost: 24px × 24px, ikona 15px
- ✅ Přidána CSS proměnná: --icon-size: 15px
- ✅ Implementováno v Quotes modulu (QuoteHeader, QuoteListPanel, QuoteDetailPanel)
- ✅ Varianty: default, primary, danger
- ✅ Hover efekt: scale(1.15) + barevná změna

### V8.1 (2026-02-02)
- ✅ Přidán Pattern 4: Context Ribbon pro Linked Moduly
- ✅ Dokumentace conditional rendering (part list)
- ✅ Manufacturing Items: Interní číslo + odstranění interní revize
- ✅ Větší spacing u icon toolbar
- ✅ Implementováno v Material/Operations/Pricing modulech

### V8.0 (2026-02-02)
- ✅ Přidán Split-Pane Module pattern
- ✅ Přidán Info Ribbon s Icon Toolbar pattern
- ✅ Přidán Action Buttons Grid pattern
- ✅ Přidán Window Linking pattern
- ✅ Dokumentace negativních margins
- ✅ Konsolidace všech aktuálních vzorů
- ✅ Real-world examples z Manufacturing Items

### V1.0 (2026-02-02)
- Initial version s base patterns

---

**🔒 END OF BIBLE V8.2**

**Toto je kompletní, konsolidovaná dokumentace všech UI vzorů používaných v Gestima.**
**Použij ji jako referenci při vytváření nových modulů.**
