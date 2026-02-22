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
  border-right: 1px solid var(--b2);
  overflow-y: auto;
  padding: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 6px 6px;
  border: none;
  background: transparent;
  color: var(--t3);
  font-size: var(--fs);
  text-align: left;
  cursor: pointer;
  border-radius: var(--rs);
  transition: background 100ms;
}

.file-item:hover { background: var(--b1); }
.file-item.active { background: var(--raised); color: var(--t1); }
.file-item.failed { opacity: 0.5; }

.fname {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-ok { color: var(--ok); }
.icon-warn { color: var(--warn); }
.icon-err { color: var(--err); }

.axis-badge {
  padding: 0 4px;
  border-radius: var(--rs);
  background: var(--b1);
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
}
</style>
