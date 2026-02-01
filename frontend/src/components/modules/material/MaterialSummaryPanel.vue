<template>
  <div v-if="summary" class="material-summary-panel">
    <div class="summary-header">
      <h4>Kalkulace materiálu</h4>
      <span v-if="loading" class="loading-indicator">Počítám...</span>
    </div>

    <div class="summary-layout">
      <!-- LEFT: Weight and price per piece -->
      <div class="summary-left">
        <div class="summary-item">
          <span class="item-label">Hmotnost na 1 ks</span>
          <span class="item-value mono">{{ summary.weight_kg.toFixed(3) }} kg</span>
        </div>

        <div class="summary-item">
          <span class="item-label">Cena za kus</span>
          <span class="item-value mono price">{{ summary.cost_per_piece.toFixed(2) }} Kč</span>
        </div>
      </div>

      <!-- RIGHT: Price tiers table -->
      <div class="summary-right">
        <div class="tier-table-header">
          <span class="tier-label">Cenové pásy</span>
        </div>
        <table v-if="allTiers && allTiers.length > 0" class="tier-table">
          <tbody>
            <tr
              v-for="tier in sortedTiers"
              :key="tier.id"
              :class="{ 'tier-selected': tier.id === summary.tier_id }"
            >
              <td class="tier-range">
                {{ tier.min_weight }}-{{ tier.max_weight ? tier.max_weight : '∞' }} kg
              </td>
              <td class="tier-price">{{ tier.price_per_kg.toFixed(2) }} Kč/kg</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="tier-table-empty">
          Žádné cenové pásy
        </div>
      </div>
    </div>
  </div>

  <!-- Empty state -->
  <div v-else class="summary-empty">
    <p>Vyplňte rozměry a kategorii pro zobrazení kalkulace</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MaterialSummary, MaterialPriceTier } from '@/types/material'

interface Props {
  summary: MaterialSummary | null
  allTiers?: MaterialPriceTier[] | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  allTiers: null
})

// Sort tiers by min_weight ascending
const sortedTiers = computed(() => {
  if (!props.allTiers) return []

  console.log('[MaterialSummaryPanel] allTiers count:', props.allTiers.length, 'IDs:', props.allTiers.map(t => t.id))

  // Remove duplicates by ID
  const uniqueTiers = props.allTiers.filter((tier, index, self) =>
    index === self.findIndex((t) => t.id === tier.id)
  )

  console.log('[MaterialSummaryPanel] uniqueTiers count:', uniqueTiers.length, 'IDs:', uniqueTiers.map(t => t.id))

  return uniqueTiers.sort((a, b) => a.min_weight - b.min_weight)
})
</script>

<style scoped>
.material-summary-panel {
  padding: var(--space-4);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.summary-header h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-body);
}

.loading-indicator {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-style: italic;
}

/* Layout: LEFT (weight/price) | RIGHT (tier table) */
.summary-layout {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: var(--space-4);
}

/* LEFT section */
.summary-left {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.item-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.item-value {
  font-size: var(--text-lg);
  color: var(--text-body);
  font-weight: var(--font-semibold);
}

.item-value.mono {
  font-family: var(--font-mono);
}

.item-value.price {
  color: var(--palette-success);
}

/* RIGHT section - Tier table */
.summary-right {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tier-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tier-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tier-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.tier-table tbody tr {
  border-bottom: 1px solid var(--border-default);
  transition: background-color 0.15s ease;
}

.tier-table tbody tr:last-child {
  border-bottom: none;
}

.tier-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.05);
}

.tier-table tbody tr.tier-selected {
  background: var(--palette-success-light, rgba(34, 197, 94, 0.15));
  border-left: 3px solid var(--palette-success);
}

.tier-table td {
  padding: var(--space-2) var(--space-1);
}

.tier-range {
  font-family: var(--font-mono);
  color: var(--text-body);
  font-weight: var(--font-medium);
}

.tier-price {
  font-family: var(--font-mono);
  color: var(--palette-success);
  font-weight: var(--font-semibold);
  text-align: right;
}

.tier-table-empty {
  padding: var(--space-3);
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-style: italic;
}

/* Empty state */
.summary-empty {
  padding: var(--space-6);
  background: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.summary-empty p {
  margin: 0;
}
</style>
