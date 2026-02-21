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
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.operations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
}

.operations-header.clickable {
  cursor: pointer;
  user-select: none;
}

.operations-header.clickable:hover {
  background: var(--bg-raised);
}

.part-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.expand-chevron {
  color: var(--text-tertiary);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.part-info h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.part-info h2.placeholder {
  color: var(--text-tertiary);
}

.part-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.ai-time-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: rgba(139, 92, 246, 0.1);
  color: var(--brand-text);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.count-badge {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

/* Expandable part detail */
.part-detail-expand {
  border-top: 1px solid var(--border-default);
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
