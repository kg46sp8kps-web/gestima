<script setup lang="ts">
import { ref, computed } from 'vue'

interface Field {
  name: string
  type: string
  required: boolean
  readOnly: boolean
}

interface Props {
  availableFields: Field[]
  selectedFields: string[]
  hideUdfFields?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hideUdfFields: true
})

const emit = defineEmits<{
  'toggle-field': [fieldName: string]
  'select-all': []
  'deselect-all': []
  'update:hide-udf-fields': [value: boolean]
}>()

const fieldSearchQuery = ref('')

const filteredFields = computed(() => {
  let fields = props.availableFields

  if (props.hideUdfFields) {
    fields = fields.filter(
      (field) =>
        !field.name.startsWith('UDF') &&
        !field.name.startsWith('_Item') &&
        !field.name.includes('RowPointer')
    )
  }

  if (fieldSearchQuery.value) {
    const query = fieldSearchQuery.value.toLowerCase()
    fields = fields.filter(
      (field) =>
        field.name.toLowerCase().includes(query) ||
        field.type.toLowerCase().includes(query)
    )
  }

  return fields
})
</script>

<template>
  <div class="field-selector">
    <div class="field-selector-header">
      <label>Select Fields ({{ selectedFields.length }}/{{ filteredFields.length }})</label>
      <div class="field-actions">
        <label class="checkbox-label">
          <input
            type="checkbox"
            :checked="hideUdfFields"
            @change="emit('update:hide-udf-fields', !hideUdfFields)"
          />
          <span>Hide UDF</span>
        </label>
        <button @click="emit('select-all')" class="btn-link">All</button>
        <button @click="emit('deselect-all')" class="btn-link">Clear</button>
      </div>
    </div>

    <div class="field-search">
      <input
        v-model="fieldSearchQuery"
        type="text"
        placeholder="Search fields..."
        class="input search-input"
      />
    </div>

    <div class="field-checkboxes">
      <label
        v-for="field in filteredFields"
        :key="field.name"
        class="field-checkbox"
      >
        <input
          type="checkbox"
          :checked="selectedFields.includes(field.name)"
          @change="emit('toggle-field', field.name)"
        />
        <span class="field-name">{{ field.name }}</span>
        <span class="field-type">{{ field.type }}</span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.field-selector {
  margin: var(--space-4) 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
}

.field-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.field-selector-header label {
  margin: 0;
  font-weight: 600;
}

.field-actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-label input[type='checkbox'] {
  width: auto;
  cursor: pointer;
}

.btn-link {
  background: transparent;
  border: none;
  color: var(--color-primary);
  font-size: var(--text-xs);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  text-decoration: underline;
}

.field-search {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-default);
}

.field-checkboxes {
  max-height: 200px;
  overflow-y: auto;
  padding: var(--space-2);
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.field-checkbox:hover {
  background: var(--bg-hover);
}

.field-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.field-type {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-family: monospace;
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
  border-color: var(--color-primary);
}
</style>
