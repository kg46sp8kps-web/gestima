<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as inforSyncApi from '@/api/infor-sync'
import * as inforImportApi from '@/api/infor-import'
import type { SyncStatus, SyncLog, ImportPreviewResponse, ImportExecuteResponse } from '@/types/infor-sync'
import { formatDate } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

type InforTab = 'sync' | 'parts' | 'routing' | 'production'
type ImportType = 'parts' | 'routing' | 'production'

const activeTab = ref<InforTab>('sync')

// ── Sync tab ──
const syncStatus = ref<SyncStatus | null>(null)
const syncLogs = ref<SyncLog[]>([])
const syncLoading = ref(false)
const syncError = ref(false)

async function loadSync() {
  if (syncStatus.value) return
  syncLoading.value = true
  syncError.value = false
  try {
    const [status, logs] = await Promise.all([
      inforSyncApi.getStatus(),
      inforSyncApi.getLogs({ limit: 30 }),
    ])
    syncStatus.value = status
    syncLogs.value = logs.items
  } catch {
    syncError.value = true
  } finally {
    syncLoading.value = false
  }
}

// ── Import tabs ──
interface ImportState {
  file: File | null
  previewing: boolean
  executing: boolean
  preview: ImportPreviewResponse | null
  result: ImportExecuteResponse | null
  error: string | null
}

function freshImport(): ImportState {
  return { file: null, previewing: false, executing: false, preview: null, result: null, error: null }
}

const imports = ref<Record<ImportType, ImportState>>({
  parts:      freshImport(),
  routing:    freshImport(),
  production: freshImport(),
})

function importTypeForTab(tab: InforTab): ImportType | null {
  if (tab === 'parts' || tab === 'routing' || tab === 'production') return tab
  return null
}

// Reactive current import state
const imp = computed<ImportState | null>(() => {
  const t = importTypeForTab(activeTab.value)
  return t ? imports.value[t] : null
})

function onFileSelected(event: Event) {
  const t = importTypeForTab(activeTab.value)
  if (!t) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const state = imports.value[t]
  state.file = file
  state.preview = null
  state.result = null
  state.error = null
  runPreview(t)
  input.value = ''
}

async function runPreview(t: ImportType) {
  const state = imports.value[t]
  if (!state.file) return
  state.previewing = true
  state.error = null
  try {
    state.preview = await inforImportApi.preview(t, state.file)
  } catch {
    state.error = 'Chyba při načítání náhledu'
  } finally {
    state.previewing = false
  }
}

async function runExecute(t: ImportType) {
  const state = imports.value[t]
  if (!state.file) return
  state.executing = true
  state.error = null
  try {
    state.result = await inforImportApi.execute(t, state.file)
  } catch {
    state.error = 'Chyba při importu'
  } finally {
    state.executing = false
  }
}

function resetImport(t: ImportType) {
  imports.value[t] = freshImport()
}

function switchTab(tab: InforTab) {
  activeTab.value = tab
  if (tab === 'sync') loadSync()
}

const LOG_STATUS_CLASSES: Record<string, string> = {
  success: 'badge-dot ok',
  error:   'badge-dot err',
  skipped: 'badge-dot neutral',
}

const IMPORT_LABELS: Record<ImportType, string> = {
  parts:      'Díly',
  routing:    'Technologie',
  production: 'Výroba',
}

onMounted(loadSync)
</script>

