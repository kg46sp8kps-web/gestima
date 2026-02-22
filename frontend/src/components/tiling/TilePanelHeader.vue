<script setup lang="ts">
/**
 * TilePanelHeader — 28px header with draggable tabs, module picker, maximize
 * Supports DnD of tabs between panels via HTML5 Drag API
 */

import { computed } from 'vue'
import { MODULE_REGISTRY } from './modules/moduleRegistry'
import type { TileModuleId } from '@/types/workspace'
import ModulePicker from './ModulePicker.vue'
import { Maximize2 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  panelId: string
  modules: TileModuleId[]
  activeModule: TileModuleId
  partNumber: string | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:activeModule': [moduleId: TileModuleId]
  'add-module': [moduleId: TileModuleId]
  'remove-module': [moduleId: TileModuleId]
  'receive-tab': [moduleId: TileModuleId, fromPanelId: string]
  'maximize': []
}>()

const tabs = computed(() =>
  props.modules.map(id => ({
    id,
    label: MODULE_REGISTRY[id].label,
    active: id === props.activeModule,
    draggable: props.modules.length > 1,
  }))
)

function handleTabClick(moduleId: TileModuleId) {
  emit('update:activeModule', moduleId)
}

// DnD handlers
function handleDragStart(e: DragEvent, moduleId: TileModuleId) {
  if (!e.dataTransfer || props.modules.length <= 1) return
  e.dataTransfer.setData('text/plain', JSON.stringify({
    moduleId,
    fromPanelId: props.panelId,
  }))
  e.dataTransfer.effectAllowed = 'move'
  document.body.classList.add('tab-dragging')
}

function handleDragEnd() {
  document.body.classList.remove('tab-dragging')
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  document.body.classList.remove('tab-dragging')
  if (!e.dataTransfer) return

  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'))
    if (data.fromPanelId !== props.panelId) {
      emit('receive-tab', data.moduleId, data.fromPanelId)
    }
  } catch {
    // Invalid drag data
  }
}
</script>

<template>
  <div
    class="ph"
    @dragover="handleDragOver"
    @drop="handleDrop"
    data-testid="tile-panel-header"
  >
    <!-- Part number hint -->
    <span v-if="partNumber" class="pht">
      <span class="pht-num">{{ partNumber }}</span>
    </span>

    <!-- Tabs -->
    <div class="ptabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="ptab"
        :class="{ on: tab.active }"
        :draggable="tab.draggable"
        @click="handleTabClick(tab.id)"
        @dragstart="handleDragStart($event, tab.id)"
        @dragend="handleDragEnd"
        :data-testid="`tab-${tab.id}`"
      >{{ tab.label }}</button>
    </div>

    <span class="phf" />

    <!-- Actions -->
    <div class="ph-actions">
      <ModulePicker
        :activeModules="modules"
        @add-module="emit('add-module', $event)"
        @remove-module="emit('remove-module', $event)"
      />
      <button
        class="pc"
        @click="emit('maximize')"
        title="Maximalizovat"
        data-testid="panel-maximize"
      >
        <Maximize2 :size="ICON_SIZE.SMALL" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.ph {
  height: 28px;
  background: rgba(255,255,255,0.025);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  padding: 0 var(--pad);
  gap: 4px;
  flex-shrink: 0;
  user-select: none;
}

.pht {
  font-size: var(--fsl);
  font-weight: 600;
  color: var(--t3);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
}

.pht-num {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: 2px;
  flex-shrink: 0;
}

/* Tabs */
.ptabs {
  display: flex;
  gap: 1px;
  margin-left: 3px;
}

.ptab {
  padding: 3px 7px;
  font-size: 10.5px;
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  transition: all 0.08s;
  font-family: inherit;
  white-space: nowrap;
}

.ptab:hover {
  color: var(--t3);
}

.ptab.on {
  color: var(--t1);
  background: var(--b1);
}

.ptab[draggable="true"] {
  cursor: grab;
}

.ptab[draggable="true"]:active {
  cursor: grabbing;
}

.phf { flex: 1; }

/* Actions */
.ph-actions {
  display: flex;
  gap: 2px;
  align-items: center;
}

.pc {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: var(--t4);
  cursor: pointer;
  font-size: 9px;
  transition: all 0.06s;
  font-family: var(--font);
}

.pc:hover {
  background: var(--b1);
  color: var(--t1);
}
</style>
