<script setup lang="ts">
import { ref } from 'vue'
import type { ContextGroup } from '@/types/workspace'
import type { QuoteDetail } from '@/types/quote'
import QuoteListPanel from './quotes/QuoteListPanel.vue'
import QuoteDetailPanel from './quotes/QuoteDetailPanel.vue'
import QuoteNewDialog from './quotes/QuoteNewDialog.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const selectedQuoteNumber = ref<string | null>(null)
const showNewDialog = ref(false)

// Split panel resize
const listWidth = ref(40) // percent
const isDragging = ref(false)
let startX = 0
let startWidth = 0

function startResize(e: MouseEvent) {
  isDragging.value = true
  startX = e.clientX
  startWidth = listWidth.value

  function onMove(ev: MouseEvent) {
    const root = document.querySelector('.wquo-root') as HTMLElement | null
    if (!root) return
    const totalWidth = root.offsetWidth
    if (totalWidth === 0) return
    const delta = ((ev.clientX - startX) / totalWidth) * 100
    listWidth.value = Math.min(75, Math.max(20, startWidth + delta))
  }

  function onUp() {
    isDragging.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

const listRef = ref<InstanceType<typeof QuoteListPanel> | null>(null)

function onQuoteCreated(quote: QuoteDetail) {
  selectedQuoteNumber.value = quote.quote_number
  listRef.value?.load()
}

function onDetailReload() {
  listRef.value?.load()
}
</script>

<template>
  <div class="wquo-root">
    <!-- List panel -->
    <div
      class="wquo-list-wrap"
      :style="selectedQuoteNumber ? { width: `${listWidth}%` } : { flex: '1' }"
    >
      <QuoteListPanel
        ref="listRef"
        :selected-quote-number="selectedQuoteNumber"
        @select="selectedQuoteNumber = $event"
        @new-quote="showNewDialog = true"
      />
    </div>

    <!-- Resize handle (only when detail is open) -->
    <div
      v-if="selectedQuoteNumber"
      :class="['resize-handle', { dragging: isDragging }]"
      @mousedown.prevent="startResize"
    />

    <!-- Detail panel -->
    <div v-if="selectedQuoteNumber" class="wquo-detail-wrap">
      <QuoteDetailPanel
        :quote-number="selectedQuoteNumber"
        :leaf-id="props.leafId"
        :ctx="props.ctx"
        @reload="onDetailReload"
      />
    </div>

    <!-- New quote dialog -->
    <QuoteNewDialog
      v-model="showNewDialog"
      @created="onQuoteCreated"
    />
  </div>
</template>

<style scoped>
.wquo-root {
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.wquo-list-wrap {
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.wquo-detail-wrap {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--b1);
}

/* ─── Resize handle ─── */
.resize-handle {
  width: 5px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  transition: background 120ms var(--ease);
  position: relative;
  z-index: 1;
}
.resize-handle:hover,
.resize-handle.dragging {
  background: var(--b2);
}
</style>
