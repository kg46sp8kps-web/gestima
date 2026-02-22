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
  padding: 12px;
  border-bottom: 1px solid var(--b2);
}

.file-metadata h4 {
  margin: 0 0 var(--pad) 0;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--pad);
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metadata-item label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
  text-transform: uppercase;
}

.metadata-item span {
  font-size: var(--fs);
  color: var(--t1);
}

.mono {
  font-family: var(--mono);
}

.status-badge {
  display: inline-block;
  padding: 4px 6px;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 500;
  text-transform: uppercase;
  width: fit-content;
}

.status-active {
  background: rgba(34,197,94,0.15);
  color: var(--ok);
}

.status-temp {
  background: var(--ground);
  color: var(--t3);
}

.status-archived {
  background: var(--ground);
  color: var(--t3);
}
</style>
