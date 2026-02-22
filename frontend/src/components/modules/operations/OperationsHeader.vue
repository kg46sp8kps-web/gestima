<script setup lang="ts">
/**
 * Operations Header Component
 * Displays part info with expandable detail panel
 */

import { ref } from 'vue'
import type { Part } from '@/types/part'
import { Sparkles, ChevronRight, ChevronDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import PartDetailPanel from '../parts/PartDetailPanel.vue'

interface Props {
  part: Part | null
  operationsCount: number
  hasAIEstimation?: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  'refresh': []
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
}>()

const expanded = ref(false)

function toggle() {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="operations-header-wrap">
    <div class="operations-header" :class="{ clickable: part }" @click="part && toggle()">
      <div v-if="part" class="part-info">
        <component :is="expanded ? ChevronDown : ChevronRight" :size="ICON_SIZE.STANDARD" class="expand-chevron" />
        <h2>{{ part.name }}</h2>
        <span class="part-badge">{{ part.article_number || part.part_number }}</span>
      </div>
      <div v-else class="part-info">
        <h2 class="placeholder">Vyberte díl</h2>
      </div>
      <div class="header-meta">
        <span v-if="hasAIEstimation" class="ai-time-badge" title="Existuje AI odhad času">
          <Sparkles :size="ICON_SIZE.SMALL" />
          AI odhad
        </span>
        <span class="count-badge">{{ operationsCount }} operací</span>
      </div>
    </div>

    <!-- EXPANDABLE PART DETAIL -->
    <Transition name="slide">
      <div v-if="expanded && part" class="part-detail-expand">
        <PartDetailPanel
          :part="part"
          :showActions="false"
          @refresh="emit('refresh')"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.operations-header-wrap {
  flex-shrink: 0;
  border-bottom: 1px solid var(--b2);
  background: var(--surface);
}

.operations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
}

.operations-header.clickable {
  cursor: pointer;
  user-select: none;
}

.operations-header.clickable:hover {
  background: var(--raised);
}

.part-info {
  display: flex;
  align-items: center;
  gap: var(--pad);
}

.expand-chevron {
  color: var(--t3);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.part-info h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.part-info h2.placeholder {
  color: var(--t3);
}

.part-badge {
  padding: 4px var(--pad);
  background: var(--red);
  color: white;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
}

.ai-time-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: rgba(37,99,235,0.1);
  color: rgba(229, 57, 53, 0.7);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
}

.count-badge {
  font-size: var(--fs);
  color: var(--t3);
  font-weight: 500;
}

/* Expandable part detail */
.part-detail-expand {
  border-top: 1px solid var(--b2);
  max-height: 400px;
  overflow-y: auto;
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.slide-enter-to,
.slide-leave-from {
  max-height: 400px;
  opacity: 1;
}
</style>
