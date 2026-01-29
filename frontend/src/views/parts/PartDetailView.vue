<script setup lang="ts">
/**
 * Part Detail View - Full page part editing with tabs
 *
 * Reuses workspace modules in tab layout:
 * - Tab 0: Basic info (name, description)
 * - Tab 1: Material settings (PartMaterialModule)
 * - Tab 2: Operations (PartOperationsModule)
 * - Tab 3: Pricing (PartPricingModule)
 */

import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import FormTabs from '@/components/ui/FormTabs.vue'
import PartMaterialModule from '@/views/workspace/modules/PartMaterialModule.vue'
import PartOperationsModule from '@/components/modules/PartOperationsModule.vue'
import PartPricingModule from '@/components/modules/PartPricingModule.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const route = useRoute()
const router = useRouter()
const partsStore = usePartsStore()
const uiStore = useUiStore()

// Tab state
const activeTab = ref(0)
const tabs = [
  { label: 'Základní', icon: '📋', testId: 'tab-basic' },
  { label: 'Materiál', icon: '🔩', testId: 'tab-material' },
  { label: 'Operace', icon: '🔧', testId: 'tab-operations' },
  { label: 'Kalkulace', icon: '💰', testId: 'tab-pricing' }
]

// Form state for basic info
const editedName = ref('')
const editedNotes = ref('')
const saving = ref(false)

// Computed
const partNumber = computed(() => route.params.partNumber as string)
const part = computed(() => partsStore.currentPart)
const loading = computed(() => partsStore.loading)
const partId = computed(() => part.value?.id ?? null)

// Watch for route changes
watch(partNumber, async (newPartNumber) => {
  if (newPartNumber) {
    await loadPart(newPartNumber)
  }
}, { immediate: true })

// Load part data
async function loadPart(pn: string) {
  try {
    await partsStore.fetchPart(pn)
    if (part.value) {
      editedName.value = part.value.name
      editedNotes.value = part.value.notes || ''
    }
  } catch (error) {
    uiStore.showError('Díl nenalezen')
    router.push({ name: 'parts-list' })
  }
}

// Save basic info
async function saveBasicInfo() {
  if (!part.value || saving.value) return

  saving.value = true
  try {
    await partsStore.updatePart(part.value.part_number, {
      name: editedName.value.trim(),
      notes: editedNotes.value.trim() || '',
      version: part.value.version
    })
    uiStore.showSuccess('Díl uložen')
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    saving.value = false
  }
}

// Navigation
function goBack() {
  router.push({ name: 'parts-list' })
}

function goToWorkspace() {
  router.push({
    name: 'workspace',
    query: { partNumber: partNumber.value }
  })
}
</script>

<template>
  <div class="part-detail-view">
    <!-- Loading state -->
    <template v-if="loading">
      <header class="page-header">
        <Skeleton width="60px" height="36px" />
        <div class="header-content">
          <Skeleton width="200px" height="32px" />
          <Skeleton width="150px" height="20px" class="mt-1" />
        </div>
      </header>
      <div class="page-content">
        <Skeleton height="400px" />
      </div>
    </template>

    <!-- Content -->
    <template v-else-if="part">
      <!-- Page header -->
      <header class="page-header">
        <button class="btn-back" @click="goBack" title="Zpět na seznam">
          ← Zpět
        </button>

        <div class="header-content">
          <div class="header-title-row">
            <h1 class="page-title" data-testid="part-name">{{ part.name }}</h1>
            <span class="part-number-badge">{{ part.part_number }}</span>
          </div>
          <p class="page-subtitle">
            {{ part.notes || 'Bez poznámek' }}
          </p>
        </div>

        <div class="header-actions">
          <button class="btn btn-secondary" @click="goToWorkspace">
            Otevřít ve Workspace
          </button>
        </div>
      </header>

      <!-- Tabs -->
      <div class="page-content">
        <FormTabs v-model="activeTab" :tabs="tabs">
          <!-- Tab 0: Basic info -->
          <template #tab-0>
            <div class="tab-content basic-info-tab">
              <form class="basic-info-form" @submit.prevent="saveBasicInfo">
                <div class="form-group">
                  <label class="form-label" for="edit-name">
                    Název dílu <span class="required">*</span>
                  </label>
                  <input
                    id="edit-name"
                    v-model="editedName"
                    type="text"
                    class="form-input"
                    maxlength="200"
                    required
                  />
                </div>

                <div class="form-group">
                  <label class="form-label" for="edit-notes">
                    Poznámky
                  </label>
                  <textarea
                    id="edit-notes"
                    v-model="editedNotes"
                    class="form-textarea"
                    rows="4"
                    maxlength="1000"
                  ></textarea>
                </div>

                <div class="info-row">
                  <span class="info-label">Číslo dílu:</span>
                  <span class="info-value">{{ part.part_number }}</span>
                </div>

                <div class="info-row">
                  <span class="info-label">Vytvořeno:</span>
                  <span class="info-value">{{ new Date(part.created_at).toLocaleDateString('cs-CZ') }}</span>
                </div>

                <div class="form-actions">
                  <button
                    type="submit"
                    class="btn btn-primary"
                    :disabled="saving || !editedName.trim()"
                  >
                    {{ saving ? 'Ukládám...' : 'Uložit změny' }}
                  </button>
                </div>
              </form>
            </div>
          </template>

          <!-- Tab 1: Material -->
          <template #tab-1>
            <div class="tab-content module-tab">
              <PartMaterialModule
                :inline="true"
                :part-id="partId"
                :part-number="partNumber"
              />
            </div>
          </template>

          <!-- Tab 2: Operations -->
          <template #tab-2>
            <div class="tab-content module-tab">
              <PartOperationsModule
                :inline="true"
                :part-id="partId"
                :part-number="partNumber"
              />
            </div>
          </template>

          <!-- Tab 3: Pricing -->
          <template #tab-3>
            <div class="tab-content module-tab">
              <PartPricingModule
                :inline="true"
                :part-id="partId"
                :part-number="partNumber"
              />
            </div>
          </template>
        </FormTabs>
      </div>
    </template>

    <!-- Not found -->
    <template v-else>
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <p>Díl nenalezen</p>
        <button class="btn btn-primary" @click="goBack">
          Zpět na seznam
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.part-detail-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

/* Page header */
.page-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.btn-back {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.btn-back:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.header-content {
  flex: 1;
  min-width: 0;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.part-number-badge {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--accent-primary);
  background: var(--accent-subtle);
  border-radius: var(--radius-full);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

/* Page content */
.page-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Make FormTabs fill the space */
.page-content :deep(.form-tabs) {
  height: 100%;
}

.page-content :deep(.tabs-content) {
  flex: 1;
  overflow: hidden;
}

.page-content :deep(.tab-panel) {
  height: 100%;
  padding: 0;
  overflow: auto;
}

/* Tab content */
.tab-content {
  height: 100%;
}

.basic-info-tab {
  padding: var(--space-6);
  max-width: 600px;
}

.module-tab {
  /* Modules handle their own padding */
}

/* Basic info form */
.basic-info-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-label {
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--space-3);
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
}

.info-row {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.info-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  min-width: 100px;
}

.info-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.form-actions {
  display: flex;
  justify-content: flex-start;
  padding-top: var(--space-4);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--space-10);
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.empty-state p {
  margin: 0 0 var(--space-6);
  font-size: var(--text-lg);
}

/* Utility */
.mt-1 {
  margin-top: var(--space-1);
}
</style>
