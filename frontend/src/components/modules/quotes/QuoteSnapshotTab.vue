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
  gap: 12px;
}

.snapshot-empty {
  text-align: center;
  padding: 24px;
  color: var(--t3);
}

.snapshot-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.snapshot-content h4 {
  margin: 0 0 6px 0;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.snapshot-meta,
.snapshot-version {
  padding: var(--pad);
  background: var(--raised);
  border-radius: var(--r);
  border: 1px solid var(--b2);
}

.snapshot-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
}

.meta-label {
  font-size: var(--fs);
  color: var(--t3);
}

.meta-value {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 600;
}

.snapshot-version {
  font-size: var(--fs);
  color: var(--t1);
}

.snapshot-info {
  padding: var(--pad);
  background: var(--b1);
  border-radius: var(--r);
  border: 1px solid var(--b3);
}

.snapshot-info p {
  margin: 0;
  font-size: var(--fs);
  color: var(--t2);
}
</style>
