<script setup lang="ts">
/**
 * AddQuoteItemModal — Modal dialog for adding a part to a quote.
 * Displayed via Teleport to body.
 */
import { reactive } from 'vue'
import { usePartsStore } from '@/stores/parts'
import type { QuoteItemCreate } from '@/types/quote'
import { Info } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  saving: boolean
}>()

const emit = defineEmits<{
  'submit': [item: QuoteItemCreate]
  'cancel': []
}>()

const partsStore = usePartsStore()

const form = reactive<QuoteItemCreate>({
  part_id: 0,
  quantity: 1,
  notes: ''
})

function reset() {
  form.part_id = 0
  form.quantity = 1
  form.notes = ''
}

function onSubmit() {
  if (!form.part_id) return
  emit('submit', { ...form })
  reset()
}

function onCancel() {
  reset()
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="onCancel">
      <div class="modal-content">
        <h3>Přidat položku</h3>
        <form class="add-form" @submit.prevent="onSubmit">
          <div class="form-group">
            <label>Díl <span class="required">*</span></label>
            <select v-model.number="form.part_id" class="form-input" required>
              <option :value="0" disabled>-- Vyberte díl --</option>
              <option
                v-for="part in partsStore.parts"
                :key="part.id"
                :value="part.id"
              >
                {{ part.article_number || part.part_number }} - {{ part.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>Množství <span class="required">*</span></label>
            <input
              v-model.number="form.quantity"
              type="number"
              class="form-input"
              required
              min="0.01"
              step="0.01"
              v-select-on-focus
            />
          </div>

          <div class="info-notice">
            <Info :size="ICON_SIZE.SMALL" />
            <span>Cena se automaticky načte z nejnovější zmrazené kalkulace dílu.</span>
          </div>

          <div class="form-group">
            <label>Poznámky</label>
            <textarea v-model="form.notes" class="form-textarea" rows="3"></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="onCancel">
              Zrušit
            </button>
            <button type="submit" class="btn-primary" :disabled="saving || !form.part_id">
              {{ saving ? 'Přidávám...' : 'Přidat' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>

.add-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.required {
  color: var(--palette-danger);
}

.info-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-lg);
  color: var(--text-body);
  font-size: var(--text-sm);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

</style>
