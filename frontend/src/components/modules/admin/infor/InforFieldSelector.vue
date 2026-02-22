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
  margin: 12px 0;
  border: 1px solid var(--b2);
  border-radius: 8px;
  background: var(--surface);
}

.field-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  background: var(--raised);
  border-radius: 8px 8px 0 0;
}

.field-selector-header label {
  margin: 0;
  font-weight: 600;
}

.field-actions {
  display: flex;
  gap: var(--pad);
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  color: var(--t1);
  cursor: pointer;
}

.checkbox-label input[type='checkbox'] {
  width: auto;
  cursor: pointer;
}

.btn-link {
  background: transparent;
  border: none;
  color: var(--red);
  font-size: var(--fs);
  cursor: pointer;
  padding: 4px 6px;
  text-decoration: underline;
}

.field-search {
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b2);
}

.field-checkboxes {
  max-height: 200px;
  overflow-y: auto;
  padding: 6px;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: var(--rs);
  cursor: pointer;
}

.field-checkbox:hover {
  background: var(--b1);
}

.field-name {
  flex: 1;
  font-weight: 500;
  color: var(--t1);
}

.field-type {
  font-size: var(--fs);
  color: var(--t3);
  font-family: var(--mono);
}

.input {
  width: 100%;
  padding: 6px var(--pad);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--ground);
  color: var(--t1);
  font-size: var(--fs);
}

.input:focus {
  outline: none;
  border-color: var(--b3);
}
</style>
