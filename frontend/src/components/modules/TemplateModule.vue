<script setup lang="ts">
/**
 * Template Module - Showcase for split-pane layout + responsive design
 *
 * DUMMY DATA - testing H/V layout + CSS container queries
 */

import { ref, onMounted, computed, watch } from 'vue'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import { Plus, Search, Filter, Download, RefreshCw, Settings, Save, X } from 'lucide-vue-next'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

// Layout settings
const { layoutMode } = usePartLayoutSettings('template')

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

// Edit mode (WYSIWYG)
const editMode = ref(false)
const totalWidth = ref(1200) // Will be calculated from actual window size

// Computed values for live display
const leftPanelWidth = computed(() => panelSize.value)
const rightPanelWidth = computed(() => totalWidth.value - panelSize.value - 4) // -4 for resize handle

// Window dimensions
const windowWidth = ref(1200)
const windowHeight = ref(800)

// Grid areas in right panel (heights in px)
const gridAreas = ref({
  header: 80,
  infoGrid: 120,
  stats: 180,
  description: 150
})

// Grid area constraints and glue settings
type GridAreaKey = 'header' | 'infoGrid' | 'stats' | 'description'

const gridConfig = ref<Record<GridAreaKey, {
  min: number
  max: number
  glue: Record<string, boolean>
}>>({
  header: {
    min: 60,
    max: 200,
    glue: { top: true, fillWidth: true }
  },
  infoGrid: {
    min: 100,
    max: 400,
    glue: { fillWidth: true }
  },
  stats: {
    min: 120,
    max: 500,
    glue: { fillWidth: true }
  },
  description: {
    min: 80,
    max: 400,
    glue: { bottom: true, fillWidth: true, fillRemaining: true }
  }
})

// Selected grid area for property panel
const selectedArea = ref<GridAreaKey | null>(null)

// Dragging state for grid areas
const gridDragging = ref<string | null>(null)

// Search & filter
const searchQuery = ref('')
const filterStatus = ref<string | null>(null)

// Dummy data (25 items)
const allItems = [
  { id: 1, name: 'Component Alpha', code: 'CMP-001', status: 'active', quantity: 150, price: 245.50 },
  { id: 2, name: 'Widget Beta', code: 'WDG-002', status: 'pending', quantity: 80, price: 189.99 },
  { id: 3, name: 'Module Gamma', code: 'MOD-003', status: 'completed', quantity: 200, price: 399.00 },
  { id: 4, name: 'Part Delta', code: 'PRT-004', status: 'active', quantity: 45, price: 125.75 },
  { id: 5, name: 'Assembly Epsilon', code: 'ASM-005', status: 'pending', quantity: 120, price: 567.80 },
  { id: 6, name: 'Fixture Zeta', code: 'FIX-006', status: 'active', quantity: 90, price: 234.20 },
  { id: 7, name: 'Tool Eta', code: 'TOL-007', status: 'completed', quantity: 65, price: 445.30 },
  { id: 8, name: 'Bracket Theta', code: 'BRK-008', status: 'active', quantity: 180, price: 89.50 },
  { id: 9, name: 'Housing Iota', code: 'HSG-009', status: 'pending', quantity: 55, price: 678.90 },
  { id: 10, name: 'Connector Kappa', code: 'CON-010', status: 'active', quantity: 300, price: 45.25 },
  { id: 11, name: 'Sensor Lambda', code: 'SNS-011', status: 'completed', quantity: 70, price: 156.40 },
  { id: 12, name: 'Controller Mu', code: 'CTL-012', status: 'active', quantity: 40, price: 890.00 },
  { id: 13, name: 'Display Nu', code: 'DSP-013', status: 'pending', quantity: 95, price: 345.60 },
  { id: 14, name: 'Cable Xi', code: 'CBL-014', status: 'active', quantity: 500, price: 12.30 },
  { id: 15, name: 'Switch Omicron', code: 'SWT-015', status: 'completed', quantity: 110, price: 67.80 },
  { id: 16, name: 'Motor Pi', code: 'MTR-016', status: 'active', quantity: 25, price: 1250.00 },
  { id: 17, name: 'Valve Rho', code: 'VLV-017', status: 'pending', quantity: 85, price: 234.50 },
  { id: 18, name: 'Pump Sigma', code: 'PMP-018', status: 'active', quantity: 35, price: 890.75 },
  { id: 19, name: 'Filter Tau', code: 'FLT-019', status: 'completed', quantity: 140, price: 78.90 },
  { id: 20, name: 'Bearing Upsilon', code: 'BRG-020', status: 'active', quantity: 200, price: 34.20 },
  { id: 21, name: 'Seal Phi', code: 'SEL-021', status: 'pending', quantity: 450, price: 8.50 },
  { id: 22, name: 'Gasket Chi', code: 'GSK-022', status: 'active', quantity: 600, price: 5.25 },
  { id: 23, name: 'Spring Psi', code: 'SPR-023', status: 'completed', quantity: 380, price: 15.60 },
  { id: 24, name: 'Fastener Omega', code: 'FST-024', status: 'active', quantity: 1000, price: 2.30 },
  { id: 25, name: 'Plate Alpha-2', code: 'PLT-025', status: 'pending', quantity: 75, price: 145.80 }
]

