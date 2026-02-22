<script setup lang="ts">
import { computed } from 'vue'
import { usePartsStore } from '@/stores/parts'
import type { ContextGroup } from '@/types/workspace'
import type { Part } from '@/types/part'
import { partStatusLabel, partSourceLabel } from '@/utils/partStatus'
import { formatDate } from '@/utils/formatters'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()

const part = computed<Part | null>(() => parts.getFocusedPart(props.ctx))

function statusBadgeDot(status: string): string {
  switch (status) {
    case 'active': return 'badge-dot-ok'
    case 'archived': return 'badge-dot-neutral'
    case 'draft': return 'badge-dot-warn'
    case 'quote': return 'badge-dot-brand'
    default: return 'badge-dot-neutral'
  }
}

function sourceBadgeDot(source: string): string {
  switch (source) {
    case 'infor_import': return 'badge-dot-brand'
    case 'quote_request': return 'badge-dot-warn'
    default: return 'badge-dot-neutral'
  }
}
</script>

<template>
  <div class="wdet">
    <!-- Empty state -->
    <div v-if="!part" class="wdet-empty">
      <div class="wdet-empty-dot" />
      <div class="wdet-empty-label">Vyberte díl ze seznamu</div>
    </div>

    <!-- Part detail -->
    <div v-else class="wdet-content">
      <!-- Header -->
      <div class="wdet-header">
        <div class="wdet-pnum">{{ part.part_number }}</div>
        <div class="wdet-badges">
          <span class="badge" data-testid="part-status-badge">
            <span :class="['badge-dot', statusBadgeDot(part.status)]" />
            {{ partStatusLabel(part.status) }}
          </span>
          <span v-if="part.source !== 'manual'" class="badge" data-testid="part-source-badge">
            <span :class="['badge-dot', sourceBadgeDot(part.source)]" />
            {{ partSourceLabel(part.source) }}
          </span>
        </div>
      </div>

      <!-- Name -->
      <div class="wdet-name">{{ part.name || '—' }}</div>

      <!-- Fields grid -->
      <div class="wdet-fields">
        <div class="wdet-field">
          <div class="wdet-field-label">Číslo artiklu</div>
          <div class="wdet-field-value mono">{{ part.article_number || '—' }}</div>
        </div>
        <div class="wdet-field">
          <div class="wdet-field-label">Číslo výkresu</div>
          <div class="wdet-field-value mono">{{ part.drawing_number || '—' }}</div>
        </div>
        <div v-if="part.revision" class="wdet-field">
          <div class="wdet-field-label">Revize</div>
          <div class="wdet-field-value mono">{{ part.revision }}</div>
        </div>
        <div v-if="part.customer_revision" class="wdet-field">
          <div class="wdet-field-label">Rev. zákazníka</div>
          <div class="wdet-field-value mono">{{ part.customer_revision }}</div>
        </div>
        <div v-if="part.length > 0" class="wdet-field">
          <div class="wdet-field-label">Délka</div>
          <div class="wdet-field-value mono">{{ part.length }} mm</div>
        </div>
        <div class="wdet-field">
          <div class="wdet-field-label">Vytvořen</div>
          <div class="wdet-field-value">
            {{ formatDate(part.created_at) }}
            <span v-if="part.created_by_name" class="wdet-by">{{ part.created_by_name }}</span>
          </div>
        </div>
        <div class="wdet-field">
          <div class="wdet-field-label">Upraven</div>
          <div class="wdet-field-value">{{ formatDate(part.updated_at) }}</div>
        </div>
      </div>

      <!-- Notes -->
      <div v-if="part.notes" class="wdet-notes">
        <div class="wdet-notes-label">Poznámky</div>
        <div class="wdet-notes-text">{{ part.notes }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wdet {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  container-type: inline-size;
}

/* ─── Empty ─── */
.wdet-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.wdet-empty-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--b2);
}
.wdet-empty-label {
  font-size: var(--fs);
}

/* ─── Content ─── */
.wdet-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ─── Header ─── */
.wdet-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.wdet-pnum {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--t1);
  letter-spacing: 0.04em;
}
.wdet-badges {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* ─── Name ─── */
.wdet-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--t1);
  line-height: 1.3;
}

/* ─── Fields ─── */
.wdet-fields {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--b1);
  border-radius: var(--r);
  overflow: hidden;
}
.wdet-field {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 5px var(--pad);
  background: var(--raised);
}
.wdet-field:first-child { border-radius: var(--r) var(--r) 0 0; }
.wdet-field:last-child { border-radius: 0 0 var(--r) var(--r); }
.wdet-field:only-child { border-radius: var(--r); }
.wdet-field-label {
  font-size: var(--fsl);
  color: var(--t4);
  white-space: nowrap;
  width: 100px;
  flex-shrink: 0;
}
.wdet-field-value {
  font-size: var(--fs);
  color: var(--t2);
  flex: 1;
  min-width: 0;
}
.wdet-field-value.mono { font-family: var(--mono); }
.wdet-by {
  font-size: var(--fsl);
  color: var(--t4);
  margin-left: 6px;
}

/* ─── Notes ─── */
.wdet-notes {
  background: var(--raised);
  border-radius: var(--r);
  padding: var(--pad);
}
.wdet-notes-label {
  font-size: var(--fsl);
  color: var(--t4);
  margin-bottom: 4px;
}
.wdet-notes-text {
  font-size: var(--fs);
  color: var(--t2);
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>
