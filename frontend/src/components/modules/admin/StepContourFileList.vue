<script setup lang="ts">
/**
 * STEP Contour File List
 *
 * Shows list of analyzed STEP files with status icons.
 * Emits selection events.
 */

import { CheckCircle, XCircle, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface ContourResult {
  filename: string
  success: boolean
  rotation_axis: string | null
  profile: {
    total_length: number | null
    max_diameter: number | null
    outer_contour: unknown[]
    inner_contour: unknown[]
    holes: unknown[]
  } | null
}

defineProps<{
  results: ContourResult[]
  selectedFilename: string | null
}>()

const emit = defineEmits<{
  (e: 'select', filename: string): void
}>()
</script>

<template>
  <div class="file-list">
    <button
      v-for="r in results"
      :key="r.filename"
      :class="['file-item', { active: selectedFilename === r.filename, failed: !r.success }]"
      @click="emit('select', r.filename)"
    >
      <CheckCircle v-if="r.profile" :size="ICON_SIZE.SMALL" class="icon-ok" />
      <AlertTriangle v-else-if="r.success && !r.profile" :size="ICON_SIZE.SMALL" class="icon-warn" />
      <XCircle v-else :size="ICON_SIZE.SMALL" class="icon-err" />
      <span class="fname">{{ r.filename }}</span>
      <span v-if="r.rotation_axis" class="axis-badge">{{ r.rotation_axis.toUpperCase() }}</span>
    </button>
  </div>
</template>

<style scoped>
.file-list {
  width: 240px;
  min-width: 200px;
  border-right: 1px solid var(--border-default);
  overflow-y: auto;
  padding: var(--space-1);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-2) var(--space-2);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}

.file-item:hover { background: var(--bg-hover); }
.file-item.active { background: var(--bg-raised); color: var(--text-primary); }
.file-item.failed { opacity: 0.5; }

.fname {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-ok { color: var(--color-success); }
.icon-warn { color: var(--color-warning); }
.icon-err { color: var(--color-danger); }

.axis-badge {
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-info);
}
</style>