const items = computed(() => {
  let filtered = allItems

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(item =>
      item.name.toLowerCase().includes(query) ||
      item.code.toLowerCase().includes(query)
    )
  }

  if (filterStatus.value) {
    filtered = filtered.filter(item => item.status === filterStatus.value)
  }

  return filtered
})

type ItemType = { id: number; name: string; code: string; status: string; quantity: number; price: number }
const selectedItem = ref<ItemType>(allItems[0]!)

// Load panel size from localStorage
onMounted(() => {
  // Load saved layout config
  const stored = localStorage.getItem('templateLayoutConfig')
  if (stored) {
    try {
      const config = JSON.parse(stored)
      if (config.panelSize) panelSize.value = config.panelSize
      if (config.windowWidth) windowWidth.value = config.windowWidth
      if (config.windowHeight) windowHeight.value = config.windowHeight
      if (config.gridAreas) gridAreas.value = { ...gridAreas.value, ...config.gridAreas }
      if (config.gridConfig) gridConfig.value = { ...gridConfig.value, ...config.gridConfig }
    } catch (e) {
      console.warn('Failed to load layout config:', e)
    }
  }

  // Calculate dimensions from container
  updateTotalWidth()
  updateWindowDimensions()

  // Update on window resize
  const onResize = () => {
    updateTotalWidth()
    updateWindowDimensions()
  }
  window.addEventListener('resize', onResize)

  // NO AUTO-LAYOUT - user edits manually only
})

// Update total width for live display
function updateTotalWidth() {
  const container = document.querySelector('.split-layout') as HTMLElement
  if (container) {
    totalWidth.value = container.offsetWidth
  }
}

// Update window dimensions
function updateWindowDimensions() {
  const container = document.querySelector('.split-layout') as HTMLElement
  if (container) {
    windowWidth.value = container.offsetWidth
    windowHeight.value = container.offsetHeight

    // Auto-adjust grid areas when window resizes - DISABLED (buggy)
    // recalculateGridAreas()
  }
}

