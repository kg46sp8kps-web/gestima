<script setup lang="ts">
/**
 * File Item - Jeden soubor v seznamu
 */

import type { FileWithLinks } from '@/types/file'
import { FileText, File, Star, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  file: FileWithLinks
  selected: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  click: [file: FileWithLinks]
}>()

// File icons mapping
const fileIcons: Record<string, typeof FileText> = {
  pdf: FileText,
  step: File,
  nc: File,
  xlsx: File
}

// Format file size
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Check if file is orphan
const isOrphan = props.file.links.length === 0 && props.file.status !== 'temp'

// Get icon component for file type
function getFileIcon(fileType: string) {
  return fileIcons[fileType] || File
}
</script>

<template>
  <div
    class="file-item"
    :class="{ selected, orphan: isOrphan }"
    @click="emit('click', file)"
  >
    <!-- File icon + name -->
    <div class="file-header">
      <component :is="getFileIcon(file.file_type)" :size="ICON_SIZE.STANDARD" class="file-icon" />
      <div class="file-info">
        <span class="file-name">{{ file.original_filename }}</span>
        <span class="file-size">{{ formatSize(file.file_size) }}</span>
      </div>
    </div>

    <!-- Links -->
    <div v-if="file.links.length > 0" class="file-links">
      <div v-for="link in file.links" :key="link.id" class="link-badge">
        <span>{{ link.entity_name || `${link.entity_type} #${link.entity_id}` }}</span>
        <Star v-if="link.is_primary" :size="ICON_SIZE.SMALL" class="primary-icon" />
      </div>
    </div>

    <!-- Orphan warning -->
    <div v-else class="orphan-warning">
      <AlertTriangle :size="ICON_SIZE.SMALL" />
      <span>No links (orphan)</span>
    </div>
  </div>
</template>

<style scoped>
.file-item {
  padding: var(--pad);
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  cursor: pointer;
  transition: all 100ms;
}

.file-item:hover {
  border-color: var(--red);
  background: var(--raised);
}

.file-item.selected {
  border-color: var(--b3);
  background: var(--b1);
}

.file-item.orphan {
  border-left: 3px solid var(--warn);
}

.file-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.file-icon {
  flex-shrink: 0;
  color: var(--red);
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: var(--fs);
  color: var(--t3);
  font-family: var(--mono);
}

.file-links {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.link-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: var(--base);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  color: var(--t3);
}

.primary-icon {
  color: var(--warn);
}

.orphan-warning {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding: 4px 6px;
  background: rgba(251,191,36,0.15);
  border-radius: var(--rs);
  font-size: var(--fs);
  color: var(--warn);
}
</style>
