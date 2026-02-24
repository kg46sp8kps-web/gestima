<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as filesApi from '@/api/files'
import { apiClient } from '@/api/client'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'
import InlineSelect from '@/components/ui/InlineSelect.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const typeGuard = useItemTypeGuard(['part'])

const OCCT_EXTS = new Set(['step', 'stp', 'iges', 'igs', 'brep', 'brp'])
const VIEW_EXTS = new Set([...OCCT_EXTS, 'stl', 'obj', '3mf'])

const files = ref<FileWithLinks[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const loadingModel = ref(false)
const containerEl = ref<HTMLElement | null>(null)

let ovViewer: { Destroy(): void; Resize(): void } | null = null
let _resizeObserver: ResizeObserver | null = null
let _resizeTimer: ReturnType<typeof setTimeout> | null = null

const part = computed(() => parts.getFocusedPart(props.ctx))

function fileExt(f: FileWithLinks): string {
  return f.original_filename.split('.').pop()?.toLowerCase() ?? ''
}

function is3DFile(f: FileWithLinks): boolean {
  return VIEW_EXTS.has(fileExt(f))
}

function destroyViewer() {
  if (ovViewer) {
    ovViewer.Destroy()
    ovViewer = null
  }
}

function onResize() {
  if (ovViewer) ovViewer.Resize()
}

function scheduleResize(delay = 150) {
  if (_resizeTimer) clearTimeout(_resizeTimer)
  _resizeTimer = setTimeout(onResize, delay)
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

// ─── B-Rep edge extraction ────────────────────────────────────────────────

function extractBRepEdges(
  positions: number[],
  indices: number[],
  brepFaces: Array<{ first: number; last: number; color: [number, number, number] | null }>,
  THREE: typeof import('three'),
): import('three').BufferGeometry {
  const verts: number[] = []

  for (const face of brepFaces) {
    const boundary = new Map<string, [number, number]>()

    for (let t = face.first; t <= face.last; t++) {
      const i0 = indices[t * 3]!
      const i1 = indices[t * 3 + 1]!
      const i2 = indices[t * 3 + 2]!
      for (const [a, b] of [
        [Math.min(i0, i1), Math.max(i0, i1)],
        [Math.min(i1, i2), Math.max(i1, i2)],
        [Math.min(i2, i0), Math.max(i2, i0)],
      ] as [number, number][]) {
        const k = `${a}_${b}`
        if (boundary.has(k)) boundary.delete(k)
        else boundary.set(k, [a, b])
      }
    }

    for (const [a, b] of boundary.values()) {
      verts.push(
        positions[a * 3]!, positions[a * 3 + 1]!, positions[a * 3 + 2]!,
        positions[b * 3]!, positions[b * 3 + 1]!, positions[b * 3 + 2]!,
      )
    }
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
  return geom
}

// ─── Model loader ─────────────────────────────────────────────────────────
// OV řídí veškerý rendering (osvětlení, materiály, kamera, resize).
// Pro OCCT formáty: po načtení přidáme B-Rep hrany do OV Three.js scény.

async function loadModel(file: FileWithLinks) {
  await nextTick()
  if (!containerEl.value) return
  destroyViewer()
  loadingModel.value = true

  try {
    const isOcct = OCCT_EXTS.has(fileExt(file))

    const [OV, resp] = await Promise.all([
      import('online-3d-viewer'),
      apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
    ])

    const blob = resp.data as Blob
    const ovFile = new File([blob], file.original_filename)

    // Pro OCCT soubory: připravíme data pro B-Rep extrakci
    let uint8: Uint8Array | null = null
    if (isOcct) {
      uint8 = new Uint8Array(await blob.arrayBuffer())
    }

    const viewer = new OV.EmbeddedViewer(containerEl.value, {
      backgroundColor: new OV.RGBAColor(20, 22, 28, 255),
      defaultColor: new OV.RGBColor(210, 218, 228),
      // OV hrany zapnuty → OV nastaví polygonOffset na mesh materiálech → bez z-fighting
      edgeSettings: new OV.EdgeSettings(true, new OV.RGBColor(20, 25, 38), 35),
      onModelLoaded: isOcct ? async () => {
        // B-Rep hranová extrakce a injekce do OV scény
        try {
          const [THREE, occtMod] = await Promise.all([
            import('three'),
            import('occt-import-js'),
          ])
          const occt = await occtMod.default({ locateFile: () => '/occt/occt-import-js.wasm' })

          const tessParams = {
            linearDeflectionType: 'bounding_box_ratio',
            linearDeflection: 0.002,
            angularDeflection: 0.08,
          }
          const ext = fileExt(file)
          const result = ext === 'iges' || ext === 'igs'
            ? occt.ReadIgesFile(uint8!, tessParams)
            : ext === 'brep' || ext === 'brp'
              ? occt.ReadBrepFile(uint8!, tessParams)
              : occt.ReadStepFile(uint8!, tessParams)

          if (!result.success || result.meshes.length === 0) return

          const ovScene = viewer.GetViewer().scene

          // Schovat OV angle-threshold hrany, nahradit B-Rep hranami
          ovScene.traverse((obj: { type: string; visible: boolean }) => {
            if (obj.type === 'LineSegments') obj.visible = false
          })

          const edgeMat = new THREE.LineBasicMaterial({ color: 0x202028 })
          for (const mesh of result.meshes) {
            const edgeGeom = extractBRepEdges(
              mesh.attributes.position.array,
              mesh.index.array,
              mesh.brep_faces,
              THREE,
            )
            if (edgeGeom.getAttribute('position').count > 0) {
              ovScene.add(new THREE.LineSegments(edgeGeom, edgeMat))
            }
          }

          viewer.GetViewer().Render()
        } catch {
          // prázdný stav
        }
      } : undefined,
    })

    viewer.GetViewer().SetNavigationMode(OV.NavigationMode.FreeOrbit)
    viewer.LoadModelFromFileList([ovFile])
    ovViewer = viewer
    scheduleResize(300)
  } catch {
    // prázdný stav
  } finally {
    loadingModel.value = false
  }
}

watch(selectedId, async (id) => {
  if (!id) return
  const file = files.value.find(f => f.id === id)
  if (file) loadModel(file)
})

watch(part, (p) => {
  files.value = []
  selectedId.value = null
  destroyViewer()
  if (p) loadFiles(p.id)
}, { immediate: true })

watch(containerEl, (el) => {
  _resizeObserver?.disconnect()
  if (!el) return
  _resizeObserver = new ResizeObserver(() => scheduleResize(150))
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
    <div v-if="!typeGuard.isSupported(ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ typeGuard.focusedTypeName(ctx) }} nepodporuje 3D</span>
    </div>

    <div v-else-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádný díl</span>
    </div>

    <div v-else-if="files.length === 0" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádné 3D soubory</span>
    </div>

    <template v-else>
      <div v-if="files.length > 1" class="file-bar">
        <InlineSelect
          :modelValue="selectedId !== null ? String(selectedId) : ''"
          @update:modelValue="selectedId = $event ? Number($event) : null"
          class="file-sel"
          data-testid="3d-file-select"
        >
          <option v-for="f in files" :key="f.id" :value="String(f.id)">
            {{ f.original_filename }}
          </option>
        </InlineSelect>
      </div>

      <div class="viewer-area">
        <div v-if="loadingModel" class="model-loading" data-testid="3d-loading">
          <Spinner size="sm" />
        </div>
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
  overflow: hidden;
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
  font-size: var(--fsm);
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

/* visual styles come from InlineSelect component */
.file-sel { flex: 1; height: 28px; }

.viewer-area {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.model-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(14, 16, 24, 0.8);
  z-index: 2;
}

.ov-container {
  position: absolute;
  inset: 0;
}

.ov-container :deep(canvas) {
  display: block;
}
</style>
