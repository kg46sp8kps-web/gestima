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
  gap: var(--pad);
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.coop-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  color: var(--t1);
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
  gap: var(--pad);
  padding: var(--pad);
  background: rgba(251,191,36,0.1);
  border-radius: var(--r);
  border: 1px solid var(--warn);
}

.coop-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coop-field label {
  font-size: var(--fs);
  color: var(--t3);
}

.coop-input {
  width: 80px;
  padding: 4px 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--ground);
  color: var(--t1);
  font-size: var(--fs);
}

.coop-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}

.coop-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--surface);
}
</style>
