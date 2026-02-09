<template>
  <section class="estimate-form">
    <h4 class="section-title">Your Estimate</h4>
    <div class="input-group">
      <input
        v-model.number="estimatedTime"
        type="number"
        class="time-input"
        placeholder="0.0"
        step="0.5"
        min="0.1"
        @keyup.enter="handleSubmit"
      />
      <span class="input-unit">minutes</span>
      <button
        class="submit-btn"
        :disabled="!canSubmit"
        @click="handleSubmit"
      >
        Save Estimate
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const emit = defineEmits<{
  (e: 'submit', time: number): void
}>()

const estimatedTime = ref<number | null>(null)

const canSubmit = computed(() => {
  return estimatedTime.value !== null && estimatedTime.value > 0
})

function handleSubmit() {
  if (canSubmit.value && estimatedTime.value) {
    emit('submit', estimatedTime.value)
    estimatedTime.value = null
  }
}
</script>

<style scoped>
.estimate-form {
  margin-bottom: var(--space-5);
}

.section-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.input-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.time-input {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-lg);
  font-weight: 600;
  font-family: var(--font-mono);
}

.time-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--bg-accent);
}

.input-unit {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.submit-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--color-success);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-inverse);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-success-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
