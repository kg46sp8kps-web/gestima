<script setup lang="ts">
/**
 * TilePricing — pricing module wrapper for tiling workspace
 * Renders PricingDetailPanel directly (ribbon handles part info)
 */

import type { LinkingGroup } from '@/types/workspace'
import PricingDetailPanel from '@/components/modules/pricing/PricingDetailPanel.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})
</script>

<template>
  <div class="tile-pricing" data-testid="tile-pricing">
    <PricingDetailPanel
      :partId="partId"
      :linkingGroup="linkingGroup"
    />
  </div>
</template>

<style scoped>
.tile-pricing {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
