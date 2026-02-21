<script setup lang="ts">
/**
 * QuoteRequestUploadStep — Step 1 of V2 quote wizard
 * Single drop zone for all PDFs. Each file gets a type badge
 * (Poptávka / Výkres) auto-detected from filename, user can toggle.
 */
import { ref, computed } from 'vue'
import { FileUp, FileText, X, Sparkles, Info } from 'lucide-vue-next'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

export interface FileWithType {
  file: File
  type: 'request' | 'drawing'
}

const emit = defineEmits<{
  'analyze': [files: FileWithType[]]
}>()

const items = ref<FileWithType[]>([])
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const MAX_SIZE = 10 * 1024 * 1024 // 10 MB

// Keywords that suggest a file is a quote request
const REQUEST_KEYWORDS = ['poptav', 'request', 'rfq', 'objedna', 'nabid', 'inquiry', 'anfrage']

function detectType(filename: string): 'request' | 'drawing' {
  const lower = filename.toLowerCase()
  return REQUEST_KEYWORDS.some(kw => lower.includes(kw)) ? 'request' : 'drawing'
}

const hasRequest = computed(() => items.value.some(f => f.type === 'request'))
const hasDrawing = computed(() => items.value.some(f => f.type === 'drawing'))
const canAnalyze = computed(() => items.value.length > 0 && hasRequest.value)

async function validateAndAdd(file: File) {
  if (file.type !== 'application/pdf') {
    await alert({ title: 'Nepodporovaný formát', message: `${file.name} — pouze PDF soubory jsou podporovány.`, type: 'warning' })
    return
  }
  if (file.size > MAX_SIZE) {
    await alert({ title: 'Soubor příliš velký', message: `${file.name} překračuje limit 10 MB.`, type: 'warning' })
    return
  }
  if (!items.value.some(f => f.file.name === file.name)) {
    items.value.push({ file, type: detectType(file.name) })
  }
}

