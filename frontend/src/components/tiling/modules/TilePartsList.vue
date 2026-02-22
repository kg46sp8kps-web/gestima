<script setup lang="ts">
/**
 * TilePartsList — parts list module wrapper for tiling workspace
 * Wraps PartListPanel with select-part event forwarding
 */

import { ref } from 'vue'
import type { LinkingGroup } from '@/types/workspace'
import type { Part } from '@/types/part'
import PartListPanel from '@/components/modules/parts/PartListPanel.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})

const emit = defineEmits<{
  'select-part': [part: Part]
  'create-new': []
}>()

const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

function handleSelectPart(part: Part) {
  emit('select-part', part)
}

function handleCreateNew() {
  emit('create-new')
}

defineExpose({
  prependAndSelect(part: Part) {
    listPanelRef.value?.prependAndSelect(part)
  },
  setSelection(id: number | null) {
    listPanelRef.value?.setSelection(id)
  },
})
</script>

<template>
  <div class="tile-parts-list" data-testid="tile-parts-list">
    <PartListPanel
      ref="listPanelRef"
      :linkingGroup="linkingGroup"
      @select-part="handleSelectPart"
      @create-new="handleCreateNew"
    />
  </div>
</template>

<style scoped>
.tile-parts-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
