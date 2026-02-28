<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useCatalogStore } from '@/stores/catalog'
import { useWorkshopStore } from '@/stores/workshop'
import { usePartsStore } from '@/stores/parts'
import { useWorkspaceStore } from '@/stores/workspace'
import * as partsApi from '@/api/parts'
import type { Part } from '@/types/part'
import type { ContextGroup, ModuleId } from '@/types/workspace'
import type { VpListItem } from '@/types/vp'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const catalog = useCatalogStore()
const workshop = useWorkshopStore()
const parts = usePartsStore()
const ws = useWorkspaceStore()

// Focused VP from catalog store
const focusedVp = computed(() => {
  const item = catalog.getFocusedItem(props.ctx)
  return item?.type === 'vp' ? item : null
})

// Find VP detail from store list
const vpDetail = computed<VpListItem | null>(() => {
  if (!focusedVp.value) return null
  return workshop.vpListItems.find(v => v.job === focusedVp.value!.number) ?? null
})

// Part lookup
const matchedPart = ref<Part | null>(null)

watch(() => vpDetail.value, async (vp) => {
  matchedPart.value = null
  if (!vp?.item) return
  // Try parts store first
  const found = parts.items.find(p => p.article_number === vp.item)
  if (found) { matchedPart.value = found; return }
  // Fallback: fetch from API
  try {
    const results = await partsApi.getAll({ search: vp.item, limit: 1 })
    const first = results.parts[0]
    if (first && first.article_number === vp.item) {
      matchedPart.value = first
    }
  } catch { /* ignore */ }
}, { immediate: true })

// Quick links
interface QuickLink {
  label: string
  module: ModuleId
  enabled: boolean
}

const quickLinks = computed<QuickLink[]>(() => [
  { label: 'Technologie VP', module: 'vp-work-ops', enabled: true },
  { label: 'Technologie dílu', module: 'work-ops', enabled: !!matchedPart.value },
])

function openModule(ql: QuickLink) {
  if (!ql.enabled) return
  if (ql.module === 'work-ops' && matchedPart.value) {
    // Focus Part first, then open work-ops
    catalog.focusItem({ type: 'part', number: matchedPart.value.part_number }, props.ctx)
  }
  ws.splitLeaf(props.leafId, ql.module, 'right', props.ctx)
}

// DnD — tab spawn
let qlDragTimer: ReturnType<typeof setTimeout> | null = null

function onQlDragStart(e: DragEvent, ql: QuickLink) {
  if (!ql.enabled || !e.dataTransfer) return
  e.dataTransfer.setData('text/plain', ql.module)
  e.dataTransfer.effectAllowed = 'move'
  qlDragTimer = setTimeout(() => {
    qlDragTimer = null
    ws.startDrag(null, ql.module, props.ctx)
  }, 0)
}

function onQlDragEnd() {
  if (qlDragTimer !== null) {
    clearTimeout(qlDragTimer)
    qlDragTimer = null
  }
  ws.endDrag()
}

function focusPart() {
  if (!matchedPart.value) return
  catalog.focusItem({ type: 'part', number: matchedPart.value.part_number }, props.ctx)
}

function statLabel(stat: string): string {
  switch (stat?.toUpperCase()) {
    case 'R': return 'Released'
    case 'F': return 'Firm'
    case 'S': return 'Scheduled'
    case 'W': return 'Waiting'
    default: return stat || '—'
  }
}

function statChipClass(stat: string): string {
  switch (stat?.toUpperCase()) {
    case 'R': return 'chip chip-ok'
    case 'F': return 'chip chip-w'
    case 'S': return 'chip chip-blue'
    default: return 'chip chip-o'
  }
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return '—'
  return String(v)
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—'
  return v.length > 10 ? v.substring(0, 10) : v
}
</script>

