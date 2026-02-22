<script setup lang="ts">
/**
 * Infor Integration Panel - COORDINATOR for Infor sub-tabs
 *
 * Delegates to:
 * - InforConnectionTab: Test and display connection status
 * - InforDiscoveryTab: Find available IDO collections
 * - InforBrowserTab: Browse IDO data with field selection
 * - InforInfoTab: Get detailed IDO metadata
 * - InforMaterialImportPanel: Import materials from Infor
 *
 * Refactored from 963 LOC to <150 LOC (L-036 compliant)
 */

import { ref } from 'vue'
import InforConnectionTab from './infor/InforConnectionTab.vue'
import InforDiscoveryTab from './infor/InforDiscoveryTab.vue'
import InforBrowserTab from './infor/InforBrowserTab.vue'
import InforInfoTab from './infor/InforInfoTab.vue'
import InforMaterialImportPanel from '../infor/InforMaterialImportPanel.vue'
import InforPurchasePricesTab from './infor/InforPurchasePricesTab.vue'
import InforPartsImportTab from './infor/InforPartsImportTab.vue'
import InforRoutingImportTab from './infor/InforRoutingImportTab.vue'
import InforProductionImportTab from './infor/InforProductionImportTab.vue'
import InforJobMaterialsImportTab from './infor/InforJobMaterialsImportTab.vue'
import DrawingImportPanel from './DrawingImportPanel.vue'
import InforDocumentImportTab from './infor/InforDocumentImportTab.vue'
import FtDataDebugTab from './infor/FtDataDebugTab.vue'
import InforSyncDashboardTab from './infor/InforSyncDashboardTab.vue'
import { Plug, Search, Globe, Info, Download, DollarSign, Lock, Package, Route, Factory, FileText, Layers, Brain, RefreshCw } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  isConnected: boolean
}>()

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

// Sub-tabs
type InforSubTab = 'connection' | 'discovery' | 'browser' | 'info' | 'import' | 'prices' | 'parts' | 'routing' | 'job-materials' | 'production' | 'drawings' | 'documents' | 'ft-data' | 'sync'
const activeInforTab = ref<InforSubTab>('connection')

// Connection status (local)
const localIsConnected = ref(false)

// Selected IDO for browser (passed from discovery)
const selectedIdoForBrowser = ref('')

// Refs for child components
const browserTabRef = ref<InstanceType<typeof InforBrowserTab> | null>(null)

// Methods
function handleConnectionChange(status: ConnectionStatus | null) {
  localIsConnected.value = status?.connected === true
  emit('connection-change', status)
}

function handleBrowseIdo(idoName: string) {
  selectedIdoForBrowser.value = idoName
  activeInforTab.value = 'browser'
}
</script>

