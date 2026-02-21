<script setup lang="ts">
/**
 * QuoteSnapshotTab — Tab 2: Snapshot
 * Shows snapshot metadata (sent_at, approved_at, rejected_at, version).
 * Draft quotes display a placeholder notice.
 */
import type { QuoteWithItems } from '@/types/quote'
import { formatDate } from '@/utils/formatters'

defineProps<{
  quote: QuoteWithItems
}>()
</script>

<template>
  <div class="snapshot-tab">
    <div v-if="quote.status === 'draft'" class="snapshot-empty">
      <p>Snapshot je dostupný až po odeslání nabídky</p>
    </div>

    <div v-else class="snapshot-content">
      <h4>Metadata</h4>
      <div class="snapshot-meta">
        <div class="meta-item">
          <span class="meta-label">Odesláno:</span>
          <span class="meta-value">{{ formatDate(quote.sent_at) }}</span>
        </div>
        <div v-if="quote.approved_at" class="meta-item">
          <span class="meta-label">Schváleno:</span>
          <span class="meta-value">{{ formatDate(quote.approved_at) }}</span>
        </div>
        <div v-if="quote.rejected_at" class="meta-item">
          <span class="meta-label">Odmítnuto:</span>
          <span class="meta-value">{{ formatDate(quote.rejected_at) }}</span>
        </div>
      </div>

      <h4>Verze</h4>
      <div class="snapshot-version">
        <span>Verze: {{ quote.version }}</span>
      </div>

      <div class="snapshot-info">
        <p>Snapshot dat je vytvořen při odeslání nabídky a zachycuje aktuální stav materiálů, cen a operací.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.snapshot-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.snapshot-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-secondary);
}

.snapshot-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.snapshot-content h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.snapshot-meta,
.snapshot-version {
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.snapshot-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-item {
  display: flex;
  justify-content: space-between;
}

.meta-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.meta-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.snapshot-version {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.snapshot-info {
  padding: var(--space-3);
  background: rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-strong);
}

.snapshot-info p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-body);
}
</style>
