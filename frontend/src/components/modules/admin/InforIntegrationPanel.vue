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
import { Plug, Search, Globe, Info, Download, DollarSign, Lock, Package, Route, Factory } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{
  isConnected: boolean
}>()

const emit = defineEmits<{
  (e: 'connection-change', status: any): void
}>()

// Sub-tabs
type InforSubTab = 'connection' | 'discovery' | 'browser' | 'info' | 'import' | 'prices' | 'parts' | 'routing' | 'production'
const activeInforTab = ref<InforSubTab>('connection')

// Connection status (local)
const localIsConnected = ref(false)

// Selected IDO for browser (passed from discovery)
const selectedIdoForBrowser = ref('')

// Refs for child components
const browserTabRef = ref<InstanceType<typeof InforBrowserTab> | null>(null)

// Methods
function handleConnectionChange(status: any) {
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
      <button @click="activeInforTab = 'production'" :class="['sub-tab', { active: activeInforTab === 'production' }]">
        <Factory :size="ICON_SIZE.SMALL" /> VP záznamy
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

      <InforProductionImportTab
        v-else-if="activeInforTab === 'production'"
        :is-connected="localIsConnected || props.isConnected"
      />
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
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.sub-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.sub-tab:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.sub-tab.active {
  color: var(--color-primary);
  background: rgba(153, 27, 27, 0.1);
}

.security-note {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
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