<template>
  <div class="tab-content">
    <!-- Inner subtab strip -->
    <div class="ptabs">
      <button
        v-for="tab in (['sync', 'parts', 'routing', 'production'] as InforTab[])"
        :key="tab"
        :class="['ptab', activeTab === tab ? 'on' : '']"
        :data-testid="`infor-tab-${tab}`"
        @click="switchTab(tab)"
      >
        {{ tab === 'sync' ? 'Sync stav' : IMPORT_LABELS[tab as ImportType] }}
      </button>
    </div>

    <!-- ── Sync stav ── -->
    <template v-if="activeTab === 'sync'">
      <div v-if="syncLoading" class="mod-placeholder">
        <Spinner size="sm" />
      </div>
      <div v-else-if="syncError" class="mod-placeholder">
        <div class="mod-dot err" />
        <span class="mod-label">Chyba při načítání</span>
      </div>
      <template v-else-if="syncStatus">
        <div class="sync-header">
          <span class="sync-running">
            <span :class="['badge-dot', syncStatus.running ? 'ok' : 'neutral']" />
            {{ syncStatus.running ? 'Sync běží' : 'Sync neběží' }}
          </span>
        </div>

        <div class="section-label">Kroky synchronizace</div>
        <div class="ot-wrap ot-half">
          <table class="ot">
            <thead>
              <tr>
                <th>Krok</th>
                <th style="width:110px">Poslední sync</th>
                <th class="r" style="width:48px">Vytvořeno</th>
                <th class="r" style="width:40px">Chyb</th>
                <th style="width:60px">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in syncStatus.steps"
                :key="s.id"
                :data-testid="`sync-step-${s.step_name}`"
              >
                <td>
                  <div class="step-name">{{ s.step_name }}</div>
                  <div v-if="s.last_error" class="step-err t4">{{ s.last_error }}</div>
                </td>
                <td class="mono t4">{{ s.last_sync_at ? formatDate(s.last_sync_at) : '—' }}</td>
                <td class="r mono t4">{{ s.created_count }}</td>
                <td class="r mono" :class="s.error_count > 0 ? 'err-text' : 't4'">
                  {{ s.error_count }}
                </td>
                <td>
                  <span class="badge">
                    <span :class="['badge-dot', s.enabled ? 'ok' : 'neutral']" />
                    {{ s.enabled ? 'Povoleno' : 'Vypnuto' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-label">Poslední záznamy</div>
        <div class="ot-wrap ot-flex">
          <table class="ot">
            <thead>
              <tr>
                <th>Krok</th>
                <th style="width:100px">Datum</th>
                <th style="width:55px">Status</th>
                <th class="r" style="width:45px">Načteno</th>
                <th class="r" style="width:48px">Vytvořeno</th>
                <th class="r" style="width:40px">Chyb</th>
                <th class="r" style="width:58px">Trvání</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="l in syncLogs"
                :key="l.id"
                :data-testid="`sync-log-${l.id}`"
              >
                <td class="t4">{{ l.step_name }}</td>
                <td class="mono t4">{{ formatDate(l.created_at) }}</td>
                <td>
                  <span class="badge">
                    <span :class="LOG_STATUS_CLASSES[l.status] ?? 'badge-dot neutral'" />
                    {{ l.status }}
                  </span>
                </td>
                <td class="r mono t4">{{ l.fetched_count }}</td>
                <td class="r mono t4">{{ l.created_count }}</td>
                <td class="r mono" :class="l.error_count > 0 ? 'err-text' : 't4'">
                  {{ l.error_count }}
                </td>
                <td class="r mono t4">
                  {{ l.duration_ms != null ? `${l.duration_ms} ms` : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>

    <!-- ── Import tabs (parts / routing / production) ── -->
    <template v-else-if="imp !== null">
      <div class="import-panel">
        <!-- No result yet: show upload + optional preview -->
        <template v-if="!imp.result">
          <label
            class="upload-zone"
            :data-testid="`import-drop-${activeTab}`"
          >
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              class="upload-input"
              @change="onFileSelected"
            />
            <span class="upload-hint">
              {{ imp.file ? imp.file.name : 'Klikněte pro výběr souboru (.csv, .xlsx)' }}
            </span>
          </label>

          <div v-if="imp.previewing" class="mod-placeholder">
            <Spinner size="sm" />
            <span class="mod-label">Načítám náhled…</span>
          </div>

          <template v-else-if="imp.preview">
            <div class="preview-header">
              <div class="preview-counts">
                <span class="cnt ok">{{ imp.preview.valid_count }} platných</span>
                <span class="cnt err-text">{{ imp.preview.error_count }} chyb</span>
                <span class="cnt t4">{{ imp.preview.duplicate_count }} duplikátů</span>
              </div>
              <div class="preview-actions">
                <button
                  class="btn-secondary"
                  :data-testid="`import-reset-${activeTab}`"
                  @click="resetImport(activeTab as ImportType)"
                >Zrušit</button>
                <button
                  class="btn-primary"
                  :disabled="imp.preview.valid_count === 0 || imp.executing"
                  :data-testid="`import-execute-${activeTab}`"
                  @click="runExecute(activeTab as ImportType)"
                >
                  {{ imp.executing ? 'Importuji…' : `Importovat ${IMPORT_LABELS[activeTab as ImportType]}` }}
                </button>
              </div>
            </div>
          </template>

          <div v-if="imp.error" class="import-error">{{ imp.error }}</div>
        </template>

        <!-- Result panel -->
        <template v-else>
          <div class="result-panel">
            <div :class="['result-icon', imp.result.success ? 'ok' : 'err']">
              {{ imp.result.success ? '✓' : '✗' }}
            </div>
            <div class="result-stats">
              <span class="cnt ok">{{ imp.result.created_count }} vytvořeno</span>
              <span class="cnt t4">{{ imp.result.updated_count }} aktualizováno</span>
              <span class="cnt t4">{{ imp.result.skipped_count }} přeskočeno</span>
              <span v-if="imp.result.errors.length" class="cnt err-text">
                {{ imp.result.errors.length }} chyb
              </span>
            </div>
            <div v-if="imp.result.errors.length" class="err-list">
              <div
                v-for="(e, i) in imp.result.errors.slice(0, 5)"
                :key="i"
                class="err-item"
              >{{ e }}</div>
              <div v-if="imp.result.errors.length > 5" class="t4 err-item">
                + {{ imp.result.errors.length - 5 }} dalších chyb
              </div>
            </div>
            <button
              class="btn-secondary"
              :data-testid="`import-new-${activeTab}`"
              @click="resetImport(activeTab as ImportType)"
            >Nový import</button>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }

.ptabs {
  display: flex; gap: 1px; padding: 3px var(--pad);
  border-bottom: 1px solid var(--b2); flex-shrink: 0;
  background: rgba(255,255,255,0.01);
}
.ptab {
  padding: 3px 7px; font-size: 10.5px; font-weight: 500; color: var(--t4);
  background: transparent; border: none; border-radius: var(--rs);
  cursor: pointer; font-family: var(--font);
}
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }

/* Sync */
.sync-header {
  display: flex; align-items: center; gap: 8px;
  padding: 6px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.sync-running {
  display: flex; align-items: center; gap: 5px;
  font-size: var(--fsl); color: var(--t2); font-weight: 500;
}
.section-label {
  padding: 4px var(--pad) 3px; font-size: 10px; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--b1);
  background: rgba(255,255,255,0.015); flex-shrink: 0;
}
.ot-half { max-height: 40%; overflow-y: auto; overflow-x: hidden; }
.ot-flex { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.step-name { font-size: var(--fs); color: var(--t2); }
.step-err { font-size: 10px; margin-top: 1px; }

/* Import */
.import-panel {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column;
  gap: 12px; padding: 12px var(--pad); min-height: 0;
}
.upload-zone {
  display: flex; align-items: center; justify-content: center;
  border: 1px dashed var(--b3); border-radius: var(--r); padding: 20px;
  cursor: pointer; transition: background 0.15s var(--ease);
}
.upload-zone:hover { background: var(--b1); }
.upload-input { display: none; }
.upload-hint { font-size: var(--fsl); color: var(--t3); }

.preview-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
}
.preview-counts { display: flex; gap: 10px; align-items: center; }
.preview-actions { display: flex; gap: 6px; align-items: center; }
.cnt { font-size: var(--fsl); font-weight: 600; font-family: var(--mono); }
.cnt.ok { color: var(--ok); }
.import-error {
  padding: 8px; background: var(--red-10); color: var(--red);
  border-radius: var(--rs); font-size: var(--fsl);
}
.result-panel {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  padding: 24px; flex: 1; justify-content: center;
}
.result-icon {
  width: 48px; height: 48px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 24px; font-weight: 700;
}
.result-icon.ok { background: var(--green-10); color: var(--green); }
.result-icon.err { background: var(--red-10); color: var(--red); }
.result-stats { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }
.err-list { display: flex; flex-direction: column; gap: 3px; width: 100%; max-width: 400px; }
.err-item { font-size: var(--fsl); color: var(--t3); padding: 2px 6px; background: var(--b1); border-radius: var(--rs); }

/* Tables */
.ot { width: 100%; border-collapse: collapse; }
.ot thead { background: rgba(255,255,255,0.025); position: sticky; top: 0; z-index: 2; }
.ot th {
  padding: 4px var(--pad); font-size: 10px; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.04em; text-align: left;
  border-bottom: 1px solid var(--b2); white-space: nowrap;
}
.ot th.r { text-align: right; }
.ot td {
  padding: 4px var(--pad); font-size: var(--fs); color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025); vertical-align: middle;
}
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); }

/* Shared */
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px;
  font-size: 10px; font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2);
}
.badge-dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }
.badge-dot.err { background: var(--err); }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }
.r { text-align: right; }
.err-text { color: var(--err); }

/* Buttons */
.btn-primary, .btn-secondary {
  padding: 4px 10px; font-size: var(--fsl); font-weight: 600;
  border-radius: var(--rs); border: 1px solid var(--b2); cursor: pointer;
  font-family: var(--font); transition: all 100ms var(--ease);
}
.btn-primary { background: var(--raised); color: var(--t1); border-color: var(--b3); }
.btn-primary:hover:not(:disabled) { background: var(--glass); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-secondary { background: transparent; color: var(--t3); }
.btn-secondary:hover { color: var(--t1); background: var(--b1); }
</style>
