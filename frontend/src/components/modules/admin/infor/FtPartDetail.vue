<script setup lang="ts">
/**
 * FT Part Detail - Expanded row showing GT operations + inference comparison
 */

import { ref } from 'vue'
import { runFtInference } from '@/api/ft-debug'
import { useUiStore } from '@/stores/ui'
import { useWindowsStore } from '@/stores/windows'
import { FileText, Brain, Loader } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface FtPartOperation {
  category: string; machine: string; operation_time_min: number
  setup_time_min: number; manning_pct: number; num_operations: number
  n_vp: number; planned_time_min: number | null; norm_ratio: number | null
  cv: number | null; manning_cv: number | null
}
interface FtPartSummary {
  part_id: number; article_number: string; name: string | null
  file_id: number | null; vp_count: number; material_norm: string | null
  stock_shape: string | null; operations: FtPartOperation[]
  max_cv: number | null; total_production_time: number
  total_planned_time: number | null; norm_ratio: number | null
  skip_reason: string | null; is_eligible: boolean
}
interface FtInferenceComparison {
  category: string; ai_time: number; gt_time: number; delta: number
  ai_setup: number; gt_setup: number
}
interface FtInferenceResult {
  material_gt: string | null; material_ai: string | null; material_match: boolean
  comparisons: FtInferenceComparison[]; mape: number | null
  tokens_used: number; cost_estimate: number
}

const props = defineProps<{ part: FtPartSummary }>()
const uiStore = useUiStore()
const windowsStore = useWindowsStore()
const inferring = ref(false)
const inferenceResult = ref<FtInferenceResult | null>(null)

function openDrawing() {
  if (props.part.file_id) {
    windowsStore.openWindow(
      'part-drawing',
      `Drawing - ${props.part.article_number}`,
    )
  }
}

async function runInference() {
  inferring.value = true
  try {
    const data = await runFtInference(props.part.part_id)
    inferenceResult.value = data
    uiStore.showSuccess(`Inference hotova — MAPE: ${data.mape?.toFixed(0) ?? '?'}%`)
  } catch (err: unknown) {
    const axErr = err as { response?: { data?: { detail?: string } }; message?: string }
    const msg = axErr.response?.data?.detail || axErr.message || 'Chyba inference'
    uiStore.showError(msg)
  } finally { inferring.value = false }
}

function fmt(v: number, d = 2): string { return v.toFixed(d) }
function normClass(ratio: number | null): string {
  if (ratio == null) return ''
  if (ratio < 0.5 || ratio > 3.0) return 'norm-extreme'
  if (ratio < 0.8 || ratio > 1.5) return 'norm-warn'
  return 'norm-ok'
}
</script>

