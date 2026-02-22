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
  border-bottom: 1px solid var(--b2);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--pad);
  padding: var(--pad) 16px;
  border-bottom: 1px solid var(--b2);
  flex-wrap: wrap;
  background: var(--surface);
}

.analytics-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--b1);
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  color: var(--t3);
}

.filter-select {
  padding: 4px 6px;
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  color: var(--t2);
}

.prefix-filters {
  display: flex;
  gap: 2px;
}

.prefix-btn {
  padding: 4px 6px;
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  cursor: pointer;
  color: var(--t3);
  transition: all 100ms;
}

.prefix-btn:hover {
  border-color: var(--b3);
  color: var(--t2);
}

.prefix-btn.active {
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
  border-color: var(--red);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  cursor: pointer;
}

.stats {
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
}
</style>
