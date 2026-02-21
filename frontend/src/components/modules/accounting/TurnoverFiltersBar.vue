<script setup lang="ts">
import { ACCOUNT_GROUPS } from '@/types/accounting'

defineProps<{
  filterPrefix: string | null
  searchText: string
  hideZero: boolean
  filterDan1: string
  filterDan2: string
  filterDan3: string
  accountCount: number
  analytics: Record<string, string[]>
}>()

const emit = defineEmits<{
  (e: 'update:filterPrefix', value: string | null): void
  (e: 'update:searchText', value: string): void
  (e: 'update:hideZero', value: boolean): void
  (e: 'update:filterDan1', value: string): void
  (e: 'update:filterDan2', value: string): void
  (e: 'update:filterDan3', value: string): void
}>()
</script>

<template>
  <div class="filters-wrapper">
    <div class="filter-bar">
      <div class="prefix-filters">
        <button
          v-for="grp in ACCOUNT_GROUPS"
          :key="grp.prefix"
          :class="['prefix-btn', { active: filterPrefix === grp.prefix }]"
          :title="grp.label"
          @click="emit('update:filterPrefix', filterPrefix === grp.prefix ? null : grp.prefix)"
        >
          {{ grp.prefix }}xx
        </button>
      </div>
      <input
        :value="searchText"
        class="search-input"
        type="text"
        placeholder="Hledat účet..."
        @input="emit('update:searchText', ($event.target as HTMLInputElement).value)"
      />
      <label class="checkbox-label">
        <input :checked="hideZero" type="checkbox" @change="emit('update:hideZero', !hideZero)" />
        Skrýt nulové
      </label>
      <span class="stats">{{ accountCount }} účtů</span>
    </div>

    <div class="analytics-bar">
      <label class="filter-label">
        Středisko:
        <select
          :value="filterDan1"
          class="filter-select"
          @change="emit('update:filterDan1', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Vše</option>
          <option v-for="v in analytics.dAn1" :key="v" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="filter-label">
        Typ:
        <select
          :value="filterDan2"
          class="filter-select"
          @change="emit('update:filterDan2', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Vše</option>
          <option v-for="v in analytics.dAn2" :key="v" :value="v">{{ v }}</option>
        </select>
      </label>
      <label class="filter-label">
        Stroj:
        <select
          :value="filterDan3"
          class="filter-select"
          @change="emit('update:filterDan3', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Vše</option>
          <option v-for="v in analytics.dAn3" :key="v" :value="v">{{ v }}</option>
        </select>
      </label>
    </div>
  </div>
</template>

<style scoped>
.filters-wrapper {
  border-bottom: 1px solid var(--color-border);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border-default);
  flex-wrap: wrap;
  background: var(--bg-surface);
}

.analytics-bar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-1) var(--space-5);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.filter-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.filter-select {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.prefix-filters {
  display: flex;
  gap: var(--space-0\.5);
}

.prefix-btn {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--duration-fast);
}

.prefix-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-body);
}

.prefix-btn.active {
  background: var(--brand-subtle);
  color: var(--brand-text);
  border-color: var(--brand);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
}

.stats {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  white-space: nowrap;
}
</style>
