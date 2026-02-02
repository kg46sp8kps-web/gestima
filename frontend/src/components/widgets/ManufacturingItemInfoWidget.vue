<script setup lang="ts">
/**
 * ManufacturingItemInfoWidget - Part information display
 *
 * Shows:
 * - Part Number
 * - Name
 * - Drawing status
 * - Customer Revision
 *
 * @example
 * <ManufacturingItemInfoWidget :context="{ item: part }" />
 */

import { computed } from 'vue'
import { Package, FileCheck, FileX } from 'lucide-vue-next'
import type { Part } from '@/types/part'

interface Props {
  context?: {
    item?: Part | null
  }
}

const props = defineProps<Props>()
const item = computed(() => props.context?.item)
const hasDrawing = computed(() => !!item.value?.drawing_path)
</script>

<template>
  <div class="widget-root">
    <!-- Empty state -->
    <div v-if="!item" class="empty-state">
      <Package :size="48" class="empty-icon" />
      <p>Vyberte položku ze seznamu</p>
    </div>

    <!-- Content -->
    <div v-else class="info-grid">
      <div class="info-field">
        <span class="label">Part Number:</span>
        <span class="value">{{ item.part_number }}</span>
      </div>

      <div class="info-field">
        <span class="label">Name:</span>
        <span class="value">{{ item.name || '—' }}</span>
      </div>

      <div class="info-field">
        <span class="label">Drawing:</span>
        <span class="value">
          <FileCheck v-if="hasDrawing" :size="16" class="icon-success" />
          <FileX v-else :size="16" class="icon-muted" />
          {{ hasDrawing ? 'Loaded' : 'No drawing' }}
        </span>
      </div>

      <div class="info-field">
        <span class="label">Revision:</span>
        <span class="value">{{ item.customer_revision || '—' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* CRITICAL: Widget root - sizeToContent compatible */
.widget-root {
  /* NO height: 100% - allows GridStack sizeToContent! */
  display: flex;
  flex-direction: column;
  /* Padding is in WidgetWrapper now */
  /* Container-type is in WidgetWrapper - use @container widget-content for breakpoints */
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-2);
  color: var(--text-tertiary);
}

.empty-icon {
  opacity: 0.3;
}

/* Info grid - Pattern z ULTIMATE-UI-GUIDE.md */
.info-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.value {
  font-size: var(--text-base);
  color: var(--text-body);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.icon-success {
  color: var(--color-success);
  flex-shrink: 0;
}

.icon-muted {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

/* Container query: horizontal layout on wide widgets */
/* Use widget-content container from WidgetWrapper */
@container widget-content (min-width: 400px) {
  .info-field {
    flex-direction: row;
    align-items: baseline;
    gap: var(--space-2);
  }

  .label {
    min-width: 120px;
    flex-shrink: 0;
  }

  .value {
    flex: 1;
  }
}
</style>
