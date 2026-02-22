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
  gap: 20px;
  max-width: 800px;
  margin: 0 auto;
  padding: 12px;
}

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--pad);
  color: var(--t3);
}

.spin-icon {
  color: var(--red);
  animation: spin 0.8s linear infinite;
}

.loading h3 {
  margin: 0;
  color: var(--t1);
}

.hint {
  font-size: var(--fs);
  color: var(--t3);
  margin: 0;
  text-align: center;
}

/* Result */
.result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--pad);
  text-align: center;
}

.success-icon {
  color: var(--ok);
}

.result-header h2 {
  margin: 0;
  color: var(--t1);
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--pad);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--pad);
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--t1);
  font-family: var(--mono);
}

.stat-label {
  font-size: var(--fs);
  color: var(--t3);
}

.stat-total .stat-value {
  color: var(--red);
}

/* Parts list */
.parts-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.part-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  background: var(--raised);
  border-radius: var(--r);
}

.part-check {
  color: var(--ok);
  flex-shrink: 0;
}

.part-number {
  font-family: var(--mono);
  font-weight: 600;
  font-size: var(--fs);
  color: var(--t1);
  white-space: nowrap;
}

.part-name {
  flex: 1;
  font-size: var(--fs);
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.part-price {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
}

/* Badges */

.badge-new { background: var(--raised); color: rgba(229, 57, 53, 0.7); }
.badge-existing { background: var(--raised); color: var(--t3); }
.badge-drawing { background: var(--raised); color: var(--ok); }
.badge-tech { background: var(--raised); color: var(--t3); }

/* Warnings */
.warnings {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  background: rgba(251,191,36,0.1);
  border-left: 3px solid var(--warn);
  border-radius: var(--rs);
  font-size: var(--fs);
  color: var(--t3);
}

/* Open button */
.open-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: var(--pad);
  border: 1px solid var(--b2);
  border-radius: 8px;
  background: transparent;
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.open-btn:hover { background: var(--red-10); border-color: var(--red); color: rgba(229, 57, 53, 0.7); }

</style>
