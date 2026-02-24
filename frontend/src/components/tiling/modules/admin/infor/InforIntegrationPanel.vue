<script setup lang="ts">
/**
 * Infor Integration Panel — COORDINATOR for all Infor sub-tabs
 *
 * Houses 15 tabs for Sync, Connection, Discovery, Browser, Import, etc.
 * Adapted from admin/InforIntegrationPanel.vue for v3 tiling workspace.
 */

import { ref } from 'vue'
import InforConnectionTab from './InforConnectionTab.vue'
import InforDiscoveryTab from './InforDiscoveryTab.vue'
import InforBrowserTab from './InforBrowserTab.vue'
import InforInfoTab from './InforInfoTab.vue'
import InforMaterialImportPanel from './InforMaterialImportPanel.vue'
import InforPurchasePricesTab from './InforPurchasePricesTab.vue'
import InforPartsImportTab from './InforPartsImportTab.vue'
import InforRoutingImportTab from './InforRoutingImportTab.vue'
import InforProductionImportTab from './InforProductionImportTab.vue'
import InforJobMaterialsImportTab from './InforJobMaterialsImportTab.vue'
import DrawingImportPanel from './DrawingImportPanel.vue'
import InforDocumentImportTab from './InforDocumentImportTab.vue'
import FtDataDebugTab from './FtDataDebugTab.vue'
import InforSyncDashboardTab from './InforSyncDashboardTab.vue'
import InforWcMappingEditor from './InforWcMappingEditor.vue'
import {
  Plug, Search, Globe, Info, Download, DollarSign, Lock,
  Package, Route, Factory, FileText, Layers, Brain, RefreshCw, Map,
} from 'lucide-vue-next'
import { ICON_SIZE_SM } from '@/config/design'

