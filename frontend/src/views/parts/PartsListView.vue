<script setup lang="ts">
/**
 * Parts List View - Full page parts listing
 *
 * Standalone page for browsing parts.
 * Wraps PartsListModule with page-level navigation.
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PartsListModule from '@/views/workspace/modules/PartsListModule.vue'

const router = useRouter()
const searchQuery = ref('')

// Navigate to part detail
function handlePartSelect(partNumber: string) {
  router.push({ name: 'part-detail', params: { partNumber } })
}

// Navigate to create part
function handleCreatePart() {
  router.push({ name: 'part-create' })
}
</script>

<template>
  <div class="parts-list-view">
    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <h1 class="page-title">Díly</h1>
        <p class="page-subtitle">Správa dílů a jejich technologie</p>
      </div>

      <div class="header-actions">
        <button
          class="btn btn-primary"
          @click="handleCreatePart"
          data-testid="create-part-button"
        >
          + Nový díl
        </button>
      </div>
    </header>

    <!-- Parts list module (reused from workspace) -->
    <div class="page-content">
      <PartsListModule
        :standalone="true"
        @part-select="handlePartSelect"
      />
    </div>
  </div>
</template>

<style scoped>
.parts-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

/* Page header */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

/* Page content */
.page-content {
  flex: 1;
  overflow: hidden;
  padding: var(--space-6);
}

/* Module styling override */
.page-content :deep(.parts-list-module) {
  height: 100%;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
}

</style>
