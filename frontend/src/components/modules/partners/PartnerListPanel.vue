<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePartnersStore } from '@/stores/partners'
import type { Partner } from '@/types/partner'
import { Plus, Building2, Users, Factory } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  selectedPartner?: Partner | null
}

const props = withDefaults(defineProps<Props>(), {
  selectedPartner: null
})

const emit = defineEmits<{
  'select-partner': [partner: Partner]
  'create-new': []
}>()

const partnersStore = usePartnersStore()
const searchQuery = ref('')
const activeTab = ref<'all' | 'customers' | 'suppliers'>('all')

const filteredPartners = computed(() => {
  let list: Partner[] = []

  // Filter by tab
  switch (activeTab.value) {
    case 'customers':
      list = partnersStore.customers
      break
    case 'suppliers':
      list = partnersStore.suppliers
      break
    default:
      list = [...partnersStore.partners]
  }

  // Sort by partner_number
  list.sort((a, b) => a.partner_number.localeCompare(b.partner_number))

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.partner_number.toLowerCase().includes(query) ||
      p.company_name.toLowerCase().includes(query) ||
      p.email?.toLowerCase().includes(query) ||
      p.contact_person?.toLowerCase().includes(query)
    )
  }

  return list
})

const isLoading = computed(() => partnersStore.loading)
const hasPartners = computed(() => filteredPartners.value.length > 0)

function selectPartner(partner: Partner) {
  emit('select-partner', partner)
}

function handleCreate() {
  emit('create-new')
}

function setTab(tab: 'all' | 'customers' | 'suppliers') {
  activeTab.value = tab
}
</script>

<template>
  <div class="partner-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Partneři</h3>
      <button @click="handleCreate" class="btn-create">
        <Plus :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        Nový
      </button>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        :class="{ active: activeTab === 'all' }"
        @click="setTab('all')"
        class="tab-button"
      >
        Všichni
      </button>
      <button
        :class="{ active: activeTab === 'customers' }"
        @click="setTab('customers')"
        class="tab-button"
      >
        Zákazníci
      </button>
      <button
        :class="{ active: activeTab === 'suppliers' }"
        @click="setTab('suppliers')"
        class="tab-button"
      >
        Dodavatelé
      </button>
    </div>

    <!-- Search Bar -->
    <input
      v-model="searchQuery"
      v-select-on-focus
      type="text"
      placeholder="Filtrovat partnery..."
      class="search-input"
    />

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-list">
      <div class="spinner"></div>
      <p>Načítám partnery...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasPartners" class="empty-list">
      <div class="empty-icon">
        <Building2 :size="48" :stroke-width="1.5" />
      </div>
      <p>Žádní partneři</p>
    </div>

    <!-- Partners List -->
    <div v-else class="partners-list">
      <div
        v-for="partner in filteredPartners"
        :key="partner.id"
        @click="selectPartner(partner)"
        :class="{ active: selectedPartner?.id === partner.id }"
        class="partner-item"
      >
        <div class="partner-header">
          <span class="partner-number">{{ partner.partner_number }}</span>
          <div class="partner-badges">
            <span v-if="partner.is_customer" class="badge-customer" title="Zákazník">
              <Users :size="ICON_SIZE.STANDARD" :stroke-width="2" />
            </span>
            <span v-if="partner.is_supplier" class="badge-supplier" title="Dodavatel">
              <Factory :size="ICON_SIZE.STANDARD" :stroke-width="2" />
            </span>
          </div>
        </div>
        <span class="partner-name">{{ partner.company_name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.partner-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.list-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-create {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--palette-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-create:hover {
  background: var(--palette-primary-hover);
}

.filter-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-default);
}

.tab-button {
  flex: 1;
  padding: var(--space-2);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.tab-button:hover {
  color: var(--text-body);
  background: var(--state-hover);
}

.tab-button.active {
  color: var(--palette-primary);
  border-bottom-color: var(--palette-primary);
}

.search-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.search-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.loading-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--palette-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-list .empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.empty-list p {
  font-size: var(--text-sm);
}

.partners-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.partner-item {
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  background: var(--bg-surface);
}

.partner-item:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.partner-item.active {
  background: var(--state-selected);
  border-color: var(--palette-primary);
}

.partner-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.partner-number {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--palette-primary);
}

.partner-badges {
  display: flex;
  gap: var(--space-1);
}

.badge-customer,
.badge-supplier {
  display: flex;
  align-items: center;
  justify-content: center;
}

.badge-customer {
  color: var(--color-primary);
}

.badge-supplier {
  color: var(--text-secondary);
}

.partner-name {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-body);
  font-weight: var(--font-medium);
}
</style>