<template>
  <div class="vpd-root">
    <!-- Empty state -->
    <div v-if="!focusedVp" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte VP ze seznamu</span>
      <span class="mod-hint">Klikněte na výrobní příkaz vlevo</span>
    </div>

    <!-- VP info card -->
    <template v-else-if="vpDetail">
      <!-- Info bar -->
      <div class="det-bar">
        <span class="det-pn">{{ vpDetail.job }}/{{ vpDetail.suffix }}</span>
        <span :class="statChipClass(vpDetail.job_stat)">{{ statLabel(vpDetail.job_stat) }}</span>
      </div>

      <!-- Quick-link strip -->
      <div class="ql-strip">
        <button
          v-for="ql in quickLinks"
          :key="ql.module"
          :class="['ql-btn', { 'ql-dis': !ql.enabled }]"
          :title="ql.enabled ? `Otevřít ${ql.label}` : `${ql.label} — díl nenalezen`"
          :draggable="ql.enabled ? 'true' : 'false'"
          @click="openModule(ql)"
          @dragstart="onQlDragStart($event, ql)"
          @dragend="onQlDragEnd"
        >
          {{ ql.label }}
        </button>
      </div>

      <!-- Scrollable body -->
      <div class="form-body">
        <!-- VP data section -->
        <div class="form-section">
          <div class="sec-hdr">VP data</div>
          <div class="field-row">
            <div class="field field-half">
              <span class="info-lbl">Artikl</span>
              <span class="info-val mono">{{ vpDetail.item || '—' }}</span>
            </div>
            <div class="field field-half">
              <span class="info-lbl">Popis</span>
              <span class="info-val">{{ vpDetail.description || '—' }}</span>
            </div>
          </div>
          <div class="field-row">
            <div class="field field-third">
              <span class="info-lbl">Released</span>
              <span class="info-val mono">{{ fmtNum(vpDetail.qty_released) }}</span>
            </div>
            <div class="field field-third">
              <span class="info-lbl">Done</span>
              <span class="info-val mono">{{ fmtNum(vpDetail.qty_complete) }}</span>
            </div>
            <div class="field field-third">
              <span class="info-lbl">Scrap</span>
              <span class="info-val mono">{{ fmtNum(vpDetail.qty_scrapped) }}</span>
            </div>
          </div>
          <div class="field-row">
            <div class="field field-half">
              <span class="info-lbl">Datum začátku</span>
              <span class="info-val mono">{{ fmtDate(vpDetail.start_date) }}</span>
            </div>
            <div class="field field-half">
              <span class="info-lbl">Datum konce</span>
              <span class="info-val mono">{{ fmtDate(vpDetail.end_date) }}</span>
            </div>
          </div>
          <div class="field-row">
            <div class="field">
              <span class="info-lbl">Počet operací</span>
              <span class="info-val mono">{{ vpDetail.oper_count }}</span>
            </div>
          </div>
        </div>

        <!-- Matched Part section -->
        <div v-if="matchedPart" class="form-section">
          <div class="sec-hdr">
            Přilinkovaný díl
            <span class="badge-found">Díl nalezen</span>
          </div>
          <div class="field-row">
            <div class="field field-half">
              <span class="info-lbl">Part number</span>
              <span class="info-val part-link" @click="focusPart">{{ matchedPart.part_number }}</span>
            </div>
            <div class="field field-half">
              <span class="info-lbl">Název</span>
              <span class="info-val">{{ matchedPart.name || '—' }}</span>
            </div>
          </div>
          <div class="field-row">
            <div class="field field-half">
              <span class="info-lbl">Výkres č.</span>
              <span class="info-val mono">{{ matchedPart.drawing_number || '—' }}</span>
            </div>
            <div class="field field-sm">
              <span class="info-lbl">Rev.</span>
              <span class="info-val mono">{{ matchedPart.revision || '—' }}</span>
            </div>
          </div>
          <div class="field-row">
            <div class="field field-half">
              <span class="info-lbl">Hmotnost [kg]</span>
              <span class="info-val mono">{{ matchedPart.unit_weight != null ? matchedPart.unit_weight : '—' }}</span>
            </div>
            <div class="field field-half">
              <span class="info-lbl">Zmetkovitost [%]</span>
              <span class="info-val mono">{{ matchedPart.scrap_rate_percent }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.vpd-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* Placeholder */
.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
  user-select: none;
  padding: 24px;
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--t4);
}
.mod-label {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t4);
}
.mod-hint {
  font-size: var(--fsm);
  color: var(--t4);
  opacity: 0.6;
}

/* Info bar */
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
.det-pn {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  flex-shrink: 0;
  letter-spacing: 0.02em;
  font-family: var(--mono, monospace);
}

/* Status chip */
.chip {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--rs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.chip-ok   { background: rgba(76,175,80,0.15); color: var(--ok); }
.chip-w    { background: rgba(255,193,7,0.15);  color: var(--warn); }
.chip-blue { background: rgba(66,165,245,0.15); color: var(--link); }
.chip-o    { background: rgba(158,158,158,0.15); color: var(--t4); }

/* Quick-link strip */
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
.ql-btn.ql-dis {
  opacity: 0.35;
  cursor: default;
  pointer-events: none;
}

/* Scrollable body */
.form-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Form section */
.form-section {
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sec-hdr {
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
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
.field-half { flex: 1; min-width: 0; }
.field-third { flex: 1; min-width: 0; }
.field-sm { width: 80px; flex-shrink: 0; }

.info-lbl {
  font-size: var(--fsm);
  color: var(--t4);
  flex-shrink: 0;
}
.info-val {
  font-size: var(--fs);
  color: var(--t2);
  font-weight: 500;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-val.mono {
  font-family: var(--mono, monospace);
}

/* Part link */
.part-link {
  color: var(--link);
  cursor: pointer;
  font-family: var(--mono, monospace);
}
.part-link:hover {
  text-decoration: underline;
}

/* Badge */
.badge-found {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--rs);
  background: rgba(76,175,80,0.15);
  color: var(--ok);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
</style>