// Recalculate grid area sizes based on available space and constraints
function recalculateGridAreas() {
  const secondPanel = document.querySelector('.second-panel') as HTMLElement
  if (!secondPanel) return

  const availableHeight = secondPanel.offsetHeight

  // Calculate total current height and constraints
  const areas = ['header', 'infoGrid', 'stats', 'description'] as const
  let totalMin = 0
  let totalMax = 0
  let totalCurrent = 0

  areas.forEach(area => {
    const config = gridConfig.value[area as keyof typeof gridConfig.value]
    totalMin += config.min
    totalMax += config.max
    totalCurrent += gridAreas.value[area as keyof typeof gridAreas.value]
  })

  // If available space is less than total min, scale down proportionally (but respect mins)
  if (availableHeight < totalMin) {
    areas.forEach(area => {
      gridAreas.value[area as keyof typeof gridAreas.value] = gridConfig.value[area as keyof typeof gridConfig.value].min
    })
    return
  }

  // If available space is more than total max, scale up proportionally (but respect maxs)
  if (availableHeight > totalMax) {
    // Find areas with fillRemaining
    const fillAreas = areas.filter(area => gridConfig.value[area as keyof typeof gridConfig.value].glue.fillRemaining)

    if (fillAreas.length > 0) {
      // Set non-fill areas to their current size (or max)
      let usedHeight = 0
      areas.forEach(area => {
        if (!gridConfig.value[area as keyof typeof gridConfig.value].glue.fillRemaining) {
          gridAreas.value[area as keyof typeof gridAreas.value] = Math.min(gridAreas.value[area as keyof typeof gridAreas.value], gridConfig.value[area as keyof typeof gridConfig.value].max)
          usedHeight += gridAreas.value[area as keyof typeof gridAreas.value]
        }
      })

      // Distribute remaining space to fill areas
      const remainingHeight = availableHeight - usedHeight
      const heightPerFillArea = remainingHeight / fillAreas.length

      fillAreas.forEach(area => {
        gridAreas.value[area as keyof typeof gridAreas.value] = Math.max(
          gridConfig.value[area as keyof typeof gridConfig.value].min,
          Math.min(gridConfig.value[area as keyof typeof gridConfig.value].max, heightPerFillArea)
        )
      })
    } else {
      // No fill areas - just max out everything
      areas.forEach(area => {
        gridAreas.value[area as keyof typeof gridAreas.value] = gridConfig.value[area as keyof typeof gridConfig.value].max
      })
    }
    return
  }

  // Available space is between min and max - scale proportionally
  const scale = availableHeight / totalCurrent

  areas.forEach(area => {
    const config = gridConfig.value[area as keyof typeof gridConfig.value]
    const newHeight = gridAreas.value[area as keyof typeof gridAreas.value] * scale

    // Apply constraints
    gridAreas.value[area as keyof typeof gridAreas.value] = Math.max(config.min, Math.min(config.max, newHeight))
  })
}

// Toggle edit mode
function toggleEditMode() {
  editMode.value = !editMode.value
}

// Save current layout (explicit save)
async function saveLayout() {
  const layoutConfig = {
    panelSize: panelSize.value,
    windowWidth: windowWidth.value,
    windowHeight: windowHeight.value,
    gridAreas: gridAreas.value,
    gridConfig: gridConfig.value
  }

  localStorage.setItem('templateLayoutConfig', JSON.stringify(layoutConfig))
  console.log('✅ Layout saved:', layoutConfig)

  // Show success feedback
  await alert({
    title: 'Úspěch',
    message: `Layout saved!\n` +
      `Window: ${windowWidth.value}×${windowHeight.value}px\n` +
      `Split: ${panelSize.value}px / ${rightPanelWidth.value}px\n` +
      `Grid: H${gridAreas.value.header} | I${gridAreas.value.infoGrid} | S${gridAreas.value.stats} | D${gridAreas.value.description}\n` +
      `Constraints & Glues saved!`,
    type: 'success'
  })
}

