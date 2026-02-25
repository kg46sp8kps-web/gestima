<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import type { ContextGroup } from '@/types/workspace'
import type { QuoteDetail } from '@/types/quote'
import { useQuoteLayoutStore } from '@/stores/quoteLayout'
import QuoteListPanel from './quotes/QuoteListPanel.vue'
import QuoteDetailPanel from './quotes/QuoteDetailPanel.vue'
import QuoteNewDialog from './quotes/QuoteNewDialog.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const layoutStore = useQuoteLayoutStore()
const layoutMode = computed(() => layoutStore.getMode(props.leafId))

onUnmounted(() => layoutStore.cleanup(props.leafId))

const selectedQuoteNumber = ref<string | null>(null)
const showNewDialog = ref(false)

// Split panel resize — works for both axes
const splitPct = ref(40) // percent
const isDragging = ref(false)

// Reset split when layout changes
watch(layoutMode, () => { splitPct.value = 40 })

function startResize(e: MouseEvent) {
  isDragging.value = true
  const startPct = splitPct.value
  const startPos = layoutMode.value === 'vertical' ? e.clientX : e.clientY

  function onMove(ev: MouseEvent) {
    const root = document.querySelector('.wquo-root') as HTMLElement | null
    if (!root) return
    const total = layoutMode.value === 'vertical' ? root.offsetWidth : root.offsetHeight
    if (total === 0) return
    const pos = layoutMode.value === 'vertical' ? ev.clientX : ev.clientY
    const delta = ((pos - startPos) / total) * 100
    splitPct.value = Math.min(75, Math.max(20, startPct + delta))
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
  <div class="wquo-root" :class="layoutMode">
    <!-- List panel -->
    <div
      class="wquo-list-wrap"
      :style="selectedQuoteNumber
        ? layoutMode === 'vertical'
          ? { width: `${splitPct}%` }
          : { height: `${splitPct}%` }
        : {}"
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
      :class="['resize-handle', layoutMode, { dragging: isDragging }]"
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

.wquo-root.vertical  { flex-direction: row; }
.wquo-root.horizontal { flex-direction: column; }

.wquo-list-wrap {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  flex: 1;
}
.wquo-root.vertical   .wquo-list-wrap[style] { flex: none; }
.wquo-root.horizontal .wquo-list-wrap[style] { flex: none; }

.wquo-detail-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.wquo-root.vertical   .wquo-detail-wrap { border-left: 1px solid var(--b1); }
.wquo-root.horizontal .wquo-detail-wrap { border-top: 1px solid var(--b1); }

.resize-handle {
  flex-shrink: 0;
  background: transparent;
  transition: background 120ms var(--ease);
}
.resize-handle.vertical   { width: 5px; cursor: col-resize; }
.resize-handle.horizontal { height: 5px; cursor: row-resize; }
.resize-handle:hover,
.resize-handle.dragging { background: var(--b2); }
</style>