defineProps<{
  isConnected?: boolean
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

type InforSubTab =
  | 'sync' | 'settings' | 'connection' | 'discovery' | 'browser' | 'info'
  | 'import' | 'prices' | 'parts' | 'routing' | 'job-materials' | 'production'
  | 'drawings' | 'documents' | 'ft-data'

const activeInforTab = ref<InforSubTab>('sync')
const localIsConnected = ref(false)
const selectedIdoForBrowser = ref('')
const browserTabRef = ref<InstanceType<typeof InforBrowserTab> | null>(null)

function handleConnectionChange(status: ConnectionStatus | null) {
  localIsConnected.value = status?.connected === true
  emit('connection-change', status)
}

function handleBrowseIdo(idoName: string) {
  selectedIdoForBrowser.value = idoName
  activeInforTab.value = 'browser'
}

const connected = () => localIsConnected.value
</script>

<template>
  <div class="infor-panel">
    <!-- SUB TABS -->
    <div class="ptabs">
      <button :class="['ptab', activeInforTab === 'sync' ? 'on' : '']" data-testid="infor-tab-sync" @click="activeInforTab = 'sync'">
        <RefreshCw :size="ICON_SIZE_SM" /> Sync
      </button>
      <button :class="['ptab', activeInforTab === 'settings' ? 'on' : '']" data-testid="infor-tab-settings" @click="activeInforTab = 'settings'">
        <Map :size="ICON_SIZE_SM" /> Nastavení
      </button>
      <button :class="['ptab', activeInforTab === 'connection' ? 'on' : '']" data-testid="infor-tab-connection" @click="activeInforTab = 'connection'">
        <Plug :size="ICON_SIZE_SM" /> Connection
      </button>
      <button :class="['ptab', activeInforTab === 'discovery' ? 'on' : '']" data-testid="infor-tab-discovery" @click="activeInforTab = 'discovery'">
        <Search :size="ICON_SIZE_SM" /> Discovery
      </button>
      <button :class="['ptab', activeInforTab === 'browser' ? 'on' : '']" data-testid="infor-tab-browser" @click="activeInforTab = 'browser'">
        <Globe :size="ICON_SIZE_SM" /> Browser
      </button>
      <button :class="['ptab', activeInforTab === 'info' ? 'on' : '']" data-testid="infor-tab-info" @click="activeInforTab = 'info'">
        <Info :size="ICON_SIZE_SM" /> Info
      </button>
      <button :class="['ptab', activeInforTab === 'import' ? 'on' : '']" data-testid="infor-tab-import" @click="activeInforTab = 'import'">
        <Download :size="ICON_SIZE_SM" /> Materiály
      </button>
      <button :class="['ptab', activeInforTab === 'parts' ? 'on' : '']" data-testid="infor-tab-parts" @click="activeInforTab = 'parts'">
        <Package :size="ICON_SIZE_SM" /> Položky
      </button>
      <button :class="['ptab', activeInforTab === 'routing' ? 'on' : '']" data-testid="infor-tab-routing" @click="activeInforTab = 'routing'">
        <Route :size="ICON_SIZE_SM" /> Technologie
      </button>
      <button :class="['ptab', activeInforTab === 'job-materials' ? 'on' : '']" data-testid="infor-tab-job-materials" @click="activeInforTab = 'job-materials'">
        <Layers :size="ICON_SIZE_SM" /> Mat. Tech
      </button>
      <button :class="['ptab', activeInforTab === 'production' ? 'on' : '']" data-testid="infor-tab-production" @click="activeInforTab = 'production'">
        <Factory :size="ICON_SIZE_SM" /> VP záznamy
      </button>
      <button :class="['ptab', activeInforTab === 'drawings' ? 'on' : '']" data-testid="infor-tab-drawings" @click="activeInforTab = 'drawings'">
        <FileText :size="ICON_SIZE_SM" /> Výkresy
      </button>
      <button :class="['ptab', activeInforTab === 'documents' ? 'on' : '']" data-testid="infor-tab-documents" @click="activeInforTab = 'documents'">
        <FileText :size="ICON_SIZE_SM" /> Dokumenty
      </button>
      <button :class="['ptab', activeInforTab === 'ft-data' ? 'on' : '']" data-testid="infor-tab-ft-data" @click="activeInforTab = 'ft-data'">
        <Brain :size="ICON_SIZE_SM" /> FT Data
      </button>
      <button :class="['ptab', activeInforTab === 'prices' ? 'on' : '']" data-testid="infor-tab-prices" @click="activeInforTab = 'prices'">
        <DollarSign :size="ICON_SIZE_SM" /> Ceny
      </button>
      <div class="security-note">
        <Lock :size="ICON_SIZE_SM" /> READ-ONLY
      </div>
    </div>

    <!-- TAB CONTENT -->
    <div class="tab-content">
      <InforSyncDashboardTab v-if="activeInforTab === 'sync'" />

      <InforWcMappingEditor v-else-if="activeInforTab === 'settings'" />

      <InforConnectionTab
        v-else-if="activeInforTab === 'connection'"
        @connection-change="handleConnectionChange"
      />

      <InforDiscoveryTab
        v-else-if="activeInforTab === 'discovery'"
        :is-connected="connected()"
        @browse-ido="handleBrowseIdo"
      />

      <InforBrowserTab
        v-else-if="activeInforTab === 'browser'"
        ref="browserTabRef"
        :is-connected="connected()"
        :initial-ido="selectedIdoForBrowser"
      />

      <InforInfoTab
        v-else-if="activeInforTab === 'info'"
        :is-connected="connected()"
      />

      <InforMaterialImportPanel
        v-else-if="activeInforTab === 'import'"
        :is-connected="connected()"
      />

      <InforPartsImportTab
        v-else-if="activeInforTab === 'parts'"
        :is-connected="connected()"
      />

      <InforRoutingImportTab
        v-else-if="activeInforTab === 'routing'"
        :is-connected="connected()"
      />

      <InforJobMaterialsImportTab
        v-else-if="activeInforTab === 'job-materials'"
        :is-connected="connected()"
      />

      <InforProductionImportTab
        v-else-if="activeInforTab === 'production'"
        :is-connected="connected()"
      />

      <DrawingImportPanel v-else-if="activeInforTab === 'drawings'" />

      <InforDocumentImportTab
        v-else-if="activeInforTab === 'documents'"
        :is-connected="connected()"
      />

      <FtDataDebugTab v-else-if="activeInforTab === 'ft-data'" />

      <InforPurchasePricesTab
        v-else-if="activeInforTab === 'prices'"
        :is-connected="connected()"
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

.ptabs {
  display: flex;
  align-items: center;
  gap: 1px;
  padding: 3px var(--pad);
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.ptab {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  border: none;
  background: transparent;
  color: var(--t4);
  font-size: var(--fsm);
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--rs);
  font-family: var(--font);
}

.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }

.security-note {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fsm);
  color: var(--t3);
  padding: 2px 6px;
  background: var(--raised);
  border-radius: var(--rs);
}

.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
