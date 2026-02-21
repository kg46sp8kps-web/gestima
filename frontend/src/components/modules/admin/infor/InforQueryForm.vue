<script setup lang="ts">
interface Props {
  properties: string
  filter: string
  orderBy: string
  limit: number
}

defineProps<Props>()

const emit = defineEmits<{
  'update:properties': [value: string]
  'update:filter': [value: string]
  'update:orderBy': [value: string]
  'update:limit': [value: number]
}>()
</script>

<template>
  <div class="form-grid">
    <div class="form-group">
      <label>Properties</label>
      <input
        :value="properties"
        @input="emit('update:properties', ($event.target as HTMLInputElement).value)"
        type="text"
        class="input"
      />
    </div>
    <div class="form-group">
      <label>Filter (SQL WHERE)</label>
      <input
        :value="filter"
        @input="emit('update:filter', ($event.target as HTMLInputElement).value)"
        type="text"
        placeholder="Item LIKE 'A%'"
        class="input"
      />
    </div>
    <div class="form-group">
      <label>Order By</label>
      <input
        :value="orderBy"
        @input="emit('update:orderBy', ($event.target as HTMLInputElement).value)"
        type="text"
        class="input"
      />
    </div>
    <div class="form-group">
      <label>Limit</label>
      <input
        :value="limit"
        @input="emit('update:limit', parseInt(($event.target as HTMLInputElement).value, 10))"
        type="number"
        min="-1"
        max="10000"
        class="input"
      />
    </div>
  </div>
</template>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.input:focus {
  outline: none;
  border-color: var(--border-strong);
}
</style>
