<script setup lang="ts">
/**
 * QuoteItemsTab — Tab 1: Položky
 * Displays items table and allows adding/deleting items (draft only).
 */
import { ref } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import type { QuoteWithItems, QuoteItemCreate } from '@/types/quote'
import AddQuoteItemModal from './AddQuoteItemModal.vue'
import { Plus, Trash2, Lock } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm } from '@/composables/useDialog'
import { formatCurrency } from '@/utils/formatters'

const props = defineProps<{
  quote: QuoteWithItems
  canEdit: boolean
}>()

const emit = defineEmits<{
  'item-added': []
  'item-deleted': []
}>()

const quotesStore = useQuotesStore()

const showAddModal = ref(false)
const saving = ref(false)

async function handleAddItem(item: QuoteItemCreate) {
  saving.value = true
  try {
    await quotesStore.addQuoteItem(props.quote.quote_number, item)
    showAddModal.value = false
    emit('item-added')
  } catch {
    // Error handled in store
  } finally {
    saving.value = false
  }
}

async function deleteItem(itemId: number) {
  const confirmed = await confirm({
    title: 'Smazat položku?',
    message: 'Opravdu chcete smazat tuto položku z nabídky?\n\nTato akce je nevratná!',
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  saving.value = true
  try {
    await quotesStore.deleteQuoteItem(itemId)
    emit('item-deleted')
  } catch {
    // Error handled in store
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="items-tab">
    <div v-if="canEdit" class="items-actions">
      <button class="icon-btn icon-btn-brand" title="Přidat položku" @click="showAddModal = true">
        <Plus :size="ICON_SIZE.STANDARD" />
      </button>
    </div>

    <div v-if="quote.items.length > 0" class="items-table-wrapper">
      <table class="items-table">
        <thead>
          <tr>
            <th>Pořadí</th>
            <th>Číslo dílu</th>
            <th>Název</th>
            <th>Množství</th>
            <th>Jednotková cena</th>
            <th>Celkem</th>
            <th v-if="canEdit">Akce</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in quote.items" :key="item.id">
            <td>{{ index + 1 }}</td>
            <td>{{ item.drawing_number || item.part_number }}</td>
            <td>{{ item.part_name }}</td>
            <td>{{ item.quantity }}</td>
            <td class="col-currency">{{ formatCurrency(item.unit_price) }}</td>
            <td class="col-currency">{{ formatCurrency(item.line_total) }}</td>
            <td v-if="canEdit">
              <button
                class="icon-btn icon-btn-danger"
                :disabled="saving"
                title="Smazat položku"
                @click="deleteItem(item.id)"
              >
                <Trash2 :size="ICON_SIZE.STANDARD" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="items-empty">
      <p>Žádné položky</p>
    </div>

    <div v-if="!canEdit" class="edit-lock-notice">
      <Lock :size="ICON_SIZE.SMALL" />
      <span>Položky lze editovat pouze ve stavu "Koncept"</span>
    </div>
  </div>

  <AddQuoteItemModal
    v-if="showAddModal"
    :saving="saving"
    @submit="handleAddItem"
    @cancel="showAddModal = false"
  />
</template>

<style scoped>
.items-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.items-actions {
  display: flex;
  justify-content: flex-end;
}

.items-table-wrapper {
  overflow-x: auto;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
}

.items-table th,
.items-table td {
  padding: var(--pad);
  text-align: left;
  border-bottom: 1px solid var(--b2);
}

.items-table th {
  background: var(--surface);
  font-size: var(--fs);
  font-weight: 700;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.items-table td {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
}

.col-currency {
  font-family: var(--mono);
  text-align: right;
}

.items-empty {
  text-align: center;
  padding: 24px;
  color: var(--t3);
}

.edit-lock-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--pad);
  background: var(--raised);
  border-radius: 8px;
  border: 1px solid var(--b2);
  color: var(--t3);
  font-size: var(--fs);
}
</style>
