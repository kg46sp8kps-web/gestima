<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as filesApi from '@/api/files'
import { apiClient } from '@/api/client'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import type { EmbeddedViewer } from 'online-3d-viewer'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const typeGuard = useItemTypeGuard(['part'])

const VIEW_EXTS = new Set(['step', 'stp', 'iges', 'igs', 'stl', 'obj', '3mf', 'brep', 'brp'])

const files = ref<FileWithLinks[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const loadingModel = ref(false)
const containerEl = ref<HTMLElement | null>(null)

let viewer: EmbeddedViewer | null = null
let _resizeObserver: ResizeObserver | null = null
let _resizeTimer: ReturnType<typeof setTimeout> | null = null

const part = computed(() => parts.getFocusedPart(props.ctx))

function is3DFile(f: FileWithLinks): boolean {
  const ext = f.original_filename.split('.').pop()?.toLowerCase() ?? ''
  return VIEW_EXTS.has(ext)
}

function destroyViewer() {
  if (viewer) {
    viewer.Destroy()
    viewer = null
  }
}

async function loadFiles(partId: number) {
  loading.value = true
  files.value = []
  try {
    const all = await filesApi.listByEntity('part', partId)
    files.value = all.filter(is3DFile)
    selectedId.value = files.value[0]?.id ?? null
  } catch {
    // prázdný stav
  } finally {
    loading.value = false
  }
}

async function loadModel(file: FileWithLinks) {
  if (!containerEl.value) return
  destroyViewer()
  loadingModel.value = true
  try {
    const [OV, resp] = await Promise.all([
      import('online-3d-viewer'),
      apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
    ])
    const f = new File([resp.data as BlobPart], file.original_filename)
    viewer = new OV.EmbeddedViewer(containerEl.value, {
      backgroundColor: new OV.RGBAColor(18, 18, 20, 255),
      defaultColor: new OV.RGBColor(180, 180, 185),
      edgeSettings: new OV.EdgeSettings(false, new OV.RGBColor(0, 0, 0), 1),
    })
    viewer.LoadModelFromFileList([f])
  } catch {
    // prázdný stav — viewer se nezobrazí
  } finally {
    loadingModel.value = false
  }
}

// Sledujeme oba najednou — načtení modelu až je kontejner i soubor připravený
watch([selectedId, containerEl] as const, async ([id, el]) => {
  if (!id || !el) return
  const file = files.value.find(f => f.id === id)
  if (file) loadModel(file)
})

// Sledujeme výběr souboru — zajistíme nextTick pro DOM
watch(selectedId, async (id) => {
  if (!id) return
  await nextTick()
  const file = files.value.find(f => f.id === id)
  if (file && containerEl.value) loadModel(file)
})

watch(part, (p) => {
  files.value = []
  selectedId.value = null
  destroyViewer()
  if (p) loadFiles(p.id)
}, { immediate: true })

// ResizeObserver — volá Resize() při změně velikosti panelu
watch(containerEl, (el) => {
  _resizeObserver?.disconnect()
  if (!el) return
  _resizeObserver = new ResizeObserver(() => {
    if (_resizeTimer) clearTimeout(_resizeTimer)
    _resizeTimer = setTimeout(() => { viewer?.Resize() }, 100)
  })
  _resizeObserver.observe(el)
})

onBeforeUnmount(() => {
  destroyViewer()
  _resizeObserver?.disconnect()
  if (_resizeTimer) clearTimeout(_resizeTimer)
})
</script>

<template>
  <div class="w3d">
    <!-- Typ není díl -->
    <div v-if="!typeGuard.isSupported(ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ typeGuard.focusedTypeName(ctx) }} nepodporuje 3D</span>
    </div>

    <!-- Načítám seznam souborů -->
    <div v-else-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Žádný díl -->
    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádný díl</span>
    </div>

    <!-- Žádné 3D soubory -->
    <div v-else-if="files.length === 0" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádné 3D soubory</span>
    </div>

    <!-- Viewer -->
    <template v-else>
      <!-- File picker — jen při více souborech -->
      <div v-if="files.length > 1" class="file-bar">
        <select
          v-model="selectedId"
          class="file-sel"
          data-testid="3d-file-select"
        >
          <option v-for="f in files" :key="f.id" :value="f.id">
            {{ f.original_filename }}
          </option>
        </select>
      </div>

      <!-- Plocha vieweru -->
      <div class="viewer-area">
        <!-- Overlay při načítání modelu -->
        <div v-if="loadingModel" class="model-loading" data-testid="3d-loading">
          <Spinner size="sm" />
        </div>
        <!-- online-3d-viewer se vykreslí sem -->
        <div ref="containerEl" class="ov-container" data-testid="3d-viewer-container" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.w3d {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}

.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}

.mod-label {
  font-size: var(--fsl);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.file-bar {
  display: flex;
  align-items: center;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

.file-sel {
  flex: 1;
  height: 28px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  padding: 3px 6px;
  outline: none;
  cursor: pointer;
  transition: border-color 120ms var(--ease);
}

.file-sel:focus {
  border-color: var(--b3);
}

.viewer-area {
  flex: 1;
  min-height: 0;
  position: relative;
}

.model-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(18, 18, 20, 0.75);
  z-index: 2;
}

.ov-container {
  width: 100%;
  height: 100%;
}

/* online-3d-viewer injektuje vlastní canvas do kontejneru */
.ov-container :deep(canvas) {
  display: block;
}
</style>
