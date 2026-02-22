<script setup lang="ts">
/**
 * Drawing Import Panel
 *
 * 2-step import workflow:
 * 1. Scan share → preview matches
 * 2. User confirms → execute import
 */

import { ref, computed } from 'vue'
import { ICON_SIZE } from '@/config/design'
import {
  Search,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FolderOpen,
  FileText,
  Box,
  Loader2,
} from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'
import {
  getDrawingShareStatus,
  previewDrawingImport,
  executeDrawingImport,
} from '@/api/drawing-import'
import type {
  ShareStatusResponse,
  ShareFolderPreview,
  DrawingImportPreviewResponse,
  DrawingImportExecuteResponse,
  ImportFolderRequest,
} from '@/types/drawing-import'

const uiStore = useUiStore()

// State
const status = ref<ShareStatusResponse | null>(null)
const preview = ref<DrawingImportPreviewResponse | null>(null)
const result = ref<DrawingImportExecuteResponse | null>(null)
const scanning = ref(false)
const importing = ref(false)
const checkingStatus = ref(false)

// Filters
const statusFilter = ref<string>('ready')
const searchQuery = ref('')

// Selection
const selectedFolders = ref<Set<string>>(new Set())

// Computed
const filteredFolders = computed<ShareFolderPreview[]>(() => {
  if (!preview.value) return []
  let folders = preview.value.folders

  if (statusFilter.value !== 'all') {
    folders = folders.filter(f => f.status === statusFilter.value)
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    folders = folders.filter(f =>
      f.folder_name.toLowerCase().includes(q) ||
      (f.matched_part_number && f.matched_part_number.includes(q))
    )
  }

  return folders
})

const readyFolders = computed(() =>
  preview.value?.folders.filter(f => f.status === 'ready') ?? []
)

const selectedCount = computed(() => selectedFolders.value.size)

const allReadySelected = computed(() =>
  readyFolders.value.length > 0 &&
  readyFolders.value.every(f => selectedFolders.value.has(f.folder_name))
)

// Actions
async function checkStatus() {
  checkingStatus.value = true
  try {
    status.value = await getDrawingShareStatus()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Chyba'
    uiStore.showError(msg)
  } finally {
    checkingStatus.value = false
  }
}

async function scanShare() {
  scanning.value = true
  result.value = null
  selectedFolders.value.clear()
  try {
    preview.value = await previewDrawingImport()
    // Auto-select all ready folders
    for (const f of readyFolders.value) {
      selectedFolders.value.add(f.folder_name)
    }
    uiStore.showSuccess(`Sken dokoncen: ${preview.value.ready} pripraveno k importu`)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Sken selhal'
    uiStore.showError(msg)
  } finally {
    scanning.value = false
  }
}

function toggleSelectAll() {
  if (allReadySelected.value) {
    selectedFolders.value.clear()
  } else {
    for (const f of readyFolders.value) {
      selectedFolders.value.add(f.folder_name)
    }
  }
}

function toggleFolder(folderName: string) {
  if (selectedFolders.value.has(folderName)) {
    selectedFolders.value.delete(folderName)
  } else {
    selectedFolders.value.add(folderName)
  }
}

