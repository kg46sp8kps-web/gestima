<script setup lang="ts">
/**
 * CoefficientsInput - Koeficienty plnění a využití strojů
 * BUILDING BLOCKS (L-039): Reusable component
 */

interface Props {
  manningCoefficient: number
  machineUtilizationCoefficient: number
  disabled?: boolean
}

interface Emits {
  (e: 'update:manning', value: number): void
  (e: 'update:machineUtilization', value: number): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<Emits>()

function handleManningInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:manning', value)
}

function handleUtilizationInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update:machineUtilization', value)
}
</script>

<template>
  <div class="coefficients-input">
    <div class="coefficient-field">
      <label class="coefficient-label">Plnění:</label>
      <input
        type="number"
        step="5"
        min="0"
        max="200"
        :value="manningCoefficient"
        @input="handleManningInput"
        :disabled="disabled"
        class="coefficient-value"
      />
      <span class="coefficient-unit">%</span>
    </div>

    <span class="separator">|</span>

    <div class="coefficient-field">
      <label class="coefficient-label">Využití:</label>
      <input
        type="number"
        step="5"
        min="0"
        max="200"
        :value="machineUtilizationCoefficient"
        @input="handleUtilizationInput"
        :disabled="disabled"
        class="coefficient-value"
      />
      <span class="coefficient-unit">%</span>
    </div>
  </div>
</template>

<style scoped>
.coefficients-input {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.coefficient-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.coefficient-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.coefficient-value {
  width: 50px;
  padding: var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-align: right;
}

.coefficient-value:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.coefficient-value:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-muted);
}

.coefficient-unit {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.separator {
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
</style>
