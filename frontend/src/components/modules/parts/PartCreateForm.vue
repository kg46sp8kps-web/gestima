<script setup lang="ts">
import { ref } from 'vue'
import { usePartsStore } from '@/stores/parts'
import type { PartCreate, Part } from '@/types/part'

const emit = defineEmits<{
  'created': [part: Part]
  'cancel': []
}>()

const partsStore = usePartsStore()
const formData = ref<PartCreate>({
  part_number: '',
  name: '',
  notes: ''
})

async function handleSubmit() {
  try {
    const created = await partsStore.createPart(formData.value)
    formData.value = { part_number: '', name: '', notes: '' }
    emit('created', created)
  } catch (error) {
    // partsStore.createPart already shows error toast via ui.showError()
    // Re-throw to allow parent components to handle if needed
    throw error
  }
}

function handleCancel() {
  formData.value = { part_number: '', name: '', notes: '' }
  emit('cancel')
}
</script>

<template>
  <div class="part-create-form">
    <h2>Nový díl</h2>

    <form @submit.prevent="handleSubmit">
      <div class="form-field">
        <label>Číslo dílu *</label>
        <input v-model="formData.part_number" required />
      </div>

      <div class="form-field">
        <label>Název *</label>
        <input v-model="formData.name" required />
      </div>

      <div class="form-field">
        <label>Popis</label>
        <textarea v-model="formData.notes" rows="3"></textarea>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn-primary">💾 Uložit</button>
        <button type="button" @click="handleCancel" class="btn-secondary">❌ Zrušit</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue CREATE FORM section */
.part-create-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 600px;
}

.part-create-form h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-base);
}

.form-field input,
.form-field textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-base);
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.form-field textarea {
  resize: vertical;
  font-family: inherit;
}

.form-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

/* Button styles removed - using global design-system.css utilities */
/* See: frontend/src/assets/css/design-system.css for .btn-primary, .btn-secondary */
</style>
