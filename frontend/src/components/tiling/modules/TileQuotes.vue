<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { ContextGroup } from '@/types/workspace'
import type { QuoteDetail, QuoteListItem } from '@/types/quote'
import { useSplitLayoutStore } from '@/stores/splitLayout'
import { useSplitResize } from '@/composables/useSplitResize'
import QuoteListPanel from './quotes/QuoteListPanel.vue'
import QuoteDetailPanel from './quotes/QuoteDetailPanel.vue'
import QuoteNewDialog from './quotes/QuoteNewDialog.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const splitLayout = useSplitLayoutStore()
const layoutMode = computed(() => splitLayout.getMode(props.leafId, 'quotes'))

onUnmounted(() => splitLayout.cleanup(props.leafId))

const selectedQuoteNumber = ref<string | null>(null)
const showNewDialog = ref(false)

// ── Resize ──
const containerRef = ref<HTMLElement | null>(null)
const { splitPct, isDragging, startResize } = useSplitResize(layoutMode, containerRef)

const listRef = ref<InstanceType<typeof QuoteListPanel> | null>(null)

onMounted(() => listRef.value?.load())

function onListLoaded(items: QuoteListItem[]) {
  if (!selectedQuoteNumber.value && items[0]) {
    selectedQuoteNumber.value = items[0].quote_number
  }
}

function onQuoteCreated(quote: QuoteDetail) {
  selectedQuoteNumber.value = quote.quote_number
  listRef.value?.load()
}

function onDetailReload() {
  listRef.value?.load()
}
</script>

<template>
  <div ref="containerRef" class="wquo-root" :class="layoutMode">
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
        @loaded="onListLoaded"
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
