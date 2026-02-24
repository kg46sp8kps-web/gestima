<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWorkspaceStore } from '@/stores/workspace'
import { useUiStore } from '@/stores/ui'
import { useDialog } from '@/composables/useDialog'
import * as filesApi from '@/api/files'
import type { Part, PartUpdate } from '@/types/part'
import type { ContextGroup, ModuleId } from '@/types/workspace'
import type { FileWithLinks } from '@/types/file-record'
import Input from '@/components/ui/Input.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Button from '@/components/ui/Button.vue'
import { X } from 'lucide-vue-next'

interface Props {
  part: Part
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ws = useWorkspaceStore()
const ui = useUiStore()
const dialog = useDialog()

// ─── Edit draft ───
interface Draft {
  name: string | null
  article_number: string | null
  drawing_number: string | null
  revision: string | null
  customer_revision: string | null
  unit_weight: number | null
}

function toDraft(p: Part): Draft {
  return {
    name: p.name ?? null,
    article_number: p.article_number ?? null,
    drawing_number: p.drawing_number ?? null,
    revision: p.revision ?? null,
    customer_revision: p.customer_revision ?? null,
    unit_weight: p.unit_weight ?? null,
  }
}

const draft = ref<Draft>(toDraft(props.part))
const saving = ref(false)

const isDirty = computed(() => {
  const p = props.part
  return (
    draft.value.name !== (p.name ?? null) ||
    draft.value.article_number !== (p.article_number ?? null) ||
    draft.value.drawing_number !== (p.drawing_number ?? null) ||
    draft.value.revision !== (p.revision ?? null) ||
    draft.value.customer_revision !== (p.customer_revision ?? null) ||
    draft.value.unit_weight !== (p.unit_weight ?? null)
  )
})

// Přepnutí na jiný díl → vždy reset draftu
watch(() => props.part.part_number, () => { draft.value = toDraft(props.part) })

// Aktualizace stejného dílu zvenku (po save, refresh) → reset jen pokud není dirty
watch(
  () => props.part,
  (p) => { if (!isDirty.value) draft.value = toDraft(p) },
  { deep: true },
)

async function save() {
  if (!isDirty.value || saving.value) return
  saving.value = true
  const update: PartUpdate = {
    name: draft.value.name || undefined,
    article_number: draft.value.article_number || undefined,
    drawing_number: draft.value.drawing_number || undefined,
    revision: draft.value.revision || undefined,
    customer_revision: draft.value.customer_revision || undefined,
    unit_weight: draft.value.unit_weight ?? null,
    version: props.part.version,
  }
  const updated = await parts.updatePart(props.part.part_number, update)
  saving.value = false
  if (updated) draft.value = toDraft(updated)
}

function reset() {
  draft.value = toDraft(props.part)
}

// ─── Quick links ───
const QUICK_LINKS: Array<{ label: string; module: ModuleId }> = [
  { label: 'Operace',  module: 'work-ops' },
  { label: 'Kalkulace', module: 'work-pricing' },
  { label: 'Materiály', module: 'work-materials' },
  { label: 'Výkres',   module: 'work-drawing' },
  { label: '3D Model', module: 'work-3d' },
]

function openModule(moduleId: ModuleId) {
  ws.splitLeaf(props.leafId, moduleId, 'right', props.ctx)
}

// DnD — tab spawn (leafId = null → nový panel, ctx zdrojového panelu)
let qlDragTimer: ReturnType<typeof setTimeout> | null = null

function onQlDragStart(e: DragEvent, moduleId: ModuleId) {
  if (!e.dataTransfer) return
  e.dataTransfer.setData('text/plain', moduleId)
  e.dataTransfer.effectAllowed = 'move'
  qlDragTimer = setTimeout(() => {
    qlDragTimer = null
    ws.startDrag(null, moduleId, props.ctx)
  }, 0)
}

function onQlDragEnd() {
  if (qlDragTimer !== null) {
    clearTimeout(qlDragTimer)
    qlDragTimer = null
  }
  ws.endDrag()
}

// ─── Files ───
const files = ref<FileWithLinks[]>([])
const filesLoading = ref(false)
const uploading = ref(false)
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const ALLOWED_EXTENSIONS = ['pdf', 'step', 'stp', 'nc', 'tap', 'mpf', 'cnc', 'gcode', 'dxf']

function isAllowedFile(file: File): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  return ALLOWED_EXTENSIONS.includes(ext)
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function inferLinkType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? ''
  if (['step', 'stp'].includes(ext)) return 'step_model'
  if (['nc', 'tap', 'mpf', 'cnc'].includes(ext)) return 'nc_program'
  return 'drawing'
}

function linkTypeBadge(lt: string): string {
  if (lt === 'drawing') return 'VYK'
  if (lt === 'step_model') return 'STEP'
  if (lt === 'nc_program') return 'NC'
  return lt.toUpperCase().slice(0, 4)
}