function toggleType(index: number) {
  const item = items.value[index]
  if (item) {
    item.type = item.type === 'request' ? 'drawing' : 'request'
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const dropped = e.dataTransfer?.files
  if (dropped) Array.from(dropped).forEach(f => validateAndAdd(f))
}

function handleSelect(e: Event) {
  const selected = (e.target as HTMLInputElement).files
  if (selected) Array.from(selected).forEach(f => validateAndAdd(f))
  if (fileInput.value) fileInput.value.value = ''
}

function removeFile(index: number) { items.value.splice(index, 1) }
function formatSize(bytes: number): string { return (bytes / 1024 / 1024).toFixed(1) + ' MB' }
function handleAnalyze() {
  if (canAnalyze.value) emit('analyze', items.value)
}
</script>

<template>
  <div class="upload-step">

    <div class="upload-zone">
      <h3><FileUp :size="ICON_SIZE.STANDARD" /> PDF soubory</h3>
      <div
        class="dropzone"
        :class="{ dragging: isDragging }"
        @click="fileInput?.click()"
        @drop.prevent="handleDrop"
        @dragover.prevent
        @dragenter.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
      >
        <FileUp :size="ICON_SIZE.HERO" class="drop-icon" />
        <p>Přetáhněte <strong>poptávku + výkresy</strong> najednou</p>
        <span class="hint">PDF &middot; Max 10 MB/ks</span>
      </div>

      <!-- File list with type badges -->
      <div v-if="items.length" class="file-list">
        <div v-for="(item, i) in items" :key="item.file.name" class="file-item">
          <button
            class="type-badge"
            :class="item.type"
            @click.stop="toggleType(i)"
            :title="'Klikni pro přepnutí na ' + (item.type === 'request' ? 'Výkres' : 'Poptávku')"
          >
            {{ item.type === 'request' ? 'Poptávka' : 'Výkres' }}
          </button>
          <FileText :size="ICON_SIZE.SMALL" class="file-icon" />
          <span class="file-name">{{ item.file.name }}</span>
          <span class="file-size">{{ formatSize(item.file.size) }}</span>
          <button class="icon-btn icon-btn-sm" @click="removeFile(i)" title="Odebrat">
            <X :size="ICON_SIZE.SMALL" />
          </button>
        </div>
      </div>

      <input ref="fileInput" type="file" accept="application/pdf" multiple class="file-input-hidden" @change="handleSelect" />
    </div>

    <!-- Validation hint -->
    <div v-if="items.length && !hasRequest" class="warn-panel">
      <Info :size="ICON_SIZE.STANDARD" />
      <span>Žádný soubor není označen jako <strong>Poptávka</strong>. Klikněte na badge pro přepnutí.</span>
    </div>

    <!-- Analyze button -->
    <button class="analyze-btn" :disabled="!canAnalyze" @click="handleAnalyze">
      <Sparkles :size="ICON_SIZE.STANDARD" />
      Analyzovat ({{ items.length }} {{ items.length === 1 ? 'soubor' : items.length < 5 ? 'soubory' : 'souborů' }})
    </button>

    <!-- Info panel -->
    <div class="info-panel">
      <Info :size="ICON_SIZE.STANDARD" class="info-icon" />
      <p>Typ souboru se pozná automaticky z názvu. <strong>Kliknutím na badge</strong> můžete typ přepnout. Poptávka = tabulkový dokument. Výkres = technický výkres s razítkem.</p>
    </div>

  </div>
</template>

<style scoped>
.upload-step { display: flex; flex-direction: column; gap: var(--space-6); max-width: 800px; margin: 0 auto; }
.upload-zone { display: flex; flex-direction: column; gap: var(--space-4); }
.upload-zone h3 { display: flex; align-items: center; gap: var(--space-2); margin: 0; font-size: var(--text-sm); font-weight: 600; color: var(--text-primary); }

.dropzone {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: var(--space-10) var(--space-8); gap: var(--space-2); text-align: center;
  border: 2px dashed var(--border-default); border-radius: var(--radius-lg);
  background: var(--bg-surface); cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.dropzone:hover { border-color: var(--brand); background: var(--state-hover); }
.dropzone.dragging { border-color: var(--brand); background: var(--brand-subtle); }
.drop-icon { color: var(--brand); flex-shrink: 0; }
.dropzone p { margin: 0; font-size: var(--text-sm); color: var(--text-body); }
.hint { font-size: var(--text-sm); color: var(--text-tertiary); }

.file-list { display: flex; flex-direction: column; gap: var(--space-1); }
.file-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised); border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}
.file-icon { color: var(--text-tertiary); flex-shrink: 0; }
.file-name { flex: 1; font-size: var(--text-sm); color: var(--text-body); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: var(--text-sm); color: var(--text-tertiary); font-family: var(--font-mono); flex-shrink: 0; }

.type-badge {
  flex-shrink: 0; padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm); font-size: var(--text-sm); font-weight: 600;
  border: 1px solid transparent; cursor: pointer; min-width: 72px; text-align: center;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.type-badge.request { background: var(--bg-raised); color: var(--palette-blue); border-color: var(--border-default); }
.type-badge.request:hover { border-color: var(--palette-blue); }
.type-badge.drawing { background: var(--bg-surface); color: var(--text-secondary); border-color: var(--border-default); }
.type-badge.drawing:hover { border-color: var(--text-tertiary); }

.warn-panel {
  display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4);
  background: var(--palette-yellow-subtle); border: 1px solid var(--palette-yellow);
  border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-body);
}

.analyze-btn {
  display: flex; align-items: center; justify-content: center;
  gap: var(--space-2); width: 100%; padding: var(--space-4) var(--space-6);
  background: transparent; border: 1px solid var(--border-default); border-radius: var(--radius-lg);
  color: var(--text-primary); font-size: var(--text-sm); font-weight: 600; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.analyze-btn:hover:not(:disabled) { background: var(--brand-subtle); border-color: var(--brand); color: var(--brand-text); }
.analyze-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.info-panel {
  display: flex; gap: var(--space-3); padding: var(--space-4);
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--text-body);
}
.info-icon { color: var(--text-tertiary); flex-shrink: 0; margin-top: 1px; }
.info-panel p { margin: 0; line-height: 1.5; }

.file-input-hidden { display: none; }
</style>
