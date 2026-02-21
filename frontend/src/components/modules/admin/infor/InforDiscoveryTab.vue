<script setup lang="ts">
/**
 * Infor Discovery Tab - Find available IDO collections
 */

import { ref, computed } from 'vue'
import { discoverInforIdos } from '@/api/infor-import'
import { alert } from '@/composables/useDialog'
import { ArrowRight } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

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
    const data = await discoverInforIdos(customIdoNames.value || undefined)
    discoveryResults.value = data
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    await alert({
      title: 'Chyba',
      message: 'Discovery failed: ' + (err.response?.data?.detail || err.message || 'Unknown error'),
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
              Browse <ArrowRight :size="ICON_SIZE.SMALL" />
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



.btn-link {
  background: transparent;
  border: none;
  color: var(--brand);
  font-size: var(--text-sm);
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
  background: var(--status-ok-bg);
  border: 1px solid var(--palette-success-light);
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
  font-size: var(--text-sm);
  font-family: 'Monaco', monospace;
}
</style>
