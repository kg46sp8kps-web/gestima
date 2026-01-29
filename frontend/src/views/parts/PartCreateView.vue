<script setup lang="ts">
/**
 * Part Create View - Create new part form
 *
 * Full page form for creating a new part.
 * After creation, redirects to part detail view.
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'

const router = useRouter()
const partsStore = usePartsStore()
const uiStore = useUiStore()

// Form state
const form = ref({
  name: '',
  notes: ''
})

const submitting = ref(false)
const errors = ref<Record<string, string>>({})

// Validation
const isValid = computed(() => {
  return form.value.name.trim().length > 0
})

// Actions
function goBack() {
  router.push({ name: 'parts-list' })
}

async function handleSubmit() {
  if (!isValid.value || submitting.value) return

  errors.value = {}
  submitting.value = true

  try {
    const newPart = await partsStore.createPart({
      name: form.value.name.trim(),
      notes: form.value.notes.trim() || undefined
    })

    if (newPart) {
      uiStore.showSuccess(`Díl "${newPart.name}" vytvořen`)
      router.push({
        name: 'part-detail',
        params: { partNumber: newPart.part_number }
      })
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při vytváření dílu'
    uiStore.showError(message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="part-create-view">
    <!-- Page header -->
    <header class="page-header">
      <button class="btn-back" @click="goBack" title="Zpět na seznam">
        ← Zpět
      </button>

      <div class="header-content">
        <h1 class="page-title">Nový díl</h1>
        <p class="page-subtitle">Vytvořte nový díl. Číslo dílu bude přiděleno automaticky.</p>
      </div>
    </header>

    <!-- Form -->
    <div class="page-content">
      <form class="create-form" @submit.prevent="handleSubmit">
        <div class="form-card">
          <h2 class="card-title">Základní údaje</h2>

          <div class="form-group">
            <label class="form-label" for="name">
              Název dílu <span class="required">*</span>
            </label>
            <input
              id="name"
              v-model="form.name"
              type="text"
              class="form-input"
              :class="{ 'has-error': errors.name }"
              placeholder="např. Hřídel hlavní"
              maxlength="200"
              required
              autofocus
              data-testid="part-name-input"
            />
            <span v-if="errors.name" class="error-text" data-testid="error-name">{{ errors.name }}</span>
          </div>

          <div class="form-group">
            <label class="form-label" for="notes">
              Poznámky
            </label>
            <textarea
              id="notes"
              v-model="form.notes"
              class="form-textarea"
              placeholder="Volitelné poznámky k dílu..."
              rows="3"
              maxlength="1000"
              data-testid="part-description-input"
            ></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button
            type="button"
            class="btn btn-secondary"
            @click="goBack"
            :disabled="submitting"
            data-testid="cancel-button"
          >
            Zrušit
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="!isValid || submitting"
            data-testid="save-button"
          >
            {{ submitting ? 'Vytvářím...' : 'Vytvořit díl' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.part-create-view {
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
}

.btn-back:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* Page content */
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

/* Form */
.create-form {
  max-width: 600px;
  margin: 0 auto;
}

.form-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}

.card-title {
  margin: 0 0 var(--space-5);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.form-group {
  margin-bottom: var(--space-5);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
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

.form-input.has-error {
  border-color: var(--color-danger);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.error-text {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-danger);
}

/* Form actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

</style>
