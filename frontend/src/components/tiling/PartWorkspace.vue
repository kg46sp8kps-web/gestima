<script setup lang="ts">
/**
 * PartWorkspace — Dynamic CSS Grid with TilePanel loop
 *
 * Replaces hardcoded GlassPanel + PartDetailTabs with:
 * - Store-driven panel array (from workspace.initializePanelsForPreset)
 * - TilePanel × N (each with tabs, ribbon, lazy-loaded modules)
 * - Create form overlay when creating a new part
 *
 * Presets:
 * - standard: 230px list + 1fr work
 * - comparison: 210px list + work + work + 210px list
 * - horizontal: 210px list (span 2) + work + work
 * - complete: 210px list (span 2) + work × 4 (2×2)
 */

import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWorkspaceStore } from '@/stores/workspace'
import { useWindowContextStore } from '@/stores/windowContext'
import { getPart } from '@/api/parts'
import type { LinkingGroup, TileModuleId } from '@/types/workspace'
import type { Part } from '@/types/part'

import TilePanel from './TilePanel.vue'
import PartCreateForm from '@/components/modules/parts/PartCreateForm.vue'

interface Props {
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: 'red',
})

const partsStore = usePartsStore()
const workspaceStore = useWorkspaceStore()
const contextStore = useWindowContextStore()

// Create form state
const isCreating = ref(false)
const creatingPanelId = ref<string | null>(null)

// Initialize panels on mount
onMounted(async () => {
  if (workspaceStore.panels.length === 0) {
    workspaceStore.initializePanelsForPreset()
  }
  if (partsStore.parts.length === 0) {
    await partsStore.fetchParts()
  }
})

// Computed
const panels = computed(() => workspaceStore.panels)
const presetConfig = computed(() => workspaceStore.getPresetConfig())

// Grid style from preset config
const gridStyle = computed(() => {
  const config = presetConfig.value
  return {
    gridTemplateColumns: config.gridTemplateColumns,
    gridTemplateRows: config.gridTemplateRows,
  }
})

// Panel grid areas from preset config
function getPanelGridArea(index: number): string | undefined {
  const config = presetConfig.value
  return config.panelDefaults[index]?.gridArea
}

// ── Part selection handler ──
function handlePartSelected(
  panelId: string,
  partId: number,
  partNumber: string,
  articleNumber: string | null,
) {
  if (isCreating.value) return

  // Update workspace store (propagates to all panels with same linkingGroup)
  workspaceStore.updatePanelPartId(panelId, partId, partNumber, articleNumber)

  // Update window context store for legacy components
  const panel = panels.value.find(p => p.id === panelId)
  if (panel?.linkingGroup) {
    contextStore.setContext(panel.linkingGroup, partId, partNumber, articleNumber)
  }
}

// ── Create new part ──
function handleCreateNew(panelId: string) {
  isCreating.value = true
  creatingPanelId.value = panelId
}

async function handlePartCreated(createdPart: Part) {
  isCreating.value = false

  if (creatingPanelId.value) {
    handlePartSelected(
      creatingPanelId.value,
      createdPart.id,
      createdPart.part_number,
      createdPart.article_number ?? null,
    )
  }
  creatingPanelId.value = null
}

function handleCancelCreate() {
  isCreating.value = false
  creatingPanelId.value = null
}

// ── Panel actions ──
function handleSetActiveModule(panelId: string, moduleId: TileModuleId) {
  workspaceStore.setPanelActiveModule(panelId, moduleId)
}

function handleAddModule(panelId: string, moduleId: TileModuleId) {
  workspaceStore.addModuleToPanel(panelId, moduleId)
}

function handleRemoveModule(panelId: string, moduleId: TileModuleId) {
  workspaceStore.removeModuleFromPanel(panelId, moduleId)
}

function handleReceiveTab(
  panelId: string,
  moduleId: TileModuleId,
  fromPanelId: string,
) {
  workspaceStore.moveModuleBetweenPanels(fromPanelId, panelId, moduleId)
}

function handleFocus(panelId: string) {
  workspaceStore.setFocusedPanel(panelId)
}
</script>

<template>
  <div
    class="tiling-grid"
    :data-preset="workspaceStore.layoutPreset"
    :style="gridStyle"
  >
    <TilePanel
      v-for="(panel, index) in panels"
      :key="panel.id"
      :panelId="panel.id"
      :modules="panel.modules"
      :activeModule="panel.activeModule"
      :partId="panel.partId"
      :partNumber="panel.partNumber"
      :articleNumber="panel.articleNumber"
      :linkingGroup="panel.linkingGroup"
      :focused="workspaceStore.focusedPanelId === panel.id"
      :enterDelay="index * 80"
      :style="getPanelGridArea(index) ? { gridArea: getPanelGridArea(index) } : undefined"
      @update:activeModule="handleSetActiveModule(panel.id, $event)"
      @update:partId="(id: number, num: string, art: string | null) => handlePartSelected(panel.id, id, num, art)"
      @add-module="handleAddModule(panel.id, $event)"
      @remove-module="handleRemoveModule(panel.id, $event)"
      @receive-tab="(modId: TileModuleId, fromId: string) => handleReceiveTab(panel.id, modId, fromId)"
      @create-new="handleCreateNew(panel.id)"
      @focus="handleFocus(panel.id)"
    />

    <!-- Create form overlay -->
    <Teleport to="body">
      <div v-if="isCreating" class="create-overlay" data-testid="create-overlay">
        <div class="create-card">
          <PartCreateForm
            @created="handlePartCreated"
            @cancel="handleCancelCreate"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tiling-grid {
  display: grid;
  gap: 3px;
  height: 100%;
  min-height: 0;
  transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Create form overlay */
.create-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
}

.create-card {
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  padding: 20px;
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}
</style>
