<script setup lang="ts">
/**
 * TileProduction — production history module wrapper for tiling workspace
 * Wraps ProductionHistoryPanel with correct props
 */

import type { LinkingGroup } from '@/types/workspace'
import ProductionHistoryPanel from '@/components/modules/production/ProductionHistoryPanel.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})
</script>

<template>
  <div class="tile-production" data-testid="tile-production">
    <ProductionHistoryPanel
      v-if="partId"
      :partId="partId"
      :collapsed="false"
    />
    <div v-else class="empty-state">
      <p>Vyberte díl pro zobrazení výrobní historie</p>
    </div>
  </div>
</template>

<style scoped>
.tile-production {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--t4);
  font-size: var(--fs);
}
</style>
