<script setup lang="ts">
/**
 * PDFPreview - Fast PDF card with instant click
 *
 * Features:
 * - Instant load (no iframe rendering)
 * - File icon + metadata
 * - Click to open full viewer
 * - Design system compliant
 */

import { FileText } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  src: string // PDF URL (not used for display, just for reference)
  width?: string
  height?: string
  clickable?: boolean
  filename?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '150px',
  height: '200px',
  clickable: true,
  filename: 'Drawing.pdf'
})

const emit = defineEmits<{
  'click': []
}>()

function handleClick() {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<template>
  <div
    class="pdf-preview-card"
    :class="{ clickable: clickable }"
    :style="{ width, height }"
    @click="handleClick"
  >
    <!-- PDF Icon -->
    <div class="pdf-icon">
      <FileText :size="ICON_SIZE.HERO" :stroke-width="1.5" />
    </div>

    <!-- Filename -->
    <div class="pdf-info">
      <p class="pdf-filename">{{ filename }}</p>
      <p class="pdf-hint">Klikni pro otevření</p>
    </div>
  </div>
</template>

<style scoped>
.pdf-preview-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  transition: var(--transition-fast);
}

.pdf-preview-card.clickable {
  cursor: pointer;
}

.pdf-preview-card.clickable:hover {
  border-color: var(--color-primary);
  background: var(--bg-raised);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.pdf-preview-card.clickable:hover .pdf-icon {
  color: var(--color-primary);
  transform: scale(1.1);
}

.pdf-icon {
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.pdf-info {
  text-align: center;
  width: 100%;
}

.pdf-filename {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
  margin: 0 0 var(--space-1) 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pdf-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: 0;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.pdf-preview-card.clickable:hover .pdf-hint {
  opacity: 1;
}
</style>