<template>
  <div class="infor-panel">
    <!-- SUB TABS -->
    <div class="sub-tabs">
      <button @click="activeInforTab = 'connection'" :class="['sub-tab', { active: activeInforTab === 'connection' }]">
        <Plug :size="ICON_SIZE.SMALL" /> Connection
      </button>
      <button @click="activeInforTab = 'discovery'" :class="['sub-tab', { active: activeInforTab === 'discovery' }]">
        <Search :size="ICON_SIZE.SMALL" /> Discovery
      </button>
      <button @click="activeInforTab = 'browser'" :class="['sub-tab', { active: activeInforTab === 'browser' }]">
        <Globe :size="ICON_SIZE.SMALL" /> Browser
      </button>
      <button @click="activeInforTab = 'info'" :class="['sub-tab', { active: activeInforTab === 'info' }]">
        <Info :size="ICON_SIZE.SMALL" /> Info
      </button>
      <button @click="activeInforTab = 'import'" :class="['sub-tab', { active: activeInforTab === 'import' }]">
        <Download :size="ICON_SIZE.SMALL" /> Import
      </button>
      <button @click="activeInforTab = 'prices'" :class="['sub-tab', { active: activeInforTab === 'prices' }]">
        <DollarSign :size="ICON_SIZE.SMALL" /> Nákupní ceny
      </button>
      <button @click="activeInforTab = 'parts'" :class="['sub-tab', { active: activeInforTab === 'parts' }]">
        <Package :size="ICON_SIZE.SMALL" /> Položky
      </button>
      <button @click="activeInforTab = 'routing'" :class="['sub-tab', { active: activeInforTab === 'routing' }]">
        <Route :size="ICON_SIZE.SMALL" /> Technologie
      </button>
      <button @click="activeInforTab = 'job-materials'" :class="['sub-tab', { active: activeInforTab === 'job-materials' }]">
        <Layers :size="ICON_SIZE.SMALL" /> Materiály Tech
      </button>
      <button @click="activeInforTab = 'production'" :class="['sub-tab', { active: activeInforTab === 'production' }]">
        <Factory :size="ICON_SIZE.SMALL" /> VP záznamy
      </button>
      <button @click="activeInforTab = 'drawings'" :class="['sub-tab', { active: activeInforTab === 'drawings' }]">
        <FileText :size="ICON_SIZE.SMALL" /> Výkresy
      </button>
      <button @click="activeInforTab = 'documents'" :class="['sub-tab', { active: activeInforTab === 'documents' }]">
        <FileText :size="ICON_SIZE.SMALL" /> Dokumenty
      </button>
      <button @click="activeInforTab = 'ft-data'" :class="['sub-tab', { active: activeInforTab === 'ft-data' }]">
        <Brain :size="ICON_SIZE.SMALL" /> FT Data
      </button>
      <button @click="activeInforTab = 'sync'" :class="['sub-tab', { active: activeInforTab === 'sync' }]">
        <RefreshCw :size="ICON_SIZE.SMALL" /> Sync
      </button>
      <div class="security-note">
        <Lock :size="ICON_SIZE.SMALL" /> READ-ONLY
      </div>
    </div>

    <!-- TAB CONTENT -->
    <div class="tab-content">
      <InforConnectionTab v-if="activeInforTab === 'connection'" @connection-change="handleConnectionChange" />

      <InforDiscoveryTab
        v-else-if="activeInforTab === 'discovery'"
        :is-connected="localIsConnected || props.isConnected"
        @browse-ido="handleBrowseIdo"
      />

      <InforBrowserTab
        v-else-if="activeInforTab === 'browser'"
        ref="browserTabRef"
        :is-connected="localIsConnected || props.isConnected"
        :initial-ido="selectedIdoForBrowser"
      />

      <InforInfoTab v-else-if="activeInforTab === 'info'" :is-connected="localIsConnected || props.isConnected" />

      <div v-else-if="activeInforTab === 'import'" class="import-tab">
        <InforMaterialImportPanel :is-connected="localIsConnected || props.isConnected" />
      </div>

      <InforPurchasePricesTab
        v-else-if="activeInforTab === 'prices'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <InforPartsImportTab
        v-else-if="activeInforTab === 'parts'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <InforRoutingImportTab
        v-else-if="activeInforTab === 'routing'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <InforJobMaterialsImportTab
        v-else-if="activeInforTab === 'job-materials'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <InforProductionImportTab
        v-else-if="activeInforTab === 'production'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <DrawingImportPanel v-else-if="activeInforTab === 'drawings'" />

      <InforDocumentImportTab
        v-else-if="activeInforTab === 'documents'"
        :is-connected="localIsConnected || props.isConnected"
      />

      <FtDataDebugTab v-else-if="activeInforTab === 'ft-data'" />

      <InforSyncDashboardTab v-else-if="activeInforTab === 'sync'" />
    </div>
  </div>
</template>

<style scoped>
.infor-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Sub Tabs */
.sub-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px var(--pad);
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
}

.sub-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--pad);
  border: none;
  background: transparent;
  color: var(--t3);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--rs);
  transition: all 100ms;
}

.sub-tab:hover {
  color: var(--t3);
  background: var(--b1);
}

.sub-tab.active {
  color: var(--red);
  background: var(--red-10);
}

.security-note {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  color: var(--t3);
  padding: 4px 6px;
  background: var(--raised);
  border-radius: var(--rs);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.import-tab {
  flex: 1;
  overflow: auto;
}
</style>
