<script setup lang="ts">
/**
 * CustomizableModule.vue - Universal customizable module wrapper
 *
 * Main coordinator for widget-based modules.
 *
 * Features:
 * - Split-pane layout (optional left panel)
 * - Grid-based widget system (drag & drop, resize)
 * - Save/load custom layouts (localStorage)
 * - Add/remove widgets
 * - Reset to default
 * - Export/import layouts (JSON)
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 * @example
 * ```vue
 * <CustomizableModule
 *   :config="partDetailConfig"
 *   :context="{ part: selectedPart }"
 *   :left-panel-component="PartListPanel"
 *   @widget-action="handleAction"
 * />
 * ```
 */

import { ref, computed, onMounted, type Component } from 'vue'
import { Plus, RotateCcw, ChevronLeft, ChevronRight, Download, Upload } from 'lucide-vue-next'
import SplitPane from './SplitPane.vue'
import GridLayoutArea from './GridLayoutArea.vue'
import WidgetWrapper from './WidgetWrapper.vue'
import { useGridLayout } from '@/composables/useGridLayout'
import type { ModuleLayoutConfig, LayoutExport } from '@/types/widget'

interface Props {
  /**
   * Module layout configuration (widgets, defaults, etc.)
   */
  config: ModuleLayoutConfig

  /**
   * Data context passed to all widgets
   */
  context?: Record<string, any>

  /**
   * Optional left panel component (for split-pane)
   */
  leftPanelComponent?: Component

  /**
   * Can left panel be collapsed?
   */
  leftPanelCollapsible?: boolean

  /**
   * Is edit mode enabled by default?
   */
  editMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  context: () => ({}),
  leftPanelComponent: undefined,
  leftPanelCollapsible: true,
  editMode: false
})

const emit = defineEmits<{
  'widget-action': [widgetId: string, action: string, payload?: any]
}>()

// Grid layout state
const {
  layouts,
  updateLayout,
  resetToDefault,
  addWidget,
  removeWidget,
  loadLayout
} = useGridLayout(props.config.moduleKey, props.config)

// UI state
const showWidgetMenu = ref(false)
const leftPanelCollapsed = ref(false)
const isEditMode = ref(props.editMode)

// Available widgets (not yet added to layout and not required)
const availableWidgets = computed(() => {
  const layoutIds = layouts.value.map(l => l.i)
  return props.config.widgets.filter(
    w => !layoutIds.includes(w.id) && !w.required
  )
})

/**
 * Get widget definition by ID
 */
function getWidgetDefinition(widgetId: string) {
  return props.config.widgets.find(w => w.id === widgetId)
}

/**
 * Handle widget action (emitted from widget)
 */
function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  emit('widget-action', widgetId, action, payload)
}

/**
 * Add widget to layout
 */
function handleAddWidget(widgetId: string) {
  addWidget(widgetId)
  showWidgetMenu.value = false
}

/**
 * Remove widget from layout
 */
function handleRemoveWidget(widgetId: string) {
  removeWidget(widgetId)
}

/**
 * Reset layout to default
 */
function handleResetLayout() {
  if (confirm('Reset to default layout? Custom changes will be lost.')) {
    resetToDefault()
  }
}

/**
 * Toggle edit mode
 */
function toggleEditMode() {
  isEditMode.value = !isEditMode.value
}

/**
 * Export layout as JSON
 */
