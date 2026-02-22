<script setup lang="ts">
/**
 * TilePanel — universal panel container for tiling workspace
 *
 * Renders: TilePanelHeader (tabs + DnD) → TileRibbon (part info) → Module content
 * Uses defineAsyncComponent for lazy-loaded module rendering
 * v-show for tab switching (preserves module state across tab changes)
 */

import { computed, defineAsyncComponent, ref } from 'vue'
import { MODULE_REGISTRY } from './modules/moduleRegistry'
import type { TileModuleId, LinkingGroup } from '@/types/workspace'
import type { Part } from '@/types/part'
import TilePanelHeader from './TilePanelHeader.vue'
import TileRibbon from './TileRibbon.vue'
import GlassPanel from './GlassPanel.vue'

interface Props {
  panelId: string
  modules: TileModuleId[]
  activeModule: TileModuleId
  partId: number | null
  partNumber: string | null
  articleNumber: string | null
  linkingGroup: LinkingGroup
  focused?: boolean
  enterDelay?: number
}

const props = withDefaults(defineProps<Props>(), {
  focused: false,
  enterDelay: 0,
})

const emit = defineEmits<{
  'update:activeModule': [moduleId: TileModuleId]
  'update:partId': [partId: number, partNumber: string, articleNumber: string | null]
  'add-module': [moduleId: TileModuleId]
  'remove-module': [moduleId: TileModuleId]
  'receive-tab': [moduleId: TileModuleId, fromPanelId: string]
  'create-new': []
  'focus': []
}>()

const isMaximized = ref(false)

// Whether any module in this panel needs a part
const showRibbon = computed(() =>
  props.modules.some(id => MODULE_REGISTRY[id].needsPart)
)

// Create async components for each module
const moduleComponents = computed(() => {
  const map: Record<string, ReturnType<typeof defineAsyncComponent>> = {}
  for (const id of props.modules) {
    const def = MODULE_REGISTRY[id]
    map[id] = defineAsyncComponent(def.component as () => Promise<{ default: unknown }>)
  }
  return map
})

function handleMaximize() {
  isMaximized.value = !isMaximized.value
}

// Handle select-part from TilePartsList
function handleSelectPart(part: Part) {
  emit('update:partId', part.id, part.part_number, part.article_number ?? null)
}

function handleCreateNew() {
  emit('create-new')
}
</script>

<template>
  <GlassPanel
    :linkingGroup="linkingGroup"
    :showCorners="true"
    :showHeader="false"
    :focused="focused"
    :enterDelay="enterDelay"
    :class="{ maximized: isMaximized }"
    @mousedown="emit('focus')"
  >
    <div class="tile-panel">
      <!-- Header with tabs -->
      <TilePanelHeader
        :panelId="panelId"
        :modules="modules"
        :activeModule="activeModule"
        :partNumber="partNumber"
        @update:activeModule="emit('update:activeModule', $event)"
        @add-module="emit('add-module', $event)"
        @remove-module="emit('remove-module', $event)"
        @receive-tab="(modId, fromId) => emit('receive-tab', modId, fromId)"
        @maximize="handleMaximize"
      />

      <!-- Ribbon (only if panel has part-requiring modules) -->
      <TileRibbon
        v-if="showRibbon"
        :partId="partId"
        :partNumber="partNumber"
        :articleNumber="articleNumber"
        :linkingGroup="linkingGroup"
      />

      <!-- Module content area -->
      <div class="panel-content">
        <template v-for="modId in modules" :key="modId">
          <div v-show="modId === activeModule" class="module-slot">
            <component
              :is="moduleComponents[modId]"
              :partId="partId"
              :linkingGroup="linkingGroup"
              @select-part="handleSelectPart"
              @create-new="handleCreateNew"
            />
          </div>
        </template>
      </div>
    </div>
  </GlassPanel>
</template>

<style scoped>
.tile-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-content {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  position: relative;
}

.module-slot {
  height: 100%;
  overflow: hidden;
}

/* Maximized state */
.maximized {
  position: fixed;
  inset: 38px 3px 24px 3px;
  z-index: 50;
}
</style>
