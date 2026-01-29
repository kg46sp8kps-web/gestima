<script setup lang="ts">
import { ref } from 'vue'
import FormTabs from '@/components/ui/FormTabs.vue'

const activeTab = ref(0)
const tabs = [
  { label: 'Normy materiálů', icon: '📋' },
  { label: 'Skupiny materiálů', icon: '🏷️' },
  { label: 'Cenové kategorie', icon: '💰' },
  { label: 'Pracoviště', icon: '🏭' }
]
</script>

<template>
  <div class="master-data-view">
    <header class="page-header">
      <h1 class="page-title">Kmenová data</h1>
      <p class="page-subtitle">Správa materiálových norem, skupin a pracovišť</p>
    </header>

    <div class="page-content">
      <FormTabs v-model="activeTab" :tabs="tabs">
        <template #tab-0>
          <div class="tab-content">
            <p>Material norms management - TODO</p>
          </div>
        </template>
        <template #tab-1>
          <div class="tab-content">
            <p>Material groups management - TODO</p>
          </div>
        </template>
        <template #tab-2>
          <div class="tab-content">
            <p>Price categories management - TODO</p>
          </div>
        </template>
        <template #tab-3>
          <div class="tab-content">
            <p>Work centers management - TODO</p>
          </div>
        </template>
      </FormTabs>
    </div>
  </div>
</template>

<style scoped>
.master-data-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.page-content {
  flex: 1;
  overflow: hidden;
}

.tab-content {
  padding: var(--space-6);
}
</style>
