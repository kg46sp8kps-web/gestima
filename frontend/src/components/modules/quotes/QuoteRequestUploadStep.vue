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
.upload-step { display: flex; flex-direction: column; gap: 20px; max-width: 800px; margin: 0 auto; }
.upload-zone { display: flex; flex-direction: column; gap: 12px; }
.upload-zone h3 { display: flex; align-items: center; gap: 6px; margin: 0; font-size: var(--fs); font-weight: 600; color: var(--t1); }

.dropzone {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px 24px; gap: 6px; text-align: center;
  border: 2px dashed var(--b2); border-radius: 8px;
  background: var(--surface); cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.dropzone:hover { border-color: var(--red); background: var(--b1); }
.dropzone.dragging { border-color: var(--red); background: var(--red-10); }
.drop-icon { color: var(--red); flex-shrink: 0; }
.dropzone p { margin: 0; font-size: var(--fs); color: var(--t2); }
.hint { font-size: var(--fs); color: var(--t3); }

.file-list { display: flex; flex-direction: column; gap: 4px; }
.file-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px var(--pad);
  background: var(--raised); border-radius: var(--r);
  border: 1px solid var(--b2);
}
.file-icon { color: var(--t3); flex-shrink: 0; }
.file-name { flex: 1; font-size: var(--fs); color: var(--t2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: var(--fs); color: var(--t3); font-family: var(--mono); flex-shrink: 0; }

.type-badge {
  flex-shrink: 0; padding: 4px 6px;
  border-radius: var(--rs); font-size: var(--fs); font-weight: 600;
  border: 1px solid transparent; cursor: pointer; min-width: 72px; text-align: center;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.type-badge.request { background: var(--raised); color: var(--t3); border-color: var(--b2); }
.type-badge.request:hover { border-color: var(--t3); }
.type-badge.drawing { background: var(--surface); color: var(--t3); border-color: var(--b2); }
.type-badge.drawing:hover { border-color: var(--t3); }

.warn-panel {
  display: flex; align-items: center; gap: 6px; padding: var(--pad) 12px;
  background: rgba(251,191,36,0.1); border: 1px solid var(--warn);
  border-radius: var(--r); font-size: var(--fs); color: var(--t2);
}

.analyze-btn {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; width: 100%; padding: 12px 20px;
  background: transparent; border: 1px solid var(--b2); border-radius: 8px;
  color: var(--t1); font-size: var(--fs); font-weight: 600; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.analyze-btn:hover:not(:disabled) { background: var(--red-10); border-color: var(--red); color: rgba(229, 57, 53, 0.7); }
.analyze-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.info-panel {
  display: flex; gap: var(--pad); padding: 12px;
  background: var(--surface); border: 1px solid var(--b2);
  border-radius: var(--r); font-size: var(--fs); color: var(--t2);
}
.info-icon { color: var(--t3); flex-shrink: 0; margin-top: 1px; }
.info-panel p { margin: 0; line-height: 1.5; }

.file-input-hidden { display: none; }
</style>
