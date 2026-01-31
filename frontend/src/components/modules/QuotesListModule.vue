<script setup lang="ts">
/**
 * Quotes List Module - Split-pane coordinator
 *
 * LEFT: QuoteListPanel (320px - standalone only, NO linking)
 * RIGHT: QuoteHeader + QuoteDetailPanel
 */

import { ref, onMounted } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import type { Quote, QuoteWithItems } from '@/types/quote'

import QuoteListPanel from './quotes/QuoteListPanel.vue'
import QuoteHeader from './quotes/QuoteHeader.vue'
import QuoteDetailPanel from './quotes/QuoteDetailPanel.vue'

interface Props {
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inline: false
})

const quotesStore = useQuotesStore()
const selectedQuote = ref<QuoteWithItems | null>(null)

async function handleSelectQuote(quote: Quote) {
  // Fetch full quote with items
  await quotesStore.fetchQuote(quote.quote_number)
  selectedQuote.value = quotesStore.currentQuote
}

function handleQuoteUpdated() {
  quotesStore.fetchQuotes()
  if (selectedQuote.value) {
    quotesStore.fetchQuote(selectedQuote.value.quote_number)
      .then((quote) => {
        selectedQuote.value = quote
      })
  }
}

function handleQuoteDeleted() {
  selectedQuote.value = null
  quotesStore.fetchQuotes()
}

onMounted(() => {
  quotesStore.fetchQuotes()
})
</script>

<template>
  <div class="split-layout">
    <!-- LEFT PANEL: Quote List (320px) -->
    <div class="left-panel">
      <QuoteListPanel
        :selected-quote="selectedQuote"
        @select-quote="handleSelectQuote"
      />
    </div>

    <!-- RIGHT PANEL: Header + Detail -->
    <div class="right-panel">
      <QuoteHeader
        :quote="selectedQuote"
        @updated="handleQuoteUpdated"
        @deleted="handleQuoteDeleted"
      />
      <QuoteDetailPanel
        :quote="selectedQuote"
        @updated="handleQuoteUpdated"
        @deleted="handleQuoteDeleted"
      />
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

/* === LEFT PANEL === */
.left-panel {
  width: 320px;
  min-width: 320px;
  padding: var(--space-3);
  height: 100%;
  border-right: 1px solid var(--border-default);
}

/* === RIGHT PANEL === */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
