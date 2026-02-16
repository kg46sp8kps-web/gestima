<script setup lang="ts">
/**
 * Infor Info Tab - Get detailed IDO metadata
 */

import { ref } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'

const props = defineProps<{
  isConnected: boolean
}>()

// State
const selectedIdoForInfo = ref('')
const idoInfo = ref<any>(null)
const idoInfoLoading = ref(false)

// Methods
async function getIdoInfo() {
  if (!selectedIdoForInfo.value) {
    await alert({
      title: 'Chyba validace',
      message: 'Please enter IDO name',
      type: 'warning'
    })
    return
  }

  idoInfoLoading.value = true
  idoInfo.value = null

  try {
    const response = await axios.get(`/api/infor/ido/${selectedIdoForInfo.value}/info`)
    idoInfo.value = response.data.info
  } catch (error: any) {
    await alert({
      title: 'Chyba',
      message: 'Failed to get IDO info: ' + (error.response?.data?.detail || error.message),
      type: 'error'
    })
  } finally {
    idoInfoLoading.value = false
  }
}
</script>

<template>
  <div class="info-tab">
    <p class="description">Get detailed metadata about IDO properties and schema</p>

    <div class="form-row">
      <input v-model="selectedIdoForInfo" type="text" placeholder="Enter IDO name" class="input flex-1" />
      <button @click="getIdoInfo" :disabled="idoInfoLoading || !props.isConnected" class="btn btn-primary">
        {{ idoInfoLoading ? 'Loading...' : 'Get Info' }}
      </button>
    </div>

    <div v-if="idoInfo" class="info-box">
      <pre class="json-preview">{{ JSON.stringify(idoInfo, null, 2) }}</pre>
    </div>
  </div>
</template>

<style scoped>
.info-tab {
  padding: var(--space-4);
  max-width: 1200px;
}

.description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.input {
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

.flex-1 {
  flex: 1;
}

.btn {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-primary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.info-box {
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  margin-top: var(--space-4);
  border: 1px solid var(--border-default);
}

.json-preview {
  font-family: 'Monaco', monospace;
  font-size: var(--text-xs);
  color: var(--text-primary);
  overflow-x: auto;
  margin: 0;
  max-height: 500px;
  overflow-y: auto;
}
</style>
