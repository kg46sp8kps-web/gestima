<script setup lang="ts">
/**
 * File Metadata - Zobrazení metadat souboru
 */

import type { FileRecord } from '@/types/file'
import { formatDate } from '@/utils/formatters'

interface Props {
  file: FileRecord
}

const props = defineProps<Props>()

// Format file size
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Truncate hash
function truncateHash(hash: string): string {
  return `${hash.slice(0, 8)}...${hash.slice(-8)}`
}
</script>

<template>
  <div class="file-metadata">
    <h4>Metadata</h4>
    <div class="metadata-grid">
      <div class="metadata-item">
        <label>Název</label>
        <span>{{ file.original_filename }}</span>
      </div>
      <div class="metadata-item">
        <label>Typ</label>
        <span>{{ file.file_type.toUpperCase() }}, {{ formatSize(file.file_size) }}</span>
      </div>
      <div class="metadata-item">
        <label>Hash</label>
        <span class="mono">{{ truncateHash(file.file_hash) }}</span>
      </div>
      <div class="metadata-item">
        <label>Nahráno</label>
        <span>{{ formatDate(file.created_at) }}</span>
      </div>
      <div class="metadata-item">
        <label>Nahrál</label>
        <span>{{ file.created_by || '-' }}</span>
      </div>
      <div class="metadata-item">
        <label>Status</label>
        <span class="status-badge" :class="`status-${file.status}`">
          {{ file.status }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-metadata {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.file-metadata h4 {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.metadata-item label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.metadata-item span {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.mono {
  font-family: var(--font-mono);
}

.status-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  width: fit-content;
}

.status-active {
  background: var(--color-success-light);
  color: var(--color-success);
}

.status-temp {
  background: var(--bg-subtle);
  color: var(--text-secondary);
}

.status-archived {
  background: var(--bg-subtle);
  color: var(--text-tertiary);
}
</style>