async function executeImport() {
  if (!preview.value || selectedCount.value === 0) return

  importing.value = true
  result.value = null

  const folders: ImportFolderRequest[] = preview.value.folders
    .filter(f => f.status === 'ready' && selectedFolders.value.has(f.folder_name) && f.matched_part_id && f.primary_pdf)
    .map(f => ({
      folder_name: f.folder_name,
      part_id: f.matched_part_id!,
      primary_pdf: f.primary_pdf!,
      import_step: true,
    }))

  try {
    result.value = await executeDrawingImport({ folders })
    if (result.value.success) {
      uiStore.showSuccess(
        `Import dokoncen: ${result.value.files_created} souboru, ${result.value.parts_updated} dilu`
      )
    } else {
      uiStore.showError(`Import s chybami: ${result.value.errors.length} chyb`)
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Import selhal'
    uiStore.showError(msg)
  } finally {
    importing.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

// Initial status check
checkStatus()
</script>

<template>
  <div class="drawing-import-panel">
    <!-- HEADER -->
    <div class="panel-header">
      <h3>Import vykresu ze share</h3>
      <div class="header-actions">
        <button
          class="btn-primary"
          :disabled="scanning || checkingStatus"
          @click="scanShare"
        >
          <Loader2 v-if="scanning" :size="ICON_SIZE.SMALL" class="spin" />
          <Search v-else :size="ICON_SIZE.SMALL" />
          <span>{{ scanning ? 'Skenuji...' : 'Skenovat' }}</span>
        </button>
      </div>
    </div>

    <!-- STATUS BAR -->
    <div class="status-bar" v-if="status">
      <div class="status-item">
        <span class="status-label">Share:</span>
        <span class="status-value mono">{{ status.share_path }}</span>
      </div>
      <div class="status-item">
        <span
          :class="['badge-dot', status.is_accessible ? 'badge-dot-ok' : 'badge-dot-error']"
        ></span>
        <span>{{ status.is_accessible ? 'Pripojeno' : 'Nedostupny' }}</span>
      </div>
      <div class="status-item" v-if="status.is_accessible">
        <FolderOpen :size="ICON_SIZE.SMALL" />
        <span>{{ status.total_folders }} slozek</span>
      </div>
    </div>

    <!-- STATS + FILTERS (only after scan) -->
    <template v-if="preview">
      <div class="stats-bar">
        <button
          :class="['stat-chip', { active: statusFilter === 'all' }]"
          @click="statusFilter = 'all'"
        >
          Vse {{ preview.total_folders }}
        </button>
        <button
          :class="['stat-chip', 'stat-ready', { active: statusFilter === 'ready' }]"
          @click="statusFilter = 'ready'"
        >
          <CheckCircle :size="ICON_SIZE.SMALL" />
          Pripraveno {{ preview.ready }}
        </button>
        <button
          :class="['stat-chip', 'stat-imported', { active: statusFilter === 'already_imported' }]"
          @click="statusFilter = 'already_imported'"
        >
          Importovano {{ preview.already_imported }}
        </button>
        <button
          :class="['stat-chip', 'stat-nomatch', { active: statusFilter === 'no_match' }]"
          @click="statusFilter = 'no_match'"
        >
          <XCircle :size="ICON_SIZE.SMALL" />
          Bez shody {{ preview.unmatched }}
        </button>
        <button
          :class="['stat-chip', { active: statusFilter === 'no_pdf' }]"
          @click="statusFilter = 'no_pdf'"
        >
          Bez PDF {{ preview.no_pdf }}
        </button>
        <span class="stat-skip" v-if="preview.skipped > 0">
          ({{ preview.skipped }} preskoceno)
        </span>
      </div>

      <!-- SEARCH -->
      <div class="search-row">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Hledat ve slozce nebo cisle dilu..."
          class="search-input"
        />
      </div>

      <!-- TABLE -->
      <div class="folder-list">
        <!-- Header -->
        <div class="folder-row folder-header">
          <div class="col-check">
            <input
              type="checkbox"
              :checked="allReadySelected"
              :indeterminate="selectedCount > 0 && !allReadySelected"
              @change="toggleSelectAll"
              :disabled="readyFolders.length === 0"
            />
          </div>
          <div class="col-folder">Slozka</div>
          <div class="col-part">Dil</div>
          <div class="col-files">PDF</div>
          <div class="col-files">STEP</div>
          <div class="col-primary">Primarni PDF</div>
          <div class="col-status">Stav</div>
        </div>

        <!-- Rows -->
        <div
          v-for="folder in filteredFolders"
          :key="folder.folder_name"
          :class="['folder-row', { selected: selectedFolders.has(folder.folder_name) }]"
          @click="folder.status === 'ready' && toggleFolder(folder.folder_name)"
        >
          <div class="col-check">
            <input
              v-if="folder.status === 'ready'"
              type="checkbox"
              :checked="selectedFolders.has(folder.folder_name)"
              @click.stop="toggleFolder(folder.folder_name)"
            />
          </div>
          <div class="col-folder mono">{{ folder.folder_name }}</div>
          <div class="col-part mono">{{ folder.matched_part_number ?? '-' }}</div>
          <div class="col-files">
            <FileText :size="ICON_SIZE.SMALL" v-if="folder.pdf_files.length" />
            {{ folder.pdf_files.length }}
          </div>
          <div class="col-files">
            <Box :size="ICON_SIZE.SMALL" v-if="folder.step_files.length" />
            {{ folder.step_files.length }}
          </div>
          <div class="col-primary mono" :title="folder.primary_pdf ?? ''">
            {{ folder.primary_pdf ? folder.primary_pdf.substring(0, 30) : '-' }}
          </div>
          <div class="col-status">
            <span v-if="folder.status === 'ready'" class="badge-dot badge-dot-ok"></span>
            <span v-else-if="folder.status === 'already_imported'" class="badge-dot badge-dot-warn"></span>
            <span v-else-if="folder.status === 'no_match'" class="badge-dot badge-dot-error"></span>
            <span v-else class="badge-dot"></span>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="filteredFolders.length === 0" class="empty-state">
          Zadne slozky pro tento filtr
        </div>
      </div>

      <!-- ACTION BAR -->
      <div class="action-bar">
        <span class="selection-info">
          Vybrano: {{ selectedCount }} z {{ readyFolders.length }} pripravenych
        </span>
        <button
          class="btn-primary"
          :disabled="selectedCount === 0 || importing"
          @click="executeImport"
        >
          <Loader2 v-if="importing" :size="ICON_SIZE.SMALL" class="spin" />
          <Download v-else :size="ICON_SIZE.SMALL" />
          <span>{{ importing ? 'Importuji...' : `Importovat (${selectedCount})` }}</span>
        </button>
      </div>
    </template>

    <!-- RESULT -->
    <div v-if="result" class="result-bar" :class="result.success ? 'result-ok' : 'result-error'">
      <CheckCircle v-if="result.success" :size="ICON_SIZE.STANDARD" />
      <AlertTriangle v-else :size="ICON_SIZE.STANDARD" />
      <div class="result-stats">
        <span>{{ result.files_created }} souboru vytvoreno</span>
        <span>{{ result.links_created }} linku</span>
        <span>{{ result.parts_updated }} dilu aktualizovano</span>
        <span v-if="result.errors.length" class="result-errors">
          {{ result.errors.length }} chyb
        </span>
      </div>
      <div v-if="result.errors.length" class="error-list">
        <div v-for="(err, i) in result.errors.slice(0, 10)" :key="i" class="error-item">
          {{ err }}
        </div>
        <div v-if="result.errors.length > 10" class="error-more">
          ... a {{ result.errors.length - 10 }} dalsich
        </div>
      </div>
    </div>

    <!-- LOADING STATE -->
    <div v-if="!preview && !scanning" class="empty-state">
      <FolderOpen :size="ICON_SIZE.XLARGE" />
      <p>Klikni "Skenovat" pro nacteni slozek ze share</p>
    </div>
  </div>
</template>

<style scoped>
.drawing-import-panel {
  display: flex;
  flex-direction: column;
  gap: var(--pad);
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--pad) 12px;
  border-bottom: 1px solid var(--b2);
}

.panel-header h3 {
  font-size: var(--fs);
  font-weight: 600;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 6px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: var(--raised);
  border-radius: var(--r);
  font-size: var(--fs);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-label {
  color: var(--t3);
}

.status-value {
  color: var(--t1);
}

.mono {
  font-family: var(--mono);
}

.stats-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  flex-wrap: wrap;
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px var(--pad);
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: 99px;
  background: transparent;
  color: var(--t3);
  cursor: pointer;
  transition: all 0.15s;
}

.stat-chip:hover {
  border-color: var(--b3);
  color: var(--t1);
}

.stat-chip.active {
  border-color: var(--t1);
  color: var(--t1);
  background: var(--raised);
}

.stat-skip {
  font-size: var(--fs);
  color: var(--t3);
}

.search-row {
  padding: 0 12px;
}

.folder-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.folder-row {
  display: grid;
  grid-template-columns: 32px 1fr 80px 48px 48px 1fr 48px;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  font-size: var(--fs);
  border-bottom: 1px solid var(--b1);
  cursor: default;
}

.folder-row:hover {
  background: var(--b1);
}

.folder-row.selected {
  background: var(--b1);
}

.folder-header {
  font-weight: 600;
  color: var(--t3);
  border-bottom: 1px solid var(--b2);
  position: sticky;
  top: 0;
  background: var(--base);
  z-index: 1;
}

.col-check {
  display: flex;
  align-items: center;
  justify-content: center;
}

.col-files {
  display: flex;
  align-items: center;
  gap: 2px;
  justify-content: center;
  font-family: var(--mono);
}

.col-primary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--fs);
}

.col-status {
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--pad) 12px;
  border-top: 1px solid var(--b2);
}

.selection-info {
  font-size: var(--fs);
  color: var(--t3);
}

.result-bar {
  padding: var(--pad) 12px;
  border-radius: var(--r);
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0 12px;
}

.result-ok {
  border: 1px solid var(--b2);
  background: var(--raised);
}

.result-error {
  border: 1px solid var(--red-10);
  background: var(--raised);
}

.result-stats {
  display: flex;
  gap: 12px;
  font-size: var(--fs);
  color: var(--t3);
}

.result-errors {
  color: var(--red);
  font-weight: 600;
}

.error-list {
  font-size: var(--fs);
  color: var(--t3);
  max-height: 120px;
  overflow-y: auto;
}

.error-item {
  padding: 2px 0;
  font-family: var(--mono);
}

.error-more {
  color: var(--t3);
  font-style: italic;
}

</style>
