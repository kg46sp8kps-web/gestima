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
        <span>{{ link.entity_type }} #{{ link.entity_id }}</span>
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
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.file-item:hover {
  border-color: var(--color-primary);
  background: var(--bg-raised);
}

.file-item.selected {
  border-color: var(--color-primary);
  background: var(--state-selected);
}

.file-item.orphan {
  border-left: 3px solid var(--color-warning);
}

.file-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.file-icon {
  flex-shrink: 0;
  color: var(--color-primary);
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.file-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.file-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-2);
}

.link-badge {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  color: var(--text-secondary);
}

.primary-icon {
  color: var(--color-warning);
}

.orphan-warning {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-2);
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  color: var(--color-warning);
}
</style>