// Resize grid area
function startGridResize(area: 'header' | 'infoGrid' | 'stats', event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  gridDragging.value = area

  const startY = event.clientY
  const startHeight = gridAreas.value[area as keyof typeof gridAreas.value]
  const config = gridConfig.value[area as keyof typeof gridConfig.value]

  const onMove = (e: MouseEvent) => {
    const delta = e.clientY - startY
    const newHeight = Math.max(config.min, Math.min(config.max, startHeight + delta))
    gridAreas.value[area as keyof typeof gridAreas.value] = newHeight
  }

  const onUp = () => {
    gridDragging.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// Select grid area for editing
function selectGridArea(area: GridAreaKey) {
  selectedArea.value = selectedArea.value === area ? null : area
}

// Custom resize handler that works for both horizontal and vertical
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
    localStorage.setItem('templatePanelSize', panelSize.value.toString())
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Dynamic layout classes
const layoutClasses = computed(() => ({
  'layout-vertical': layoutMode.value === 'vertical',
  'layout-horizontal': layoutMode.value === 'horizontal'
}))

// Dynamic resize cursor
const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)

function selectItem(item: typeof items.value[0]) {
  selectedItem.value = item
}
</script>

<template>
  <div class="split-layout" :class="layoutClasses">
    <!-- WYSIWYG TOOLBAR (Floating) -->
    <div v-if="editMode" class="wysiwyg-toolbar">
      <div class="toolbar-section">
        <span class="toolbar-title">📐 Layout Editor</span>
        <div class="toolbar-values">
          <!-- Window Size -->
          <span class="value-group">
            <span class="value-label">Window:</span>
            <strong>{{ windowWidth }}×{{ windowHeight }}</strong>
          </span>
          <span class="value-separator">|</span>

          <!-- Split Pane -->
          <span class="value-group">
            <span class="value-label">Split:</span>
            <strong>{{ leftPanelWidth }}</strong> / <strong>{{ rightPanelWidth }}</strong>
          </span>
          <span class="value-separator">|</span>

          <!-- Grid Areas -->
          <span class="value-group">
            <span class="value-label">Grid:</span>
            <strong>H{{ gridAreas.header }}</strong> |
            <strong>I{{ gridAreas.infoGrid }}</strong> |
            <strong>S{{ gridAreas.stats }}</strong> |
            <strong>D{{ gridAreas.description }}</strong>
          </span>
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="btn-toolbar btn-save" @click="saveLayout" title="Save layout">
          <Save :size="ICON_SIZE.SMALL" />
          Save
        </button>
        <button class="btn-toolbar btn-close" @click="toggleEditMode" title="Exit edit mode">
          <X :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </div>

    <!-- EDIT MODE TOGGLE (Bottom-right corner) -->
    <button
      v-if="!editMode"
      class="btn-edit-mode"
      @click="toggleEditMode"
      title="Enter layout edit mode"
    >
      <Settings :size="ICON_SIZE.STANDARD" />
    </button>

    <!-- PROPERTY PANEL (Right side) -->
    <div v-if="editMode && selectedArea" class="property-panel">
      <div class="property-header">
        <h4>{{ selectedArea === 'header' ? 'Header' : selectedArea === 'infoGrid' ? 'Info Grid' : selectedArea === 'stats' ? 'Statistics' : 'Description' }}</h4>
        <button @click="selectedArea = null" class="btn-close-panel">×</button>
      </div>

      <div class="property-body">
        <!-- Current Height -->
        <div class="property-group">
          <label class="property-label">Current Height</label>
          <div class="property-value">{{ gridAreas[selectedArea] }}px</div>
        </div>

        <!-- Min/Max Constraints -->
        <div class="property-group">
          <label class="property-label">Min Height</label>
          <input
            type="number"
            v-model.number="gridConfig[selectedArea].min"
            class="property-input"
            min="40"
            max="1000"
            step="10"
          />
        </div>

        <div class="property-group">
          <label class="property-label">Max Height</label>
          <input
            type="number"
            v-model.number="gridConfig[selectedArea].max"
            class="property-input"
            min="40"
            max="1000"
            step="10"
          />
        </div>

        <!-- Glue Settings -->
        <div class="property-section">
          <h5>Glue System</h5>

          <label class="property-checkbox">
            <input type="checkbox" v-model="gridConfig[selectedArea].glue.top" />
            <span>Stick to top edge</span>
          </label>

          <label class="property-checkbox">
            <input type="checkbox" v-model="gridConfig[selectedArea].glue.bottom" />
            <span>Stick to bottom edge</span>
          </label>

          <label class="property-checkbox">
            <input type="checkbox" v-model="gridConfig[selectedArea].glue.fillWidth" />
            <span>Fill full width</span>
          </label>

          <label class="property-checkbox">
            <input type="checkbox" v-model="gridConfig[selectedArea].glue.fillRemaining" />
            <span>Fill remaining space</span>
          </label>
        </div>

        <!-- Info -->
        <div class="property-info">
          💡 Changes apply immediately. Click Save to persist.
        </div>
      </div>
    </div>
    <!-- FIRST PANEL: List with Toolbar -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
      <!-- TOOLBAR -->
      <div class="toolbar">
        <div class="toolbar-left">
          <button class="icon-btn icon-btn-primary" title="Create New">
            <Plus :size="ICON_SIZE.STANDARD" />
          </button>
          <div class="search-box">
            <Search :size="ICON_SIZE.SMALL" class="search-icon" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search..."
              class="search-input"
            />
          </div>
        </div>
        <div class="toolbar-right">
          <button class="icon-btn" @click="filterStatus = filterStatus ? null : 'active'" :class="{ active: filterStatus }" title="Filter">
            <Filter :size="ICON_SIZE.STANDARD" />
          </button>
          <button class="icon-btn btn-refresh" title="Refresh">
            <RefreshCw :size="ICON_SIZE.STANDARD" />
          </button>
          <button class="icon-btn btn-export" title="Export">
            <Download :size="ICON_SIZE.STANDARD" />
          </button>
        </div>
      </div>

      <!-- TABLE (responsive with container queries) -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th class="col-code">Code</th>
              <th class="col-name">Name</th>
              <th class="col-qty">Qty</th>
              <th class="col-price">Price</th>
              <th class="col-status">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in items"
              :key="item.id"
              class="data-row"
              :class="{ 'is-selected': selectedItem.id === item.id }"
              @click="selectItem(item)"
            >
              <td class="col-code">{{ item.code }}</td>
              <td class="col-name">{{ item.name }}</td>
              <td class="col-qty">{{ item.quantity }}</td>
              <td class="col-price">${{ item.price.toFixed(2) }}</td>
              <td class="col-status">
                <span class="badge" :class="`badge-${item.status}`">
                  {{ item.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Detail (responsive grid) -->
    <div v-if="selectedItem" class="second-panel" :class="{ 'edit-mode-active': editMode }">
      <!-- HEADER AREA -->
      <div
        class="grid-area detail-header"
        :class="{ 'area-selected': selectedArea === 'header' }"
        :style="{ height: `${gridAreas.header}px` }"
        @click="editMode ? selectGridArea('header') : null"
      >
        <h3>{{ selectedItem.name }}</h3>
        <div class="detail-actions">
          <button class="btn btn-secondary">Edit</button>
          <button class="btn btn-danger">Delete</button>
        </div>
      </div>

      <!-- RESIZE HANDLE: Header ↔ Info Grid -->
      <div
        v-if="editMode"
        class="grid-resize-handle"
        :class="{ dragging: gridDragging === 'header' }"
        @mousedown="startGridResize('header', $event)"
        title="Resize Header"
      >
        <span class="handle-label">H: {{ gridAreas.header }}px</span>
      </div>

      <!-- INFO GRID AREA -->
      <div
        class="grid-area info-grid"
        :class="{ 'area-selected': selectedArea === 'infoGrid' }"
        :style="{ height: `${gridAreas.infoGrid}px` }"
        @click="editMode ? selectGridArea('infoGrid') : null"
      >
        <div class="info-card">
          <label>Code</label>
          <span class="value">{{ selectedItem.code }}</span>
        </div>
        <div class="info-card">
          <label>Status</label>
          <span class="badge" :class="`badge-${selectedItem.status}`">
            {{ selectedItem.status }}
          </span>
        </div>
        <div class="info-card">
          <label>Quantity</label>
          <span class="value">{{ selectedItem.quantity }} pcs</span>
        </div>
        <div class="info-card">
          <label>Price</label>
          <span class="value">${{ selectedItem.price.toFixed(2) }}</span>
        </div>
      </div>

      <!-- RESIZE HANDLE: Info Grid ↔ Stats -->
      <div
        v-if="editMode"
        class="grid-resize-handle"
        :class="{ dragging: gridDragging === 'infoGrid' }"
        @mousedown="startGridResize('infoGrid', $event)"
        title="Resize Info Grid"
      >
        <span class="handle-label">I: {{ gridAreas.infoGrid }}px</span>
      </div>

      <!-- STATS AREA -->
      <div
        class="grid-area stats-section"
        :class="{ 'area-selected': selectedArea === 'stats' }"
        :style="{ height: `${gridAreas.stats}px` }"
        @click="editMode ? selectGridArea('stats') : null"
      >
        <h4>Statistics</h4>
        <table class="stats-table">
          <tr>
            <td>Total Value:</td>
            <td class="value">${{ (selectedItem.quantity * selectedItem.price).toFixed(2) }}</td>
          </tr>
          <tr>
            <td>Unit Weight:</td>
            <td class="value">2.5 kg</td>
          </tr>
          <tr>
            <td>Lead Time:</td>
            <td class="value">14 days</td>
          </tr>
          <tr>
            <td>Supplier:</td>
            <td class="value">Acme Corp</td>
          </tr>
        </table>
      </div>

      <!-- RESIZE HANDLE: Stats ↔ Description -->
      <div
        v-if="editMode"
        class="grid-resize-handle"
        :class="{ dragging: gridDragging === 'stats' }"
        @mousedown="startGridResize('stats', $event)"
        title="Resize Stats"
      >
        <span class="handle-label">S: {{ gridAreas.stats }}px</span>
      </div>

      <!-- DESCRIPTION AREA -->
      <div
        class="grid-area description-section"
        :class="{ 'area-selected': selectedArea === 'description' }"
        :style="{ minHeight: `${gridAreas.description}px` }"
        @click="editMode ? selectGridArea('description') : null"
      >
        <h4>Description</h4>
        <p>This is a demonstration of responsive split-pane layout with CSS container queries.
        The table columns and detail grid automatically adapt based on available space.</p>
        <p><strong>Try resizing the panels and switching between Horizontal/Vertical modes!</strong></p>
        <p v-if="editMode" class="edit-hint">🎨 Edit mode: Click areas to edit constraints & glues</p>
      </div>
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

/* Layout modes */
.split-layout.layout-horizontal {
  flex-direction: column; /* Horizontal split = stacked (nad sebou) */
}

.split-layout.layout-vertical {
  flex-direction: row; /* Vertical split = side by side (vedle sebe) */
}

/* === FIRST PANEL (with container queries) === */
.first-panel {
  flex-shrink: 0;
  padding: var(--space-3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  container-type: inline-size; /* Enable container queries */
  container-name: list-panel;
}

.layout-vertical .first-panel {
  height: 100%;
}

.layout-horizontal .first-panel {
  width: 100%;
}

/* === TOOLBAR === */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: var(--text-secondary);
  pointer-events: none;
}

.search-input {
  padding: 6px 8px 6px 32px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: var(--text-sm);
  width: 200px;
  transition: all var(--duration-fast) var(--ease-out);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(153, 27, 27, 0.1);
}

/* Container queries: progressive hiding based on width */
@container list-panel (max-width: 500px) {
  .btn-export {
    display: none;
  }
}

@container list-panel (max-width: 400px) {
  .search-box {
    display: none;
  }
}

@container list-panel (max-width: 350px) {
  .btn-refresh {
    display: none;
  }
}

/* Very narrow: stack toolbar vertically */
@container list-panel (max-width: 280px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
    justify-content: center;
  }
}

/* === TABLE CONTAINER === */
.table-container {
  flex: 1;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  container-type: inline-size;
  container-name: table;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table thead {
  background: var(--bg-secondary);
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table th {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--border-color);
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-light);
}

.data-row {
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.data-row:hover {
  background: var(--state-hover);
}

.data-row.is-selected {
  background: var(--accent-subtle);
  border-left: 3px solid var(--color-primary);
}

/* Responsive columns with container queries */
.col-price,
.col-qty {
  text-align: right;
}

/* Hide less important columns on narrow width */
@container table (max-width: 500px) {
  .col-price,
  .col-qty {
    display: none;
  }
}

@container table (max-width: 350px) {
  .col-code {
    display: none;
  }
}

/* === RESIZE HANDLE === */
.resize-handle {
  background: var(--border-default);
  flex-shrink: 0;
  transition: background var(--transition-fast);
  position: relative;
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

/* Wider hit area for easier dragging */
.layout-vertical .resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -4px;
  bottom: -4px;
  cursor: row-resize;
}

/* === SECOND PANEL (with container queries) === */
.second-panel {
  flex: 1;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
  container-type: inline-size;
  container-name: detail-panel;
}

.layout-vertical .second-panel {
  height: 100%;
}

.layout-horizontal .second-panel {
  width: 100%;
}

/* Detail Header */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border-color);
}

.detail-header h3 {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: var(--space-2);
}

/* Info Grid (responsive with container queries) */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
}

