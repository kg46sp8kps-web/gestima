<script setup lang="ts">
import { ref } from 'vue'
import { FileUp, Info } from 'lucide-vue-next'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

interface Emits {
  (e: 'upload', file: File): void
}

const emit = defineEmits<Emits>()

const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function triggerFileSelect() {
  fileInput.value?.click()
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) {
      await uploadPDF(file)
    }
  }
}

async function handleDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') {
      await uploadPDF(file)
    } else if (file) {
      await alert({
        title: 'Nepodporovaný formát',
        message: 'Pouze PDF soubory jsou podporovány',
        type: 'warning'
      })
    }
  }
}

async function uploadPDF(file: File) {
  if (file.size > 10 * 1024 * 1024) {
    await alert({
      title: 'Soubor je příliš velký',
      message: 'PDF je příliš velké. Maximum je 10 MB.',
      type: 'warning'
    })
    return
  }

  emit('upload', file)
}

function handleDragEnter() {
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}
</script>

<template>
  <div class="upload-section">
    <div
      class="upload-dropzone"
      :class="{ dragging: isDragging }"
      @click="triggerFileSelect"
      @drop.prevent="handleDrop"
      @dragover.prevent
      @dragenter.prevent="handleDragEnter"
      @dragleave.prevent="handleDragLeave"
    >
      <FileUp :size="ICON_SIZE.HERO" class="upload-icon" />
      <h2>Nahrajte PDF poptávky</h2>
      <p>Klikněte nebo přetáhněte PDF sem</p>
      <p class="upload-hint">Maximum 10 MB</p>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="application/pdf"
      @change="handleFileSelect"
      style="display: none"
    />

    <!-- Info panel -->
    <div class="info-panel">
      <h3><Info :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: var(--space-3);" /> Jak to funguje?</h3>
      <ul>
        <li>Nahraje se PDF s poptávkou (obsahuje zákazníka + díly + množství)</li>
        <li>AI Vision extrahuje: firma, IČO, kontakt, díly, počty kusů</li>
        <li>Systém hledá existující zákazníky a díly v databázi</li>
        <li>Automaticky přiřadí ceny z vhodných zamražených dávek</li>
        <li>Vy zkontrolujete, upravíte a potvrdíte → vytvoří se nabídka</li>
      </ul>
      <p class="info-note">
        <strong>Bezpečnost:</strong> AI pouze navrhuje, vy máte finální kontrolu. Ceny jsou
        konzervativní (raději vyšší než nižší).
      </p>
    </div>
  </div>
</template>

<style scoped>
.upload-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 800px;
  margin: 0 auto;
}

.upload-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12);
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  cursor: pointer;
  transition: all 0.2s;
}

.upload-dropzone:hover {
  border-color: var(--palette-primary);
  background: var(--state-hover);
}

.upload-dropzone.dragging {
  border-color: var(--palette-primary);
  background: var(--palette-primary-faint);
}

.upload-icon {
  color: var(--palette-primary);
}

.upload-dropzone h2 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.upload-dropzone p {
  margin: 0;
  color: var(--text-secondary);
}

.upload-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.info-panel {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.info-panel h3 {
  margin: 0 0 var(--space-3) 0;
  color: var(--text-primary);
  font-size: var(--text-base);
}

.info-panel ul {
  margin: 0 0 var(--space-3) 0;
  padding-left: var(--space-5);
  color: var(--text-body);
}

.info-panel li {
  margin-bottom: var(--space-1);
}

.info-note {
  margin: 0;
  padding: var(--space-2);
  background: var(--palette-warning-faint);
  border-left: 3px solid var(--palette-warning);
  font-size: var(--text-sm);
  color: var(--text-body);
}
</style>
