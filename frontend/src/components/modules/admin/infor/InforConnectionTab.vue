<script setup lang="ts">
/**
 * Infor Connection Tab - Test and display connection status
 */

import { ref, computed, onMounted } from 'vue'
import { testInforConnection } from '@/api/infor-import'

interface ConnectionStatus {
  connected: boolean
  error?: string
  status?: string
  token_acquired?: boolean
  base_url?: string
  config?: Record<string, unknown>
  configurations?: unknown[]
}

const emit = defineEmits<{
  (e: 'connection-change', status: ConnectionStatus | null): void
}>()

// State
const loading = ref(false)
const connectionStatus = ref<ConnectionStatus | null>(null)
const connectionError = ref<string | null>(null)

// Computed
const isConnected = computed(() => connectionStatus.value?.connected === true)

// Methods
async function testConnection() {
  loading.value = true
  connectionError.value = null

  try {
    const data = await testInforConnection()
    connectionStatus.value = data as unknown as ConnectionStatus
    emit('connection-change', data as unknown as ConnectionStatus)

    if (!data.connected) {
      connectionError.value = (data.error as string) || 'Connection failed'
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    connectionError.value = err.response?.data?.detail || err.message || 'Unknown error'
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
  padding: 12px;
  max-width: 1200px;
}


.mb-4 {
  margin-bottom: 12px;
}

.connection-info {
  margin-top: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--pad);
  margin-bottom: 12px;
}

.info-card {
  padding: var(--pad);
  background: var(--surface);
  border-radius: var(--r);
  border: 1px solid var(--b2);
}

.info-card.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--fs);
  color: var(--t3);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
}

.info-value.mono {
  font-family: var(--mono);
  font-size: var(--fs);
  word-break: break-all;
}

.info-value.success {
  color: var(--ok);
}

.info-value.error {
  color: var(--err);
}

.error-box {
  padding: var(--pad);
  background: rgba(248,113,113,0.1);
  border: 1px solid rgba(248,113,113,0.15);
  border-radius: var(--r);
  color: var(--err);
  font-size: var(--fs);
  margin-top: 12px;
}

.icon {
  width: 16px;
  height: 16px;
}

.spin {
  animation: spin 1s linear infinite;
}

</style>
