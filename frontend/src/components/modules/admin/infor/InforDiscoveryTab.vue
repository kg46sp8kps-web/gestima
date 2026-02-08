<script setup lang="ts">
/**
 * Infor Discovery Tab - Find available IDO collections
 */

import { ref, computed } from 'vue'
import axios from 'axios'
import { alert } from '@/composables/useDialog'
import { ArrowRight } from 'lucide-vue-next'

const props = defineProps<{
  isConnected: boolean
}>()

const emit = defineEmits<{
  (e: 'browse-ido', idoName: string): void
}>()

// State
const discoveryLoading = ref(false)
const discoveryResults = ref<{ found: string[]; not_found: string[] } | null>(null)
const customIdoNames = ref('')

// Computed
const foundIdos = computed(() => {
  if (!discoveryResults.value) return []
  return discoveryResults.value.found || []
})

// Methods
async function runDiscovery() {
  discoveryLoading.value = true

  try {
    const params = customIdoNames.value ? { custom_names: customIdoNames.value } : {}
    const response = await axios.get('/api/infor/discover-idos', { params })
    discoveryResults.value = response.data
  } catch (error: any) {
    await alert({
      title: 'Chyba',
      message: 'Discovery failed: ' + (error.response?.data?.detail || error.message),
      type: 'error'
    })
  } finally {
    discoveryLoading.value = false
  }
}

function useIdoForBrowse(idoName: string) {
  emit('browse-ido', idoName)
}
</script>

<template>
  <div class="discovery-tab">
    <p class="description">Find available IDO (Intelligent Data Objects) collections</p>

    <div class="form-group">
      <label>Custom IDO Names (comma-separated, optional)</label>
      <input v-model="customIdoNames" type="text" placeholder="e.g., SLItems,Items,ItemMaster" class="input" />
    </div>

    <button @click="runDiscovery" :disabled="discoveryLoading || !props.isConnected" class="btn btn-primary">
      {{ discoveryLoading ? 'Discovering...' : 'Run Discovery' }}
    </button>

    <div v-if="discoveryResults" class="discovery-results">
      <div v-if="foundIdos.length > 0" class="found-box">
        <div class="result-header">Found IDOs ({{ foundIdos.length }})</div>
        <div class="ido-list">
          <div v-for="ido in foundIdos" :key="ido" class="ido-item">
            <span class="ido-name">{{ ido }}</span>
            <button @click="useIdoForBrowse(ido)" class="btn-link">
              Browse <ArrowRight :size="14" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="discoveryResults.not_found.length > 0" class="not-found-box">
        <div class="result-header">Not Found ({{ discoveryResults.not_found.length }})</div>
        <div class="tag-list">
          <span v-for="ido in discoveryResults.not_found" :key="ido" class="tag">{{ ido }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.discovery-tab {
  padding: var(--space-4);
  max-width: 1200px;
}

.description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
}

.form-group {
  margin-bottom: var(--space-3);
}

.form-group label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
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
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-link {
  background: transparent;
  border: none;
  color: var(--color-primary);
  font-size: var(--text-xs);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  text-decoration: underline;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.discovery-results {
  margin-top: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.found-box {
  padding: var(--space-4);
  background: rgba(5, 150, 105, 0.1);
  border: 1px solid rgba(5, 150, 105, 0.3);
  border-radius: var(--radius-md);
}

.not-found-box {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.result-header {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-bottom: var(--space-3);
}

.ido-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ido-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2);
  background: var(--bg-base);
  border-radius: var(--radius-sm);
}

.ido-name {
  font-family: 'Monaco', monospace;
  font-size: var(--text-sm);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-raised);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: 'Monaco', monospace;
}
</style>
