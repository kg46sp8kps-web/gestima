<script setup lang="ts">
import { computed } from 'vue'

type TabKey = 'executive' | 'details' | 'data'

interface Props {
  selectedYear: number
  activeTab: TabKey
  loading: boolean
  activeAccountsCount?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:year', year: number): void
  (e: 'update:tab', tab: TabKey): void
  (e: 'refresh'): void
}>()

const tabs = [
  { key: 'executive', label: 'Executive' },
  { key: 'details', label: 'Detaily' },
  { key: 'data', label: 'Data' },
] as const

const currentYear = new Date().getFullYear()
const availableYears = Array.from({ length: currentYear - 2015 + 2 }, (_, i) => 2015 + i)
const recentYears = computed(() => [currentYear - 1, currentYear, currentYear + 1])
</script>

<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <h2 class="module-title">Finanční přehled</h2>
      <div class="year-selector">
        <button
          v-for="y in recentYears"
          :key="y"
          :class="['year-btn', { active: selectedYear === y }]"
          @click="emit('update:year', y)"
        >
          {{ y }}
        </button>
        <select
          :value="selectedYear"
          class="year-select"
          @change="emit('update:year', Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
    </div>
    <div class="tab-buttons">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="emit('update:tab', tab.key as TabKey)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="toolbar-right">
      <span v-if="activeAccountsCount && activeTab === 'data'" class="data-badge">
        {{ activeAccountsCount }} aktivních účtů
      </span>
      <button class="refresh-btn" :disabled="loading" @click="emit('refresh')">
        Obnovit
      </button>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.module-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.data-badge {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  background: var(--bg-raised);
  padding: var(--space-0\.5) var(--space-3);
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.year-selector {
  display: flex;
  align-items: center;
  gap: var(--space-0\.5);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  padding: var(--space-0\.5);
}

.year-select {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-secondary);
  cursor: pointer;
  margin-left: var(--space-0\.5);
}

.year-btn {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.year-btn:hover {
  background: var(--bg-surface);
  color: var(--text-body);
}

.year-btn.active {
  background: var(--brand-subtle);
  color: var(--brand-text);
  border: 1px solid var(--brand);
}

.refresh-btn {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.refresh-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
