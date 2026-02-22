<script setup lang="ts">
/**
 * Partners List Module - Split-pane coordinator
 *
 * LEFT: PartnerListPanel (320px - standalone only, NO linking)
 * RIGHT: PartnerHeader + PartnerDetailPanel
 */

import { ref, onMounted } from 'vue'
import { usePartnersStore } from '@/stores/partners'
import type { Partner } from '@/types/partner'

import PartnerListPanel from './partners/PartnerListPanel.vue'
import PartnerHeader from './partners/PartnerHeader.vue'
import PartnerDetailPanel from './partners/PartnerDetailPanel.vue'

interface Props {
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inline: false
})

const partnersStore = usePartnersStore()
const selectedPartner = ref<Partner | null>(null)

function handleSelectPartner(partner: Partner) {
  selectedPartner.value = partner
}

function handlePartnerUpdated() {
  // Refresh list after update
  partnersStore.fetchPartners()
}

function handlePartnerDeleted() {
  selectedPartner.value = null
  partnersStore.fetchPartners()
}

onMounted(() => {
  if (!partnersStore.loaded) {
    partnersStore.fetchPartners()
  }
})
</script>

<template>
  <div class="split-layout">
    <!-- LEFT PANEL: Partner List (320px) -->
    <div class="left-panel">
      <PartnerListPanel
        :selected-partner="selectedPartner"
        @select-partner="handleSelectPartner"
      />
    </div>

    <!-- RIGHT PANEL: Header + Detail -->
    <div class="right-panel">
      <PartnerHeader :partner="selectedPartner" />
      <PartnerDetailPanel
        :partner="selectedPartner"
        @updated="handlePartnerUpdated"
        @deleted="handlePartnerDeleted"
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
  padding: var(--pad);
  height: 100%;
  border-right: 1px solid var(--b2);
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
