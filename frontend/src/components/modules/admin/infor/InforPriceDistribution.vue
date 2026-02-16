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
.dist-panel { display: flex; flex-direction: column; gap: var(--space-3); }
.dist-title { font-weight: var(--font-medium); font-size: var(--text-sm); color: var(--text-primary); }
.dist-stats { display: flex; gap: var(--space-4); font-size: var(--text-xs); color: var(--text-secondary); flex-wrap: wrap; }
.dist-stats b { color: var(--text-primary); font-family: var(--font-mono); }
.dist-bar-wrap { padding: var(--space-2) 0; }
.dist-bar { position: relative; height: 28px; background: rgba(255,255,255,0.05); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); }
.dist-range { position: absolute; top: 2px; bottom: 2px; background: var(--palette-info-bg); border-radius: var(--radius-sm); }
.dist-marker { position: absolute; top: 0; bottom: 0; width: 2px; }
.dist-median { background: var(--palette-info); }
.dist-tier-line { background: var(--status-error); }
.dist-suggested { background: var(--status-ok); border-left: 1px dashed var(--status-ok); width: 3px; opacity: 0.9; }
.dist-label { position: absolute; top: -16px; left: -12px; font-size: 9px; color: var(--text-tertiary); white-space: nowrap; }
.tier-label { color: var(--status-error); }
.suggested-label { color: var(--status-ok); top: auto; bottom: -16px; }
.dist-bar-labels { display: flex; justify-content: space-between; font-size: var(--text-2xs); color: var(--text-tertiary); margin-top: 2px; }
.dist-hint, .dist-empty { font-size: var(--text-xs); color: var(--text-tertiary); font-style: italic; }
.red-text { color: var(--status-error); }
.green-text { color: var(--status-ok); }
.suggestions { padding: var(--space-3); background: rgba(34,197,94,0.05); border: 1px solid rgba(34,197,94,0.2); border-radius: var(--radius-md); display: flex; flex-direction: column; gap: var(--space-2); }
.suggest-title { font-size: var(--text-xs); font-weight: var(--font-medium); color: var(--text-primary); }
.suggest-row { display: flex; gap: var(--space-3); font-size: var(--text-xs); align-items: center; }
.suggest-change { font-family: var(--font-mono); color: var(--text-primary); }
.old-val { color: var(--status-error); text-decoration: line-through; }
.new-val { color: var(--status-ok); font-weight: var(--font-medium); }
.suggest-reason { color: var(--text-tertiary); }
.btn-apply { align-self: flex-start; padding: var(--space-2) var(--space-3); font-size: var(--text-xs); background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.3); border-radius: var(--radius-md); color: var(--status-ok); cursor: pointer; transition: var(--transition-fast); margin-top: var(--space-1); }
.btn-apply:hover:not(:disabled) { background: rgba(34,197,94,0.25); }
.btn-apply:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