async function loadFiles() {
  filesLoading.value = true
  try {
    files.value = await filesApi.listByEntity('part', props.part.id)
  } catch {
    ui.showError('Chyba při načítání souborů')
  } finally {
    filesLoading.value = false
  }
}

async function handleUpload(file: File) {
  if (uploading.value) return
  if (!isAllowedFile(file)) {
    ui.showError(`Nepodporovaný typ souboru. Povolené: ${ALLOWED_EXTENSIONS.join(', ')}`)
    return
  }
  uploading.value = true
  try {
    const f = await filesApi.upload(file, 'part', props.part.id, inferLinkType(file.name))
    files.value.push(f)
    ui.showSuccess('Soubor nahrán')
  } catch {
    ui.showError('Chyba při nahrávání souboru')
  } finally {
    uploading.value = false
  }
}

function onFileInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file) handleUpload(file)
}

async function deleteFile(f: FileWithLinks, e: MouseEvent) {
  e.stopPropagation()
  const ok = await dialog.confirm({
    title: 'Smazat soubor?',
    message: `Soubor "${f.original_filename}" bude trvale smazán.`,
    confirmLabel: 'Smazat',
    cancelLabel: 'Zrušit',
  })
  if (!ok) return
  try {
    await filesApi.deleteFile(f.id)
    files.value = files.value.filter(x => x.id !== f.id)
  } catch {
    ui.showError('Chyba při mazání souboru')
  }
}

watch(() => props.part.id, loadFiles, { immediate: true })
</script>

<template>
  <div class="pdc">
    <!-- Info bar -->
    <div class="det-bar">
      <span class="det-pn">{{ part.part_number }}</span>
      <span class="det-nm">{{ part.name || part.article_number || '—' }}</span>
      <span class="det-uom">{{ part.uom }}</span>
    </div>

    <!-- Quick-link strip -->
    <div class="ql-strip">
      <button
        v-for="ql in QUICK_LINKS"
        :key="ql.module"
        class="ql-btn"
        :data-testid="`open-${ql.module}`"
        :title="`Otevřít ${ql.label} — klik vedle, táhnout kamkoli`"
        draggable="true"
        @click="openModule(ql.module)"
        @dragstart="onQlDragStart($event, ql.module)"
        @dragend="onQlDragEnd"
      >
        {{ ql.label }}
      </button>
    </div>

    <!-- Scrollable body -->
    <div class="form-body">

      <!-- ── Part fields ── -->
      <div class="form-section">
        <div class="field-row">
          <div class="field field-grow">
            <Input
              :modelValue="draft.name"
              @update:modelValue="draft.name = $event as string | null"
              label="Název"
              placeholder="—"
              testid="field-name"
            />
          </div>
          <div class="field">
            <Input
              :modelValue="draft.article_number"
              @update:modelValue="draft.article_number = $event as string | null"
              label="Artikl"
              placeholder="—"
              testid="field-article"
            />
          </div>
        </div>
        <div class="field-row">
          <div class="field field-grow">
            <Input
              :modelValue="draft.drawing_number"
              @update:modelValue="draft.drawing_number = $event as string | null"
              label="Výkres č."
              placeholder="—"
              testid="field-drawing-number"
            />
          </div>
          <div class="field field-sm">
            <Input
              :modelValue="draft.revision"
              @update:modelValue="draft.revision = $event as string | null"
              label="Rev."
              placeholder="—"
              testid="field-revision"
            />
          </div>
          <div class="field field-sm">
            <Input
              :modelValue="draft.customer_revision"
              @update:modelValue="draft.customer_revision = $event as string | null"
              label="Rev. zák."
              placeholder="—"
              testid="field-customer-revision"
            />
          </div>
        </div>
        <div class="field-row">
          <div class="field field-sm">
            <Input
              :modelValue="draft.unit_weight !== null ? String(draft.unit_weight) : ''"
              @update:modelValue="draft.unit_weight = $event ? Number($event) || null : null"
              label="Hmotnost (kg/ks)"
              placeholder="—"
              type="number"
              testid="field-unit-weight"
            />
          </div>
        </div>
      </div>

      <!-- Save bar — only when dirty -->
      <div v-if="isDirty" class="save-bar">
        <Button
          variant="ghost"
          data-testid="reset-btn"
          @click="reset"
        >Zahodit</Button>
        <Button
          variant="primary"
          :disabled="saving"
          data-testid="save-btn"
          @click="save"
        >{{ saving ? 'Ukládání…' : 'Uložit' }}</Button>
      </div>

      <!-- ── Files section ── -->
      <div class="sec-hdr">Soubory</div>

      <div v-if="filesLoading" class="files-loading">
        <Spinner size="sm" />
      </div>
      <template v-else>
        <!-- File list -->
        <div v-if="files.length" class="file-list">
          <div
            v-for="f in files"
            :key="f.id"
            class="file-row"
            :data-testid="`file-row-${f.id}`"
          >
            <span class="badge">{{ linkTypeBadge(f.links.find(l => l.entity_type === 'part')?.link_type ?? 'drawing') }}</span>
            <span class="fname">{{ f.original_filename }}</span>
            <span class="fsize">{{ formatBytes(f.file_size) }}</span>
            <a
              :href="`/api/files/${f.id}/download`"
              class="fdl"
              target="_blank"
              :data-testid="`dl-file-${f.id}`"
              title="Stáhnout"
            >↓</a>
            <button
              class="icon-btn icon-btn-danger fdel"
              :data-testid="`del-file-${f.id}`"
              title="Smazat soubor"
              @click="deleteFile(f, $event)"
            ><X :size="12" /></button>
          </div>
        </div>

        <!-- Drop zone -->
        <div
          :class="['drop-zone', { 'dz-over': isDragOver, 'dz-busy': uploading }]"
          data-testid="file-drop-zone"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop="onDrop"
          @click="fileInput?.click()"
        >
          <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
          <input ref="fileInput" type="file" class="file-inp" accept=".pdf,.step,.stp,.nc,.tap,.mpf,.cnc,.gcode,.dxf" @change="onFileInput" /> <!-- intentional: programmatic trigger -->
          <span class="dz-text">{{ uploading ? 'Nahrávání…' : 'Přetáhněte soubor nebo klikněte' }}</span>
          <span class="dz-hint">PDF · DXF · STEP / STP · NC · TAP · MPF</span>
        </div>
      </template>

    </div>
  </div>
