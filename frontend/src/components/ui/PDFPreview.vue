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
  gap: var(--pad);
  padding: 12px;
  border: 2px dashed var(--b2);
  border-radius: var(--r);
  background: var(--surface);
  transition: all 100ms var(--ease);
}

.pdf-preview-card.clickable {
  cursor: pointer;
}

.pdf-preview-card.clickable:hover {
  border-color: var(--red);
  background: var(--raised);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

.pdf-preview-card.clickable:hover .pdf-icon {
  color: var(--red);
  transform: scale(1.1);
}

.pdf-icon {
  color: var(--t3);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 100ms var(--ease);
}

.pdf-info {
  text-align: center;
  width: 100%;
}

.pdf-filename {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pdf-hint {
  font-size: var(--fs);
  color: var(--t3);
  margin: 0;
  opacity: 0;
  transition: opacity all 100ms var(--ease);
}

.pdf-preview-card.clickable:hover .pdf-hint {
  opacity: 1;
}
</style>