<template>
  <div class="ft-detail">
    <div class="detail-header">
      <span class="detail-title">{{ part.article_number }} &mdash; {{ part.name || '?' }}</span>
      <span class="detail-meta">
        Material: {{ part.material_norm || '?' }} | Polotovar: {{ part.stock_shape || '?' }} | {{ part.vp_count }} VP
        <template v-if="part.norm_ratio != null">
          | Plnění normy: <strong :class="normClass(part.norm_ratio)">{{ fmt(part.norm_ratio) }}x</strong>
        </template>
      </span>
    </div>

    <table class="ops-table">
      <thead>
        <tr>
          <th>Kategorie</th><th>Stroj</th><th>Cas (min)</th><th>Norma (min)</th><th>Ratio</th>
          <th>Setup</th><th>Manning</th><th>#Op</th><th>Time CV</th><th>Mann CV</th><th>nVP</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="op in part.operations" :key="op.category">
          <td class="cat-badge">{{ op.category }}</td>
          <td>{{ op.machine }}</td>
          <td class="mono">{{ fmt(op.operation_time_min) }}</td>
          <td class="mono">{{ op.planned_time_min != null ? fmt(op.planned_time_min) : '-' }}</td>
          <td class="mono" :class="normClass(op.norm_ratio)">
            {{ op.norm_ratio != null ? fmt(op.norm_ratio) + 'x' : '-' }}
          </td>
          <td class="mono">{{ fmt(op.setup_time_min, 0) }}</td>
          <td class="mono">{{ op.manning_pct }}%</td>
          <td class="mono">{{ op.num_operations }}</td>
          <td class="mono" :class="{ 'cv-high': op.cv != null && op.cv > 0.5 }">
            {{ op.cv != null ? fmt(op.cv) : '-' }}
          </td>
          <td class="mono" :class="{ 'cv-high': op.manning_cv != null && op.manning_cv > 0.5 }">
            {{ op.manning_cv != null ? fmt(op.manning_cv) : '-' }}
          </td>
          <td class="mono">{{ op.n_vp }}</td>
        </tr>
      </tbody>
    </table>

    <div class="detail-actions">
      <button v-if="part.file_id" @click="openDrawing" class="btn-ghost btn-secondary">
        <FileText :size="ICON_SIZE.STANDARD" /> Otevrit vykres
      </button>
      <button @click="runInference" :disabled="inferring || !part.file_id" class="btn-ghost btn-primary">
        <Loader v-if="inferring" :size="ICON_SIZE.STANDARD" class="spin" />
        <Brain v-else :size="ICON_SIZE.STANDARD" />
        {{ inferring ? 'Inference...' : 'Spustit inference' }}
      </button>
    </div>

    <div v-if="inferenceResult" class="inference-result">
      <div class="inference-header">
        <span>
          Material: GT={{ inferenceResult.material_gt || '?' }} | AI={{ inferenceResult.material_ai || '?' }}
          <span :class="inferenceResult.material_match ? 'match-ok' : 'match-fail'">
            {{ inferenceResult.material_match ? '&#10003;' : '&#10007;' }}
          </span>
        </span>
        <span>MAPE: <strong>{{ inferenceResult.mape != null ? fmt(inferenceResult.mape, 0) + '%' : '?' }}</strong></span>
        <span class="inference-meta">Tokens: {{ inferenceResult.tokens_used }} | ~${{ fmt(inferenceResult.cost_estimate, 3) }}</span>
      </div>
      <table class="ops-table">
        <thead>
          <tr>
            <th>Kategorie</th><th>AI cas</th><th>GT cas</th><th>Delta</th><th>AI setup</th><th>GT setup</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in inferenceResult.comparisons" :key="c.category">
            <td class="cat-badge">{{ c.category }}</td>
            <td class="mono">{{ fmt(c.ai_time) }}</td>
            <td class="mono">{{ fmt(c.gt_time) }}</td>
            <td class="mono" :class="{ 'delta-pos': c.delta > 0, 'delta-neg': c.delta < 0 }">
              {{ c.delta >= 0 ? '+' : '' }}{{ fmt(c.delta) }}
            </td>
            <td class="mono">{{ fmt(c.ai_setup, 0) }}</td>
            <td class="mono">{{ fmt(c.gt_setup, 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.ft-detail { padding: 12px; }
.detail-header { display: flex; align-items: baseline; gap: 6px; margin-bottom: var(--pad); flex-wrap: wrap; }
.detail-title { font-weight: 600; font-size: var(--fs); color: var(--t1); }
.detail-meta { font-size: var(--fs); color: var(--t3); }
.ops-table { width: 100%; border-collapse: collapse; font-size: var(--fs); margin-bottom: 6px; }
.ops-table th { background: var(--surface); padding: 4px 6px; text-align: left; font-weight: 600; color: var(--t3); border-bottom: 1px solid var(--b2); white-space: nowrap; }
.ops-table td { padding: 4px 6px; border-bottom: 1px solid var(--b1); white-space: nowrap; }
.cat-badge { font-weight: 600; font-size: var(--fs); color: var(--t1); }
.mono { font-variant-numeric: tabular-nums; font-family: var(--mono); }
.cv-high { color: var(--err); font-weight: 600; }
.norm-ok { color: var(--ok); }
.norm-warn { color: var(--warn); font-weight: 600; }
.norm-extreme { color: var(--err); font-weight: 600; }
.detail-actions { display: flex; gap: 6px; margin: var(--pad) 0; }
.inference-result { margin-top: var(--pad); padding: var(--pad); background: var(--surface); border-radius: var(--r); border: 1px solid var(--b2); }
.inference-header { display: flex; gap: 12px; font-size: var(--fs); margin-bottom: 6px; flex-wrap: wrap; align-items: center; }
.inference-meta { font-size: var(--fs); color: var(--t3); }
.match-ok { color: var(--ok); font-weight: 600; }
.match-fail { color: var(--err); font-weight: 600; }
.delta-pos { color: var(--err); }
.delta-neg { color: var(--ok); }
</style>
