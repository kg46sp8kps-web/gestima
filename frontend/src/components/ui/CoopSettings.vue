<script setup lang="ts">
/**
 * CoopSettings - Kooperace (externí dodavatel) settings
 * BUILDING BLOCKS (L-039): Reusable component
 */

interface Props {
  isCoop: boolean
  coopPrice: number
  coopMinPrice: number
  coopDays: number
  disabled?: boolean
}

interface Emits {
  (e: 'toggle'): void
  (e: 'update:price', value: number): void
  (e: 'update:minPrice', value: number): void
  (e: 'update:days', value: number): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<Emits>()

function handlePriceInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:price', value)
}

function handleMinPriceInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:minPrice', value)
}

function handleDaysInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:days', value)
}
</script>

<template>
  <div class="coop-settings">
    <!-- Coop Toggle -->
    <div class="setting-group">
      <label class="coop-toggle">
        <input
          type="checkbox"
          :checked="isCoop"
          @change="emit('toggle')"
          :disabled="disabled"
        />
        Kooperace (externí dodavatel)
      </label>
    </div>

    <!-- Coop Fields (conditional) -->
    <div v-if="isCoop" class="coop-fields">
      <div class="coop-field">
        <label>Cena [Kč]</label>
        <input
          type="number"
          min="0"
          step="1"
          :value="coopPrice"
          @input="handlePriceInput"
          :disabled="disabled"
          class="coop-input"
        />
      </div>
      <div class="coop-field">
        <label>Min. cena [Kč]</label>
        <input
          type="number"
          min="0"
          step="1"
          :value="coopMinPrice"
          @input="handleMinPriceInput"
          :disabled="disabled"
          class="coop-input"
        />
      </div>
      <div class="coop-field">
        <label>Dní</label>
        <input
          type="number"
          min="0"
          :value="coopDays"
          @input="handleDaysInput"
          :disabled="disabled"
          class="coop-input"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.coop-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.coop-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.coop-toggle input {
  cursor: pointer;
}

.coop-toggle input:disabled {
  cursor: not-allowed;
}

.coop-fields {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-warning);
}

.coop-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.coop-field label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.coop-input {
  width: 80px;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.coop-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.coop-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-muted);
}
</style>
