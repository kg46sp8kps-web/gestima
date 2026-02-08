<script setup lang="ts">
/**
 * Infor Connection Tab - Test and display connection status
 */

import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits<{
  (e: 'connection-change', status: any): void
}>()

// State
const loading = ref(false)
const connectionStatus = ref<any>(null)
const connectionError = ref<string | null>(null)

// Computed
const isConnected = computed(() => connectionStatus.value?.connected === true)

// Methods
async function testConnection() {
  loading.value = true
  connectionError.value = null

  try {
    const response = await axios.get('/api/infor/test-connection')
    connectionStatus.value = response.data
    emit('connection-change', response.data)

    if (!response.data.connected) {
      connectionError.value = response.data.error || 'Connection failed'
    }
  } catch (error: any) {
    connectionError.value = error.response?.data?.detail || error.message
    connectionStatus.value = null
    emit('connection-change', null)
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  testConnection()
})

// Expose for parent
defineExpose({ testConnection, isConnected })
</script>

<template>
  <div class="connection-tab">
    <button @click="testConnection" :disabled="loading" class="btn btn-primary mb-4">
      <svg v-if="loading" class="icon spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
      {{ loading ? 'Testing...' : 'Test Connection' }}
    </button>

    <div v-if="connectionStatus" class="connection-info">
      <div class="info-grid">
        <div class="info-card">
          <div class="info-label">Status</div>
          <div class="info-value" :class="isConnected ? 'success' : 'error'">
            {{ connectionStatus.status }}
          </div>
        </div>
        <div class="info-card">
          <div class="info-label">Token</div>
          <div class="info-value" :class="connectionStatus.token_acquired ? 'success' : 'error'">
            {{ connectionStatus.token_acquired ? 'Acquired' : 'Not acquired' }}
          </div>
        </div>
        <div class="info-card full-width">
          <div class="info-label">Base URL</div>
          <div class="info-value mono">{{ connectionStatus.base_url }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">Config</div>
          <div class="info-value mono">{{ connectionStatus.config }}</div>
        </div>
        <div class="info-card">
          <div class="info-label">Available Configs</div>
          <div class="info-value mono">{{ connectionStatus.configurations?.join(', ') || 'N/A' }}</div>
        </div>
      </div>
      <div v-if="connectionError" class="error-box"><strong>Error:</strong> {{ connectionError }}</div>
    </div>
  </div>
</template>

<style scoped>
.connection-tab {
  padding: var(--space-4);
  max-width: 1200px;
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

.mb-4 {
  margin-bottom: var(--space-4);
}

.connection-info {
  margin-top: var(--space-4);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.info-card {
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.info-card.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-bottom: var(--space-1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.mono {
  font-family: 'Monaco', monospace;
  font-size: var(--text-xs);
  word-break: break-all;
}

.info-value.success {
  color: var(--color-success);
}

.info-value.error {
  color: var(--color-danger);
}

.error-box {
  padding: var(--space-3);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  color: var(--color-danger);
  font-size: var(--text-sm);
  margin-top: var(--space-4);
}

.icon {
  width: 16px;
  height: 16px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
