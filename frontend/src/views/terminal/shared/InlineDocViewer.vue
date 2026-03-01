<script setup lang="ts">
/**
 * Inline document viewer for operator terminal.
 * Shows PDF (via iframe) or 3D model for a given item number.
 * Resolves item → Part → files automatically.
 */
import { ref, watch, onUnmounted } from 'vue'
import { apiClient } from '@/api/client'
import * as filesApi from '@/api/files'
import type { FileWithLinks } from '@/types/file-record'

const props = defineProps<{
  item: string
  visible: boolean
}>()

const emit = defineEmits<{ close: [] }>()

const loading = ref(false)
const error = ref('')
const files = ref<FileWithLinks[]>([])
const selectedFile = ref<FileWithLinks | null>(null)
const viewMode = ref<'pdf' | '3d' | null>(null)

type PartSearchRow = { id: number }
type DestroyableViewer = { Destroy?: () => void }

// 3D viewer
const containerEl = ref<HTMLElement | null>(null)
let ovViewer: DestroyableViewer | null = null

const OCCT_EXTS = new Set(['step', 'stp', 'iges', 'igs', 'brep', 'brp', 'stl', 'obj', '3mf'])

function fileExt(f: FileWithLinks): string {
  return (f.original_filename ?? '').split('.').pop()?.toLowerCase() ?? ''
}

function fileKind(f: FileWithLinks): 'pdf' | '3d' | 'other' {
  if (f.mime_type === 'application/pdf') return 'pdf'
  if (OCCT_EXTS.has(fileExt(f))) return '3d'
  return 'other'
}

watch(() => [props.item, props.visible] as const, async ([item, visible]) => {
  if (!visible || !item) return
  await loadFiles(item)
}, { immediate: true })

async function loadFiles(item: string) {
  loading.value = true
  error.value = ''
  files.value = []
  selectedFile.value = null
  viewMode.value = null
  destroyViewer()

  try {
    // 1. Resolve item → Part
    const { data } = await apiClient.get<{ parts: PartSearchRow[] }>('/parts', {
      params: { search: item, limit: 1 },
    })
    if (!data.parts?.length) {
      error.value = 'Díl nenalezen'
      return
    }
    const partId = data.parts[0]!.id

    // 2. Load files for part
    const loaded = await filesApi.listByEntity('part', partId)
    files.value = loaded.filter(f => fileKind(f) !== 'other')

    if (files.value.length === 0) {
      error.value = 'Žádné dokumenty'
      return
    }

    // Auto-select first PDF, or first file
    const firstPdf = files.value.find(f => fileKind(f) === 'pdf')
    selectFile(firstPdf ?? files.value[0]!)
  } catch {
    error.value = 'Nepodařilo se načíst dokumenty'
  } finally {
    loading.value = false
  }
}

function selectFile(f: FileWithLinks) {
  destroyViewer()
  selectedFile.value = f
  const kind = fileKind(f)
  viewMode.value = kind === 'pdf' || kind === '3d' ? kind : null

  if (kind === '3d') {
    // Load 3D after DOM update
    setTimeout(() => load3D(f), 50)
  }
}

async function load3D(file: FileWithLinks) {
  if (!containerEl.value) return

  try {
    const [OV, resp] = await Promise.all([
      import('online-3d-viewer'),
      apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
    ])

    const blob = resp.data as Blob
    const ovFile = new File([blob], file.original_filename)

    const viewer = new OV.EmbeddedViewer(containerEl.value, {
      backgroundColor: new OV.RGBAColor(20, 22, 28, 255),
      defaultColor: new OV.RGBColor(210, 218, 228),
    })
    viewer.GetViewer().SetNavigationMode(OV.NavigationMode.FreeOrbit)
    viewer.LoadModelFromFileList([ovFile])
    ovViewer = viewer
  } catch {
    error.value = 'Nepodařilo se načíst 3D model'
  }
}

function destroyViewer() {
  if (ovViewer) {
    try { ovViewer.Destroy?.() } catch { /* ignore */ }
    ovViewer = null
  }
  if (containerEl.value) {
    containerEl.value.innerHTML = ''
  }
}

onUnmounted(destroyViewer)
</script>

<template>
  <div v-if="visible" class="idv-overlay" @click.self="emit('close')">
    <div class="idv-panel">
      <!-- Header -->
      <div class="idv-header">
        <div class="idv-title">{{ item }}</div>
        <!-- File tabs -->
        <div v-if="files.length > 1" class="idv-tabs">
          <button
            v-for="f in files"
            :key="f.id"
            :class="['idv-tab', { active: selectedFile?.id === f.id }]"
            @click="selectFile(f)"
          >
            {{ fileKind(f) === 'pdf' ? 'PDF' : '3D' }}
          </button>
        </div>
        <button class="idv-close" @click="emit('close')">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="idv-content">
        <div v-if="loading" class="idv-msg">Načítám...</div>
        <div v-else-if="error" class="idv-msg idv-err">{{ error }}</div>

        <!-- PDF iframe -->
        <iframe
          v-else-if="viewMode === 'pdf' && selectedFile"
          :src="`/api/files/${selectedFile.id}/preview`"
          class="idv-pdf"
        />

        <!-- 3D viewer -->
        <div
          v-else-if="viewMode === '3d'"
          ref="containerEl"
          class="idv-3d"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.idv-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 16px;
}

.idv-panel {
  width: 100%;
  max-width: 900px;
  background: var(--ground, #181a1f);
  border: 1px solid var(--b2);
  border-radius: var(--rs, 8px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.idv-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

.idv-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--t1);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.idv-tabs {
  display: flex;
  gap: 4px;
}
.idv-tab {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  font-family: var(--font);
  color: var(--t3);
  background: none;
  border: 1px solid var(--b2);
  border-radius: 4px;
  cursor: pointer;
}
.idv-tab.active {
  color: var(--t1);
  border-color: var(--red, #e53935);
  background: rgba(229, 57, 53, 0.1);
}

.idv-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--t3);
  cursor: pointer;
  border-radius: 4px;
  flex-shrink: 0;
}
.idv-close:active {
  background: rgba(255, 255, 255, 0.06);
}

.idv-content {
  flex: 1;
  min-height: 0;
  display: flex;
}

.idv-msg {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--t4);
  font-size: 14px;
}
.idv-err { color: var(--red, #e53935); }

.idv-pdf {
  flex: 1;
  border: none;
  background: rgba(255, 255, 255, 0.95);
}

.idv-3d {
  flex: 1;
  min-height: 300px;
}
</style>
