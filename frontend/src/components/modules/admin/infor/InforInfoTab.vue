<script setup lang="ts">
/**
 * Infor Info Tab - Get detailed IDO metadata
 */

import { ref } from 'vue'
import { getInforIdoInfo } from '@/api/infor-import'
import { alert } from '@/composables/useDialog'

const props = defineProps<{
  isConnected: boolean
}>()

// State
const selectedIdoForInfo = ref('')
const idoInfo = ref<Array<{ name: string; dataType?: string; required?: boolean }> | null>(null)
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
    const data = await getInforIdoInfo(selectedIdoForInfo.value)
    idoInfo.value = data.info
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    await alert({
      title: 'Chyba',
      message: 'Failed to get IDO info: ' + (err.response?.data?.detail || err.message || 'Unknown error'),
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
  padding: 12px;
  max-width: 1200px;
}

.description {
  font-size: var(--fs);
  color: var(--t3);
  margin-bottom: 12px;
}

.form-row {
  display: flex;
  gap: var(--pad);
  align-items: center;
}

.input {
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

.flex-1 {
  flex: 1;
}


.info-box {
  padding: var(--pad);
  background: var(--surface);
  border-radius: var(--r);
  margin-top: 12px;
  border: 1px solid var(--b2);
}

.json-preview {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--t1);
  overflow-x: auto;
  margin: 0;
  max-height: 500px;
  overflow-y: auto;
}
</style>
