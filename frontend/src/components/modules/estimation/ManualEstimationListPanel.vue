<template>
  <div class="estimation-list-panel">
    <!-- TAB HEADER -->
    <div class="tabs">
      <button
        class="tab-button"
        :class="{ active: activeTab === 'ROT' }"
        @click="switchTab('ROT')"
      >
        <span>Turning</span>
        <span class="count-badge">{{ turningCount }}</span>
      </button>
      <button
        class="tab-button"
        :class="{ active: activeTab === 'PRI' }"
        @click="switchTab('PRI')"
      >
        <span>Milling</span>
        <span class="count-badge">{{ millingCount }}</span>
      </button>
    </div>

    <!-- LOADING STATE -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading parts...</p>
    </div>

    <!-- EMPTY STATE -->
    <div v-else-if="records.length === 0" class="empty-state">
      <p>No parts found for {{ activeTab }} parts</p>
    </div>

    <!-- PARTS LIST -->
    <div v-else class="parts-list">
      <EstimationListItem
        v-for="record in records"
        :key="record.id"
        :record="record"
        :selected="selectedId === record.id"
        @click="$emit('select', record.id)"
      />
    </div>

    <!-- FOOTER ACTIONS -->
    <div class="footer-actions">
      <button class="action-btn" @click="$emit('refresh')">
        Refresh
      </button>
      <button
        class="action-btn primary"
        :disabled="exportDisabled"
        @click="$emit('export')"
      >
        Export CSV
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EstimationRecord, PartType } from '@/types/estimation'
import EstimationListItem from './EstimationListItem.vue'

interface Props {
  records: EstimationRecord[]
  selectedId: number | null
  partType: PartType
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'select', id: number): void
  (e: 'change-part-type', type: PartType): void
  (e: 'export'): void
  (e: 'refresh'): void
}>()

const activeTab = computed(() => props.partType)

const turningCount = computed(() =>
  props.partType === 'ROT' ? props.records.length : 0
)

const millingCount = computed(() =>
  props.partType === 'PRI' ? props.records.length : 0
)

const exportDisabled = computed(() => {
  return !props.records.some(r => r.estimated_time_min)
})

function switchTab(type: PartType) {
  if (type !== props.partType) {
    emit('change-part-type', type)
  }
}
</script>

<style scoped>
.estimation-list-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
}

.tabs {
  display: flex;
  gap: 2px;
  padding: var(--space-2);
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
}

.tab-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.tab-button:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tab-button.active {
  background: var(--color-primary);
  color: var(--text-inverse);
  border-color: var(--color-primary);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 var(--space-1);
  background: var(--bg-base);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
}

.tab-button.active .count-badge {
  background: var(--color-primary-dark);
  color: var(--text-inverse);
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.parts-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.footer-actions {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--border-default);
  background: var(--bg-base);
}

.action-btn {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.action-btn.primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--text-inverse);
}

.action-btn.primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
