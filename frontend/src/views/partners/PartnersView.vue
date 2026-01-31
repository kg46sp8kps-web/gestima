<template>
  <div class="partners-view">
    <!-- Page header -->
    <header class="page-header">
      <h1>Partneři</h1>
      <div class="header-actions">
        <button class="btn btn-primary" @click="handleCreate">
          + Nový partner
        </button>
      </div>
    </header>

    <!-- Tabs: Customers | Suppliers -->
    <FormTabs v-model="activeTab" :tabs="tabs">
      <!-- Tab 0: Zákazníci -->
      <template #tab-0>
        <div class="tab-content">
          <DataTable
            :data="customers"
            :columns="columns"
            :loading="partnersStore.loading"
            empty-text="Žádní zákazníci"
            row-key="partner_number"
          >
            <!-- Custom actions column -->
            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon"
                  title="Upravit"
                  @click.stop="handleEdit(row as unknown as Partner)"
                >
                  ✏️
                </button>
                <button
                  class="btn-icon btn-danger"
                  title="Smazat"
                  @click.stop="handleDelete(row as unknown as Partner)"
                >
                  🗑️
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>

      <!-- Tab 1: Dodavatelé -->
      <template #tab-1>
        <div class="tab-content">
          <DataTable
            :data="suppliers"
            :columns="columns"
            :loading="partnersStore.loading"
            empty-text="Žádní dodavatelé"
            row-key="partner_number"
          >
            <!-- Custom actions column -->
            <template #actions="{ row }">
              <div class="row-actions">
                <button
                  class="btn-icon"
                  title="Upravit"
                  @click.stop="handleEdit(row as unknown as Partner)"
                >
                  ✏️
                </button>
                <button
                  class="btn-icon btn-danger"
                  title="Smazat"
                  @click.stop="handleDelete(row as unknown as Partner)"
                >
                  🗑️
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </template>
    </FormTabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePartnersStore } from '@/stores/partners'
import FormTabs from '@/components/ui/FormTabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import type { Partner } from '@/types/partner'

const router = useRouter()
const partnersStore = usePartnersStore()

// Tab state
const activeTab = ref(0)

const tabs = [
  { label: 'Zákazníci', icon: '👥' },
  { label: 'Dodavatelé', icon: '🏭' }
]

// Computed data
const customers = computed(() => partnersStore.customers)
const suppliers = computed(() => partnersStore.suppliers)

// DataTable columns (shared for both tabs)
const columns = [
  { key: 'partner_number', label: 'Číslo', width: '120px', sortable: true },
  { key: 'company_name', label: 'Název firmy', sortable: true },
  { key: 'ico', label: 'IČO', width: '120px' },
  { key: 'email', label: 'Email', width: '200px' },
  { key: 'phone', label: 'Telefon', width: '150px' },
  { key: 'city', label: 'Město', width: '150px' }
]

// Actions
function handleCreate() {
  // TODO: Open modal or navigate to create form
  router.push({ name: 'partner-create' })
}

function handleRowClick(partner: Partner) {
  router.push({
    name: 'partner-detail',
    params: { partnerNumber: partner.partner_number }
  })
}

function handleEdit(partner: Partner) {
  router.push({
    name: 'partner-edit',
    params: { partnerNumber: partner.partner_number }
  })
}

async function handleDelete(partner: Partner) {
  if (!confirm(`Opravdu smazat partnera "${partner.company_name}"?`)) {
    return
  }

  try {
    await partnersStore.deletePartner(partner.partner_number)
  } catch (error) {
    // Error handled by store
  }
}

// Lifecycle
onMounted(() => {
  partnersStore.fetchPartners()
})
</script>

<style scoped>
.partners-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* === PAGE HEADER === */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.page-header h1 {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

/* === TAB CONTENT === */
.tab-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* === ROW ACTIONS === */
.row-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

.btn-icon {
  padding: var(--space-1) var(--space-2);
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
  font-size: var(--text-base);
}

.btn-icon:hover {
  background: var(--state-hover);
}

.btn-icon.btn-danger:hover {
  background: var(--status-error-bg);
  color: var(--status-error);
}

/* === BUTTONS === */
.btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn:hover {
  background: var(--state-hover);
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
  border-color: var(--accent-primary);
}

.btn-primary:hover {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}
</style>
