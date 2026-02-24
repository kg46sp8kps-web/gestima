<script setup lang="ts">
/**
 * FT Part Detail - Expanded row showing GT operations + inference comparison
 */

import { ref } from 'vue'
import { runFtInference } from '@/api/ft-debug'
import type { FtPartSummary, FtInferenceResult } from '@/api/ft-debug'
import { useUiStore } from '@/stores/ui'
import { FileText, Brain, Loader, X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{ part: FtPartSummary }>()
const emit = defineEmits<{ close: [] }>()
const uiStore = useUiStore()
const inferring = ref(false)
const inferenceResult = ref<FtInferenceResult | null>(null)

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
      <button class="btn-icon close-btn" @click="emit('close')" data-testid="ft-detail-close">
        <X :size="ICON_SIZE" />
      </button>
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
      <button v-if="part.file_id" class="btn-secondary" data-testid="ft-detail-drawing">
        <FileText :size="ICON_SIZE" /> Vykres k dispozici
      </button>
      <button @click="runInference" :disabled="inferring || !part.file_id" class="btn-primary" data-testid="ft-run-inference">
        <Loader v-if="inferring" :size="ICON_SIZE" class="spin" />
        <Brain v-else :size="ICON_SIZE" />
        {{ inferring ? 'Inference...' : 'Spustit inference' }}
      </button>
    </div>

    <div v-if="inferenceResult" class="inference-result">
      <div class="inference-header">
        <span>
          Material: GT={{ inferenceResult.material_gt || '?' }} | AI={{ inferenceResult.material_ai || '?' }}
          <span :class="inferenceResult.material_match ? 'match-ok' : 'match-fail'">
            {{ inferenceResult.material_match ? '✓' : '✗' }}
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
.detail-meta { font-size: var(--fs); color: var(--t3); flex: 1; }
.close-btn { margin-left: auto; align-self: center; }
.ops-table { width: 100%; border-collapse: collapse; font-size: var(--fs); margin-bottom: 6px; }
.ops-table th { background: var(--surface); padding: 4px 6px; text-align: left; font-weight: 600; color: var(--t3); border-bottom: 1px solid var(--b2); white-space: nowrap; }
.ops-table td { padding: 4px 6px; border-bottom: 1px solid var(--b1); white-space: nowrap; }
.cat-badge { font-weight: 600; font-size: var(--fs); color: var(--t1); }
.mono { font-variant-numeric: tabular-nums; }
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
.btn-icon { background: transparent; border: none; cursor: pointer; color: var(--t3); padding: 4px; border-radius: var(--rs); display: inline-flex; align-items: center; }
.btn-icon:hover { color: var(--t1); }
</style>
