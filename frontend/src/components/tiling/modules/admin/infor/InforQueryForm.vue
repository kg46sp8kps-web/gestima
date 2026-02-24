<script setup lang="ts">
import Input from '@/components/ui/Input.vue'

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
      <Input
        :model-value="properties"
        @update:model-value="emit('update:properties', $event as string)"
        label="Properties"
      />
    </div>
    <div class="form-group">
      <Input
        :model-value="filter"
        @update:model-value="emit('update:filter', $event as string)"
        label="Filter (SQL WHERE)"
        placeholder="Item LIKE 'A%'"
      />
    </div>
    <div class="form-group">
      <Input
        :model-value="orderBy"
        @update:model-value="emit('update:orderBy', $event as string)"
        label="Order By"
      />
    </div>
    <div class="form-group">
      <label>Limit</label>
      <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
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
  gap: var(--pad);
}


</style>