/* Adjust grid on narrow width */
@container detail-panel (max-width: 400px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}

.info-card {
  background: var(--bg-secondary);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.info-card label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-1);
}

.info-card .value {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

/* Stats Section */
.stats-section h4,
.description-section h4 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-2) 0;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
}

.stats-table tr {
  border-bottom: 1px solid var(--border-light);
}

.stats-table td {
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
}

.stats-table td:first-child {
  color: var(--text-secondary);
  font-weight: 500;
}

.stats-table td.value {
  text-align: right;
  color: var(--text-primary);
  font-weight: 600;
}

/* Description Section */
.description-section p {
  margin: 0 0 var(--space-2) 0;
  line-height: 1.6;
  color: var(--text-secondary);
}

/* === BADGES === */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
}

.badge-active {
  background: #dcfce7;
  color: #166534;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.badge-completed {
  background: #dbeafe;
  color: #1e40af;
}

/* === BUTTONS === */
.btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  border: none;
  white-space: nowrap;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background: #7f1d1d;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
}

/* === WYSIWYG TOOLBAR === */
.wysiwyg-toolbar {
  position: fixed;
  bottom: 80px; /* Above floating window footer */
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;

  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);

  background: var(--bg-surface);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);

  font-size: var(--text-sm);
  font-weight: 500;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.toolbar-title {
  color: var(--text-primary);
  font-weight: 600;
}

