<script setup lang="ts">
import { computed } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useCatalogStore } from '@/stores/catalog'
import type { ContextGroup } from '@/types/workspace'
import PartDetailCard from './PartDetailCard.vue'
import MaterialDetailCard from './MaterialDetailCard.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const catalog = useCatalogStore()

const catalogItem = computed(() => catalog.getFocusedItem(props.ctx))
const part = computed(() => parts.getFocusedPart(props.ctx))
</script>

<template>
  <div class="wdet">
    <!-- ── Empty state ── -->
    <div v-if="!catalogItem" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte položku ze seznamu</span>
      <span class="mod-hint">Klikněte na díl nebo polotovar v panelu Položky</span>
    </div>

    <!-- ── Material detail ── -->
    <MaterialDetailCard
      v-else-if="catalogItem.type === 'material'"
      :material-number="catalogItem.number"
    />

    <!-- ── Part detail ── -->
    <PartDetailCard
      v-else-if="part"
      :part="part"
      :leaf-id="leafId"
      :ctx="ctx"
    />
  </div>
</template>

<style scoped>
.wdet {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.mod-hint { font-size: var(--fsm); opacity: 0.6; }
</style>
