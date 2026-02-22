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
  gap: 12px;
  padding: var(--pad) 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.module-title {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  margin: 0;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.data-badge {
  font-size: var(--fs);
  color: var(--t3);
  background: var(--raised);
  padding: 2px var(--pad);
  border-radius: 99px;
  white-space: nowrap;
}

.year-selector {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--raised);
  border-radius: var(--r);
  padding: 2px;
}

.year-select {
  padding: 4px 6px;
  font-size: var(--fs);
  font-weight: 500;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  color: var(--t3);
  cursor: pointer;
  margin-left: 2px;
}

.year-btn {
  padding: 4px var(--pad);
  font-size: var(--fs);
  font-weight: 500;
  border: none;
  border-radius: var(--rs);
  background: transparent;
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms;
}

.year-btn:hover {
  background: var(--surface);
  color: var(--t2);
}

.year-btn.active {
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
  border: 1px solid var(--red);
}

.refresh-btn {
  padding: 4px var(--pad);
  font-size: var(--fs);
  font-weight: 500;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--surface);
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms;
}

.refresh-btn:hover {
  border-color: var(--red);
  color: var(--red);
}

.refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
