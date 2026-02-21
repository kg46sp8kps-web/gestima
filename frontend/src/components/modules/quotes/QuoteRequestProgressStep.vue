<script setup lang="ts">
/**
 * QuoteRequestProgressStep — Step 3 of V2 wizard
 * Shows progress while creating, then results when done.
 */
import type { QuoteCreationResult } from '@/types/quote'
import { CheckCircle, AlertTriangle, ExternalLink, Loader } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { formatCurrency } from '@/utils/formatters'

const props = defineProps<{
  loading: boolean
  result: QuoteCreationResult | null
}>()

const emit = defineEmits<{
  'open-quote': [quoteNumber: string]
}>()
</script>

<template>
  <div class="progress-step">
    <!-- Loading state -->
    <div v-if="props.loading" class="loading">
      <Loader :size="ICON_SIZE.HERO" class="spin-icon" />
      <h3>Vytvářím nabídku...</h3>
      <p class="hint">Vytváření dílů, technologií a kalkulací. Trvá 10–30 sekund.</p>
    </div>

    <!-- Result state -->
    <div v-else-if="props.result" class="result">
      <div class="result-header">
        <CheckCircle :size="ICON_SIZE.HERO" class="success-icon" />
        <h2>Nabídka {{ props.result.quote_number }} vytvořena</h2>
      </div>

      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat">
          <span class="stat-value">{{ props.result.parts_created }}</span>
          <span class="stat-label">Nových dílů</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ props.result.parts_existing }}</span>
          <span class="stat-label">Existujících dílů</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ props.result.drawings_linked }}</span>
          <span class="stat-label">Výkresů přiřazeno</span>
        </div>
        <div class="stat stat-total">
          <span class="stat-value">{{ formatCurrency(props.result.total_amount) }}</span>
          <span class="stat-label">Celková cena</span>
        </div>
      </div>

      <!-- Parts detail -->
      <div class="parts-list">
        <div
          v-for="part in props.result.parts"
          :key="part.article_number"
          class="part-row"
        >
          <CheckCircle :size="ICON_SIZE.SMALL" class="part-check" />
          <span class="part-number">{{ part.part_number || part.article_number }}</span>
          <span class="part-name">{{ part.name }}</span>
          <span v-if="part.is_new" class="badge badge-new">Nový</span>
          <span v-else class="badge badge-existing">Existující</span>
          <span v-if="part.drawing_linked" class="badge badge-drawing">Výkres</span>
          <span v-if="part.technology_generated" class="badge badge-tech">Technologie</span>
          <span class="part-price">{{ formatCurrency(part.unit_price) }}/ks</span>
        </div>
      </div>

      <!-- Warnings -->
      <div v-if="props.result.warnings.length" class="warnings">
        <div v-for="(warn, i) in props.result.warnings" :key="i" class="warning-item">
          <AlertTriangle :size="ICON_SIZE.SMALL" />
          <span>{{ warn }}</span>
        </div>
      </div>

      <!-- Open quote button -->
      <button class="open-btn" @click="emit('open-quote', props.result.quote_number)">
        <ExternalLink :size="ICON_SIZE.STANDARD" />
        Otevřít nabídku
      </button>
    </div>
  </div>
</template>

<style scoped>
.progress-step {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-4);
}

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--space-3);
  color: var(--text-secondary);
}

.spin-icon {
  color: var(--brand);
  animation: spin 0.8s linear infinite;
}

.loading h3 {
  margin: 0;
  color: var(--text-primary);
}

.hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0;
  text-align: center;
}

/* Result */
.result {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.result-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
}

.success-icon {
  color: var(--color-success);
}

.result-header h2 {
  margin: 0;
  color: var(--text-primary);
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.stat-total .stat-value {
  color: var(--brand);
}

/* Parts list */
.parts-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.part-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
}

.part-check {
  color: var(--color-success);
  flex-shrink: 0;
}

.part-number {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--text-primary);
  white-space: nowrap;
}

.part-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.part-price {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Badges */

.badge-new { background: rgba(153,27,27,0.15); color: var(--brand-text); }
.badge-existing { background: rgba(115,115,115,0.15); color: var(--text-secondary); }
.badge-drawing { background: rgba(34,197,94,0.15); color: var(--color-success); }
.badge-tech { background: rgba(168,85,247,0.15); color: rgb(168, 85, 247); }

/* Warnings */
.warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.warning-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: rgba(234, 179, 8, 0.1);
  border-left: 3px solid var(--palette-warning);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* Open button */
.open-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.open-btn:hover { background: var(--brand-subtle); border-color: var(--brand); color: var(--brand-text); }

</style>
