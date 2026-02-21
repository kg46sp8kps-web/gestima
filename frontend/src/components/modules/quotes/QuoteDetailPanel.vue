<script setup lang="ts">
/**
 * Quote Detail Panel
 * Thin coordinator: action bar + FormTabs delegating to QuoteInfoTab,
 * QuoteItemsTab and QuoteSnapshotTab.
 */
import { ref, computed, reactive, watch } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartnersStore } from '@/stores/partners'
import { usePartsStore } from '@/stores/parts'
import type { QuoteWithItems, QuoteUpdate } from '@/types/quote'
import FormTabs from '@/components/ui/FormTabs.vue'
import QuoteInfoTab from './QuoteInfoTab.vue'
import QuoteItemsTab from './QuoteItemsTab.vue'
import QuoteSnapshotTab from './QuoteSnapshotTab.vue'
import { FileText, Edit, X, Save } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  quote: QuoteWithItems | null
}>()

const emit = defineEmits<{
  'updated': []
  'deleted': []
}>()

const quotesStore = useQuotesStore()
const partnersStore = usePartnersStore()
const partsStore = usePartsStore()

const activeTab = ref(0)
const isEditing = ref(false)

const editForm = reactive({
  partner_id: null as number | null,
  title: '',
  description: '',
  customer_request_number: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: ''
})

const saving = computed(() => quotesStore.loading)
const isDraft = computed(() => props.quote?.status === 'draft')
const canEdit = computed(() => isDraft.value)

watch(() => props.quote, (quote) => {
  if (quote) {
    editForm.partner_id = quote.partner_id
    editForm.title = quote.title
    editForm.description = quote.description || ''
    editForm.customer_request_number = quote.customer_request_number || ''
    editForm.valid_until = quote.valid_until || ''
    editForm.discount_percent = quote.discount_percent
    editForm.tax_percent = quote.tax_percent
    editForm.notes = ''
    isEditing.value = false
  }
}, { immediate: true })

function startEdit() {
  isEditing.value = true
}

function cancelEdit() {
  if (props.quote) {
    editForm.partner_id = props.quote.partner_id
    editForm.title = props.quote.title
    editForm.description = props.quote.description || ''
    editForm.customer_request_number = props.quote.customer_request_number || ''
    editForm.valid_until = props.quote.valid_until || ''
    editForm.discount_percent = props.quote.discount_percent
    editForm.tax_percent = props.quote.tax_percent
  }
  isEditing.value = false
}

async function saveQuote() {
  if (!props.quote) return

  const data: QuoteUpdate = {
    partner_id: editForm.partner_id,
    title: editForm.title,
    description: editForm.description || undefined,
    customer_request_number: editForm.customer_request_number || undefined,
    valid_until: editForm.valid_until || undefined,
    discount_percent: editForm.discount_percent,
    tax_percent: editForm.tax_percent,
    version: props.quote.version
  }

  try {
    await quotesStore.updateQuote(props.quote.quote_number, data)
    isEditing.value = false
    emit('updated')
  } catch {
    // Error handled in store
  }
}

// Load dependencies on mount
partnersStore.fetchPartners()
partsStore.fetchParts()
</script>

<template>
  <div class="quote-detail-panel">
    <!-- Empty State -->
    <div v-if="!quote" class="empty">
      <FileText :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Vyberte nabídku pro zobrazení detailů</p>
    </div>

    <!-- Quote Details -->
    <div v-else class="detail-content">
      <!-- Action Buttons -->
      <div class="panel-actions">
        <button
          v-if="!isEditing && canEdit"
          class="icon-btn"
          title="Upravit"
          @click="startEdit"
        >
          <Edit :size="ICON_SIZE.STANDARD" />
        </button>
        <template v-else-if="isEditing">
          <button class="icon-btn" title="Zrušit" @click="cancelEdit">
            <X :size="ICON_SIZE.STANDARD" />
          </button>
          <button
            class="icon-btn icon-btn-primary"
            :disabled="saving"
            :title="saving ? 'Ukládám...' : 'Uložit'"
            @click="saveQuote"
          >
            <Save :size="ICON_SIZE.STANDARD" />
          </button>
        </template>
      </div>

      <!-- Tabs -->
      <FormTabs v-model="activeTab" :tabs="['Základní info', 'Položky', 'Snapshot']">
        <template #tab-0>
          <QuoteInfoTab
            :quote="quote"
            :is-editing="isEditing"
            :can-edit="canEdit"
            :edit-form="editForm"
            :partners="partnersStore.customers"
          />
        </template>

        <template #tab-1>
          <QuoteItemsTab
            :quote="quote"
            :can-edit="canEdit"
            @item-added="emit('updated')"
            @item-deleted="emit('updated')"
          />
        </template>

        <template #tab-2>
          <QuoteSnapshotTab :quote="quote" />
        </template>
      </FormTabs>
    </div>
  </div>
</template>

<style scoped>
.quote-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  container-type: inline-size;
  container-name: detail-panel;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-secondary);
  text-align: center;
}

.empty-icon {
  margin-bottom: var(--space-2);
  opacity: 0.5;
  color: var(--text-secondary);
}

.empty p {
  font-size: var(--text-base);
}

.detail-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}
</style>
