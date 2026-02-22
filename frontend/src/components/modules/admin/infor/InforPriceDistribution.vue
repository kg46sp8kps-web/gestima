<script setup lang="ts">
import type { WeightDistribution, TierAnalysis, TierBoundaryUpdate } from '@/types/purchase-prices'
import { applyBoundaries } from '@/api/purchase-prices'
import { useUiStore } from '@/stores/ui'
import { ref } from 'vue'

const props = defineProps<{
  distribution: WeightDistribution | null
  tiers: TierAnalysis[]
  categoryId: number
}>()

const emit = defineEmits<{ (e: 'boundaries-applied'): void }>()

const uiStore = useUiStore()
const applying = ref(false)

const fmtKg = (n: number) => n.toLocaleString('cs-CZ', { maximumFractionDigits: 0 })

function barPos(val: number, max: number) {
  if (max <= 0) return '0%'
  return Math.min((val / max) * 100, 100).toFixed(1) + '%'
}

const hasSuggestions = () => (props.distribution?.suggested_boundaries?.length ?? 0) > 0

async function applySuggested() {
  if (!props.distribution || !hasSuggestions()) return
  applying.value = true
  try {
    // Build boundary updates from suggestions merged with current tier data
    const tiersCopy = [...props.tiers]
    const suggestions = props.distribution.suggested_boundaries

    // Apply suggestions to a working copy of boundaries
    const boundaries: TierBoundaryUpdate[] = tiersCopy.map((tier, idx) => {
      const suggestion = suggestions.find(s => s.tier_index === idx)
      const newMax = suggestion ? suggestion.suggested_max_weight : tier.max_weight
      // For the tier AFTER a changed boundary, update its min_weight
      const prevSuggestion = suggestions.find(s => s.tier_index === idx - 1)
      const newMin = prevSuggestion && prevSuggestion.suggested_max_weight != null
        ? prevSuggestion.suggested_max_weight : tier.min_weight
      return {
        tier_id: tier.tier_id,
        new_min_weight: newMin,
        new_max_weight: newMax,
        version: tier.current_tier_version,
      }
    })

    const result = await applyBoundaries({ category_id: props.categoryId, tier_boundaries: boundaries })
    if (result.success) {
      uiStore.showSuccess(`Hranice tieru aktualizovany (${result.updated_count} tieru)`)
      emit('boundaries-applied')
    } else {
      uiStore.showError(result.errors.join(', ') || 'Chyba pri aplikaci hranic')
    }
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba pri aplikaci hranic')
  } finally { applying.value = false }
}
</script>