.toolbar-values {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-secondary);
}

.value-item strong {
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.value-separator {
  color: var(--border-color);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-save {
  background: var(--color-primary);
  color: white;
}

.btn-save:hover {
  background: #7f1d1d;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(153, 27, 27, 0.3);
}

.btn-close {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: var(--space-2);
}

.btn-close:hover {
  background: var(--state-hover);
}

/* Edit Mode Toggle Button (Bottom-right corner) */
.btn-edit-mode {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;

  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;

  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-edit-mode:hover {
  background: #7f1d1d;
  transform: scale(1.1) rotate(90deg);
  box-shadow: 0 6px 20px rgba(153, 27, 27, 0.3);
}

/* Highlight resize handle in edit mode */
.wysiwyg-toolbar ~ * .resize-handle {
  background: var(--color-primary);
  width: 6px;
}

.wysiwyg-toolbar ~ * .resize-handle:hover {
  background: #7f1d1d;
  width: 8px;
}

/* === GRID AREAS === */
.grid-area {
  overflow: auto;
  transition: all var(--duration-fast) var(--ease-out);
}

.edit-mode-active .grid-area {
  border: 2px dashed var(--border-color);
  position: relative;
}

.edit-mode-active .grid-area:hover {
  border-color: var(--color-primary);
  background: rgba(153, 27, 27, 0.02);
}

/* Grid Resize Handles */
.grid-resize-handle {
  height: 8px;
  background: var(--color-primary);
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 10;
}

.grid-resize-handle:hover {
  height: 12px;
  background: #7f1d1d;
}

.grid-resize-handle.dragging {
  height: 16px;
  background: #991b1b;
  box-shadow: 0 0 12px rgba(153, 27, 27, 0.5);
}

.handle-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: white;
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  user-select: none;
}

.edit-hint {
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--palette-info-bg);
  color: var(--palette-info);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
}

/* Toolbar value groups */
.value-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.value-label {
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  font-weight: 500;
  text-transform: uppercase;
}

/* === PROPERTY PANEL === */
.property-panel {
  position: fixed;
  top: 80px;
  right: 24px;
  width: 300px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;

  background: var(--bg-surface);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 1001;
}

.property-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.property-header h4 {
  margin: 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
  font-weight: 600;
}

.btn-close-panel {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.btn-close-panel:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.property-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.property-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.property-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.property-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.property-input {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-base);
  font-family: var(--font-mono);
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.property-input:focus {
  outline: none;
  border-color: var(--color-primary);
  background: var(--bg-base);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

.property-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-color);
}

.property-section h5 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.property-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
}

.property-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

.property-checkbox span {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.property-info {
  padding: var(--space-3);
  background: var(--palette-info-bg);
  color: var(--palette-info);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 500;
}

/* Selected grid area */
.edit-mode-active .grid-area {
  cursor: pointer;
}

.area-selected {
  border-color: var(--color-primary) !important;
  border-style: solid !important;
  border-width: 3px !important;
  background: rgba(153, 27, 27, 0.05) !important;
  box-shadow: 0 0 0 4px rgba(153, 27, 27, 0.1);
}
</style>
