<script setup lang="ts">
/**
 * TileDrawing — drawing viewer module wrapper for tiling workspace
 * Wraps PartDrawingWindow (resolves part from windowContext internally)
 */

import type { LinkingGroup } from '@/types/workspace'
import PartDrawingWindow from '@/components/modules/parts/PartDrawingWindow.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})
</script>

<template>
  <div class="tile-drawing" data-testid="tile-drawing">
    <PartDrawingWindow :linkingGroup="linkingGroup" />
  </div>
</template>

<style scoped>
.tile-drawing {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
