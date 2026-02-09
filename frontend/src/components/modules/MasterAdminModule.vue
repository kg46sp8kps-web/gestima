<script setup lang="ts">
/**
 * Master Admin Module - Unified admin floating window COORDINATOR
 *
 * Tab system coordinator - delegates to specialized panels:
 * - InforIntegrationPanel: Infor ERP connection, discovery, browser, import
 * - MaterialNormsPanel: Material norms CRUD
 * - MaterialGroupsPanel: Material groups CRUD
 * - PriceCategoriesPanel: Price categories with tiers
 * - WorkCentersPanel: Work centers CRUD
 * - VisionDebugModule: PDF annotation refinement
 *
 * Refactored from 2149 LOC to <200 LOC (L-036 compliant)
 */

import { ref } from 'vue'
import InforIntegrationPanel from './admin/InforIntegrationPanel.vue'
import MaterialNormsPanel from './admin/MaterialNormsPanel.vue'
import MaterialGroupsPanel from './admin/MaterialGroupsPanel.vue'
import PriceCategoriesPanel from './admin/PriceCategoriesPanel.vue'
import WorkCentersPanel from './admin/WorkCentersPanel.vue'
import VisionDebugModule from './admin/VisionDebugModule.vue'
import MachiningTimeEstimationModule from './estimation/MachiningTimeEstimationModule.vue'
import ManualEstimationListModule from './estimation/ManualEstimationListModule.vue'
import { Cloud, ClipboardList, Tag, DollarSign, Factory, Eye, Clock, Brain } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

// Main tabs
type MainTab = 'infor' | 'norms' | 'groups' | 'categories' | 'workcenters' | 'vision' | 'machining-time' | 'ml-estimation'
const activeMainTab = ref<MainTab>('infor')

// Connection status from Infor panel
const isConnected = ref(false)

function handleConnectionChange(status: Record<string, unknown>) {
  isConnected.value = status?.connected === true
}
</script>

<template>
  <div class="master-admin-module">
    <!-- MAIN TABS -->
    <div class="main-tabs">
      <button @click="activeMainTab = 'infor'" :class="['main-tab', { active: activeMainTab === 'infor' }]">
        <Cloud :size="ICON_SIZE.STANDARD" />
        <span>Infor</span>
        <span v-if="isConnected" class="status-dot connected"></span>
        <span v-else class="status-dot disconnected"></span>
      </button>
      <button @click="activeMainTab = 'norms'" :class="['main-tab', { active: activeMainTab === 'norms' }]">
        <ClipboardList :size="ICON_SIZE.STANDARD" />
        <span>Normy</span>
      </button>
      <button @click="activeMainTab = 'groups'" :class="['main-tab', { active: activeMainTab === 'groups' }]">
        <Tag :size="ICON_SIZE.STANDARD" />
        <span>Skupiny</span>
      </button>
      <button @click="activeMainTab = 'categories'" :class="['main-tab', { active: activeMainTab === 'categories' }]">
        <DollarSign :size="ICON_SIZE.STANDARD" />
        <span>Ceny</span>
      </button>
      <button @click="activeMainTab = 'workcenters'" :class="['main-tab', { active: activeMainTab === 'workcenters' }]">
        <Factory :size="ICON_SIZE.STANDARD" />
        <span>Pracoviste</span>
      </button>
      <button @click="activeMainTab = 'vision'" :class="['main-tab', { active: activeMainTab === 'vision' }]">
        <Eye :size="ICON_SIZE.STANDARD" />
        <span>Vision Debug</span>
      </button>
      <button @click="activeMainTab = 'machining-time'" :class="['main-tab', { active: activeMainTab === 'machining-time' }]">
        <Clock :size="ICON_SIZE.STANDARD" />
        <span>Strojní časy</span>
      </button>
      <button @click="activeMainTab = 'ml-estimation'" :class="['main-tab', { active: activeMainTab === 'ml-estimation' }]">
        <Brain :size="ICON_SIZE.STANDARD" />
        <span>ML Estimation</span>
      </button>
    </div>

    <!-- TAB CONTENT -->
    <div class="tab-content">
      <InforIntegrationPanel
        v-if="activeMainTab === 'infor'"
        :is-connected="isConnected"
        @connection-change="handleConnectionChange"
      />
      <MaterialNormsPanel v-else-if="activeMainTab === 'norms'" />
      <MaterialGroupsPanel v-else-if="activeMainTab === 'groups'" />
      <PriceCategoriesPanel v-else-if="activeMainTab === 'categories'" />
      <WorkCentersPanel v-else-if="activeMainTab === 'workcenters'" />
      <VisionDebugModule v-else-if="activeMainTab === 'vision'" />
      <MachiningTimeEstimationModule v-else-if="activeMainTab === 'machining-time'" />
      <ManualEstimationListModule v-else-if="activeMainTab === 'ml-estimation'" />
    </div>
  </div>
</template>

<style scoped>
.master-admin-module {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-base);
}

/* Main Tabs */
.main-tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.main-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.main-tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.main-tab.active {
  color: var(--text-primary);
  background: var(--bg-raised);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--color-success);
}

.status-dot.disconnected {
  background: var(--color-danger);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