function exportLayout() {
  const data: LayoutExport = {
    moduleKey: props.config.moduleKey,
    layouts: layouts.value,
    version: 1,
    exportedAt: new Date().toISOString(),
    metadata: {
      name: `${props.config.moduleKey} layout`,
      density: document.documentElement.dataset.density as 'compact' | 'comfortable'
    }
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json'
  })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.config.moduleKey}-layout.json`
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Import layout from JSON
 */
async function importLayout() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'

  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const data = JSON.parse(text) as LayoutExport

      if (data.moduleKey !== props.config.moduleKey) {
        alert(`Layout is for module "${data.moduleKey}", but this is "${props.config.moduleKey}"`)
        return
      }

      updateLayout(data.layouts)
      alert('Layout imported successfully!')
    } catch (error) {
      console.error('Failed to import layout:', error)
      alert('Failed to import layout. Invalid file format.')
    }
  }

  input.click()
}

// Load layout on mount
onMounted(() => {
  loadLayout()
})
</script>

<template>
  <div class="customizable-module">
    <!-- Toolbar -->
    <div class="module-toolbar">
      <div class="toolbar-left">
        <!-- Toggle left panel -->
        <button
          v-if="leftPanelComponent && leftPanelCollapsible"
          @click="leftPanelCollapsed = !leftPanelCollapsed"
          class="btn btn-sm btn-secondary"
          :title="leftPanelCollapsed ? 'Show panel' : 'Hide panel'"
        >
          <ChevronRight v-if="leftPanelCollapsed" :size="14" />
          <ChevronLeft v-else :size="14" />
        </button>

        <!-- Edit mode toggle -->
        <button
          @click="toggleEditMode"
          class="btn btn-sm"
          :class="isEditMode ? 'btn-primary' : 'btn-secondary'"
          title="Toggle edit mode"
        >
          {{ isEditMode ? '✓ Edit Mode' : 'Edit Layout' }}
        </button>
      </div>

      <div class="toolbar-right">
        <!-- Add widget -->
        <button
          v-if="isEditMode && availableWidgets.length > 0"
          @click="showWidgetMenu = !showWidgetMenu"
          class="btn btn-sm btn-primary"
          title="Add widget"
        >
          <Plus :size="14" />
          Add Widget
        </button>

        <!-- Reset -->
        <button
          v-if="isEditMode"
          @click="handleResetLayout"
          class="btn btn-sm btn-secondary"
          title="Reset to default layout"
        >
          <RotateCcw :size="14" />
        </button>

        <!-- Export/Import -->
        <button
          @click="exportLayout"
          class="btn btn-sm btn-secondary"
          title="Export layout"
        >
          <Download :size="14" />
        </button>

        <button
          @click="importLayout"
          class="btn btn-sm btn-secondary"
          title="Import layout"
        >
          <Upload :size="14" />
        </button>
      </div>
    </div>

    <!-- Widget menu dropdown -->
    <div v-if="showWidgetMenu" class="widget-menu" @click.stop>
      <div class="widget-menu-header">
        <span>Available Widgets</span>
        <button @click="showWidgetMenu = false" class="btn-close">
          <Plus :size="14" style="transform: rotate(45deg)" />
        </button>
      </div>
      <button
        v-for="widget in availableWidgets"
        :key="widget.id"
        @click="handleAddWidget(widget.id)"
        class="widget-menu-item"
      >
        <span class="widget-menu-title">{{ widget.title }}</span>
        <span class="widget-menu-type">{{ widget.type }}</span>
      </button>
    </div>

    <!-- Layout -->
    <div class="module-content">
      <!-- With left panel (split-pane) -->
      <SplitPane
        v-if="leftPanelComponent"
        :left-collapsed="leftPanelCollapsed"
        :storage-key="`${config.moduleKey}-split`"
      >
        <template #left>
          <component :is="leftPanelComponent" v-bind="$attrs" />
        </template>

        <template #right>
          <GridLayoutArea
            :layouts="layouts"
            :cols="config.cols"
            :row-height="config.rowHeight"
            :is-draggable="isEditMode"
            :is-resizable="isEditMode"
            @update:layouts="updateLayout"
          >
            <template #widget="{ widget }">
              <WidgetWrapper
                :definition="getWidgetDefinition(widget.i)!"
                :context="context"
                :edit-mode="isEditMode"
                @action="handleWidgetAction(widget.i, $event)"
                @remove="handleRemoveWidget(widget.i)"
              />
            </template>
          </GridLayoutArea>
        </template>
      </SplitPane>

      <!-- No left panel (full width grid) -->
      <GridLayoutArea
        v-else
        :layouts="layouts"
        :cols="config.cols"
        :row-height="config.rowHeight"
        :is-draggable="isEditMode"
        :is-resizable="isEditMode"
        @update:layouts="updateLayout"
      >
        <template #widget="{ widget }">
          <WidgetWrapper
            :definition="getWidgetDefinition(widget.i)!"
            :context="context"
            :edit-mode="isEditMode"
            @action="handleWidgetAction(widget.i, $event)"
            @remove="handleRemoveWidget(widget.i)"
          />
        </template>
      </GridLayoutArea>
    </div>
  </div>
</template>

<style scoped>
.customizable-module {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.module-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
  gap: var(--space-2);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: var(--space-2);
}

.module-content {
  flex: 1;
  overflow: hidden;
}

/* Widget Menu Dropdown */
.widget-menu {
  position: absolute;
  top: 48px;
  right: var(--space-3);
  min-width: 280px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  max-height: 400px;
  overflow-y: auto;
}

.widget-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.btn-close {
  display: flex;
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
  transition: var(--transition-fast);
}

.btn-close:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.widget-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-body);
  font-size: var(--text-sm);
  transition: var(--transition-fast);
  gap: var(--space-2);
}

.widget-menu-item:hover {
  background: var(--state-hover);
}

.widget-menu-title {
  flex: 1;
  font-weight: var(--font-medium);
}

.widget-menu-type {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
}
</style>
