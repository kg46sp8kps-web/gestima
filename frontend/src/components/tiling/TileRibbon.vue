<script setup lang="ts">
/**
 * TileRibbon — info strip with part context, KPIs, and action buttons
 * Extracted from PartDetailTabs.vue ribbon section
 * Displayed at the top of panels that have needsPart=true modules
 */

import { computed } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useMaterialsStore } from '@/stores/materials'
import { useBatchesStore } from '@/stores/batches'
import type { LinkingGroup } from '@/types/workspace'
import { formatCurrency } from '@/utils/formatters'

interface Props {
  partId: number | null
  partNumber: string | null
  articleNumber: string | null
  linkingGroup: LinkingGroup
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'refresh-part': []
}>()

const operationsStore = useOperationsStore()
const materialsStore = useMaterialsStore()
const batchesStore = useBatchesStore()

const operationsCount = computed(() => operationsStore.getContext(props.linkingGroup).operations.length)
const materialsCount = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs.length)

const ribbonPrice = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  const firstBatch = ctx.batches?.[0]
  if (firstBatch?.unit_cost != null) return formatCurrency(firstBatch.unit_cost)
  return '—'
})

const displayNumber = computed(() => props.articleNumber || props.partNumber || '—')
</script>

<template>
  <div v-if="partId" class="rib" data-testid="tile-ribbon">
    <div class="rib-r">
      <span class="rib-i">
        <span class="rib-l">Díl</span>
        <span class="rib-v rib-mono">{{ displayNumber }}</span>
      </span>
      <span v-if="materialsCount > 0" class="rib-i">
        <span class="rib-l">Mat.</span>
        <span class="rib-v">{{ materialsCount }}×</span>
      </span>
      <span class="rib-i">
        <span class="rib-l">Ops</span>
        <span class="rib-v rib-mono">{{ operationsCount }}</span>
      </span>
    </div>
    <div class="rib-kpis">
      <div class="rib-kpi">
        <span class="kl">Cena/ks</span>
        <span class="kv">{{ ribbonPrice }}</span>
        <span class="ku">CZK</span>
      </div>
    </div>
    <div class="acts">
      <button class="act brand" @click="emit('refresh-part')" data-testid="ribbon-refresh">Obnovit</button>
    </div>
  </div>
</template>

<style scoped>
.rib {
  padding: 6px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: opacity 0.15s;
}

.rib-r {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rib-i {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.rib-l {
  font-size: 10px;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.rib-v {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
}

.rib-mono {
  font-family: var(--mono);
}

/* KPI cards */
.rib-kpis {
  display: flex;
  gap: 6px;
}

.rib-kpi {
  padding: 3px 7px;
  background: var(--b1);
  border-radius: var(--rs);
  display: flex;
  align-items: center;
  gap: 5px;
}

.kl {
  font-size: 10px;
  color: var(--t4);
}

.kv {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--green);
  font-weight: 600;
}

.ku {
  font-size: 9px;
  color: var(--t4);
}

/* Action buttons */
.acts {
  display: flex;
  gap: 3px;
}

.act {
  padding: 2px 7px;
  font-size: 10.5px;
  font-weight: 500;
  background: transparent;
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  color: var(--t3);
  cursor: pointer;
  transition: all 0.08s;
  font-family: inherit;
}

.act:hover {
  background: var(--b1);
  color: var(--t1);
  border-color: var(--b2);
}

.act.brand {
  border-color: rgba(229,57,53,0.25);
  color: var(--red);
}

.act.brand:hover {
  background: var(--red-dim);
  border-color: rgba(229,57,53,0.4);
}
</style>
