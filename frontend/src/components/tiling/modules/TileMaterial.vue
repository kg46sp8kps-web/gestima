<script setup lang="ts">
/**
 * TileMaterial — material input module wrapper for tiling workspace
 * Wraps MaterialInputSelectorV2 with correct props
 */

import type { LinkingGroup } from '@/types/workspace'
import MaterialInputSelectorV2 from '@/components/modules/operations/MaterialInputSelectorV2.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})
</script>

<template>
  <div class="tile-material" data-testid="tile-material">
    <MaterialInputSelectorV2
      :partId="partId"
      :linkingGroup="linkingGroup"
    />
  </div>
</template>

<style scoped>
.tile-material {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}
</style>