<template>
  <div v-if="props.distribution" class="dist-panel">
    <div class="dist-title">Distribuce velikosti nakupu (kg na objednavku)</div>
    <div class="dist-stats">
      <span>Min: <b>{{ fmtKg(props.distribution.min_qty) }}</b> kg</span>
      <span>P25: <b>{{ fmtKg(props.distribution.p25) }}</b> kg</span>
      <span>Median: <b>{{ fmtKg(props.distribution.p50) }}</b> kg</span>
      <span>P75: <b>{{ fmtKg(props.distribution.p75) }}</b> kg</span>
      <span>Max: <b>{{ fmtKg(props.distribution.max_qty) }}</b> kg</span>
      <span>Prumer: <b>{{ fmtKg(props.distribution.avg_qty) }}</b> kg</span>
      <span>({{ props.distribution.sample_count }} objednavek)</span>
    </div>
    <div class="dist-bar-wrap">
      <div class="dist-bar">
        <div class="dist-range"
             :style="{ left: barPos(props.distribution.p25, props.distribution.max_qty),
                       width: 'calc(' + barPos(props.distribution.p75, props.distribution.max_qty) + ' - ' + barPos(props.distribution.p25, props.distribution.max_qty) + ')' }">
        </div>
        <div class="dist-marker dist-median"
             :style="{ left: barPos(props.distribution.p50, props.distribution.max_qty) }">
          <div class="dist-label">P50</div>
        </div>
        <!-- Current tier boundaries (red) -->
        <div v-for="tier in props.tiers.slice(0, 2)" :key="'b'+tier.tier_id" class="dist-marker dist-tier-line"
             :style="{ left: barPos(tier.max_weight ?? 0, props.distribution.max_qty) }">
          <div class="dist-label tier-label">{{ tier.max_weight }} kg</div>
        </div>
        <!-- Suggested boundaries (green dashed) -->
        <div v-for="s in props.distribution.suggested_boundaries" :key="'s'+s.tier_index" class="dist-marker dist-suggested"
             :style="{ left: barPos(s.suggested_max_weight ?? 0, props.distribution.max_qty) }">
          <div class="dist-label suggested-label">{{ s.suggested_max_weight }} kg</div>
        </div>
      </div>
      <div class="dist-bar-labels">
        <span>0 kg</span>
        <span>{{ fmtKg(props.distribution.max_qty) }} kg</span>
      </div>
    </div>
    <div class="dist-hint">
      Modra = 50% nakupu (P25-P75).
      <span class="red-text">Cervene</span> = aktualni hranice.
      <template v-if="hasSuggestions()"><span class="green-text">Zelene</span> = navrhovane hranice.</template>
    </div>
    <!-- Suggested boundaries detail -->
    <div v-if="hasSuggestions()" class="suggestions">
      <div class="suggest-title">Navrhovane zmeny hranic:</div>
      <div v-for="s in props.distribution.suggested_boundaries" :key="s.tier_index" class="suggest-row">
        <span class="suggest-change">
          Tier {{ s.tier_index + 1 }}: <span class="old-val">{{ s.current_max_weight }} kg</span>
          → <span class="new-val">{{ s.suggested_max_weight }} kg</span>
        </span>
        <span class="suggest-reason">{{ s.reason }}</span>
      </div>
      <button class="btn-apply" @click="applySuggested" :disabled="applying">
        {{ applying ? 'Aplikuji...' : 'Aplikovat navrhovane hranice' }}
      </button>
    </div>
  </div>
  <div v-else class="dist-panel dist-empty">
    Nedostatek dat pro distribuci (min. 3 objednavky)
  </div>
</template>

<style scoped>
.dist-panel { display: flex; flex-direction: column; gap: var(--pad); }
.dist-title { font-weight: 500; font-size: var(--fs); color: var(--t1); }
.dist-stats { display: flex; gap: 12px; font-size: var(--fs); color: var(--t3); flex-wrap: wrap; }
.dist-stats b { color: var(--t1); font-family: var(--mono); }
.dist-bar-wrap { padding: 6px 0; }
.dist-bar { position: relative; height: 28px; background: var(--b1); border-radius: var(--rs); border: 1px solid var(--b1); }
.dist-range { position: absolute; top: 2px; bottom: 2px; background: rgba(37,99,235,0.1); border-radius: var(--rs); }
.dist-marker { position: absolute; top: 0; bottom: 0; width: 2px; }
.dist-median { background: var(--t3); }
.dist-tier-line { background: var(--err); }
.dist-suggested { background: var(--ok); border-left: 1px dashed var(--ok); width: 3px; opacity: 0.9; }
.dist-label { position: absolute; top: -16px; left: -12px; font-size: var(--fs); color: var(--t3); white-space: nowrap; }
.tier-label { color: var(--err); }
.suggested-label { color: var(--ok); top: auto; bottom: -16px; }
.dist-bar-labels { display: flex; justify-content: space-between; font-size: var(--fs); color: var(--t3); margin-top: 2px; }
.dist-hint, .dist-empty { font-size: var(--fs); color: var(--t3); font-style: italic; }
.red-text { color: var(--err); }
.green-text { color: var(--ok); }
.suggestions { padding: var(--pad); background: rgba(52,211,153,0.1); border: 1px solid rgba(34,197,94,0.15); border-radius: var(--r); display: flex; flex-direction: column; gap: 6px; }
.suggest-title { font-size: var(--fs); font-weight: 500; color: var(--t1); }
.suggest-row { display: flex; gap: var(--pad); font-size: var(--fs); align-items: center; }
.suggest-change { font-family: var(--mono); color: var(--t1); }
.old-val { color: var(--err); text-decoration: line-through; }
.new-val { color: var(--ok); font-weight: 500; }
.suggest-reason { color: var(--t3); }
.btn-apply { align-self: flex-start; padding: 6px var(--pad); font-size: var(--fs); background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.15); border-radius: var(--r); color: var(--ok); cursor: pointer; transition: all 100ms var(--ease); margin-top: 4px; }
.btn-apply:hover:not(:disabled) { background: rgba(34,197,94,0.15); }
.btn-apply:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