</template>

<style scoped>
.pdc {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Info bar ─── */
.det-bar {
  height: 30px;
  padding: 0 var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  overflow: hidden;
}
.det-pn { font-size: var(--fs); font-weight: 600; color: var(--t1); flex-shrink: 0; letter-spacing: 0.02em; }
.det-nm { font-size: var(--fs); color: var(--t3); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.det-uom { font-size: var(--fsm); font-weight: 600; color: var(--t4); flex-shrink: 0; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Quick-link strip ─── */
.ql-strip {
  display: flex;
  gap: 1px;
  padding: 4px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  background: rgba(255,255,255,0.01);
}
.ql-btn {
  padding: 3px 9px;
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  font-family: var(--font);
  transition: color 100ms var(--ease), background 100ms var(--ease);
}
.ql-btn:hover { color: var(--t1); background: var(--b1); }
.ql-btn[draggable="true"] { cursor: grab; }
.ql-btn[draggable="true"]:active { cursor: grabbing; }

/* ─── Scrollable body ─── */
.form-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* ─── Form section ─── */
.form-section {
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.field-grow { flex: 1; }
.field-sm { width: 80px; flex-shrink: 0; }

/* ─── Save bar ─── */
.save-bar {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
  background: rgba(255,255,255,0.015);
  flex-shrink: 0;
  animation: savebar-in 150ms var(--ease);
}
@keyframes savebar-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ─── Section header ─── */
.sec-hdr {
  padding: 5px var(--pad);
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

/* ─── Files loading ─── */
.files-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* ─── File list ─── */
.file-list {
  border-bottom: 1px solid var(--b1);
}
.file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.file-row:hover { background: var(--b1); }
/* File type badge uses global .badge from design-system.css */
.fname {
  flex: 1;
  font-size: var(--fs);
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.fsize { font-size: var(--fsm); color: var(--t4); flex-shrink: 0; }
.fdl {
  font-size: var(--fsm);
  color: var(--t4);
  text-decoration: none;
  padding: 2px 5px;
  border-radius: var(--rs);
  flex-shrink: 0;
  transition: color 100ms var(--ease);
}
.fdl:hover { color: var(--t1); }
.fdel {
  width: 20px;
  height: 20px;
  opacity: 0;
  flex-shrink: 0;
}
.file-row:hover .fdel { opacity: 1; }

/* ─── Drop zone ─── */
.drop-zone {
  margin: 8px var(--pad);
  border: 1px dashed var(--b2);
  border-radius: var(--rs);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: border-color 100ms var(--ease), background 100ms var(--ease);
  position: relative;
}
.drop-zone:hover { border-color: var(--b3); background: rgba(255,255,255,0.02); }
.drop-zone.dz-over { border-color: var(--b3); background: rgba(255,255,255,0.04); }
.drop-zone.dz-busy { opacity: 0.5; cursor: default; pointer-events: none; }
.dz-text { font-size: var(--fsm); color: var(--t3); }
.dz-hint { font-size: var(--fsm); color: var(--t4); }
.file-inp { position: absolute; inset: 0; opacity: 0; width: 100%; height: 100%; cursor: pointer; pointer-events: none; }
</style>
