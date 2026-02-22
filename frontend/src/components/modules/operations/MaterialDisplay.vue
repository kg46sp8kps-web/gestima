<template>
  <div class="space-y-2">
    <!-- Inline material row - VÝRAZNĚJŠÍ BACKGROUND -->
    <div
      class="flex items-center gap-2 h-8 px-3 border rounded
             bg-[var(--raised)]
             border-[var(--b2)]"
    >
      <span class="flex-1 text-xs truncate text-[var(--t1)]">
        <span class="font-medium">{{ material.item_code || material.w_nr || 'Materiál' }}</span>
        <span class="mx-1 text-[var(--t3)]">&middot;</span>
        <span class="text-[var(--t3)]">{{ material.item_description || '' }}</span>
        <span v-if="dimensionText !== '—'" class="text-[var(--t3)]">
          <span class="mx-1">&middot;</span>{{ dimensionText }}
        </span>
      </span>
      <span
        v-if="material.match_type"
        class="px-1.5 py-0.5 text-[10px] rounded-full shrink-0"
        :class="matchTypeBadgeClass(material.match_type)"
      >
        {{ material.match_type }}
      </span>
      <button
        class="p-0.5 rounded hover:bg-[var(--b1)] text-[var(--t3)] shrink-0"
        title="Zobrazit detaily"
        @click="detailsOpen = !detailsOpen"
      >
        <component
          :is="detailsOpen ? ChevronUp : ChevronDown"
          :size="ICON_SIZE.SMALL"
        />
      </button>
      <button
        class="p-0.5 rounded hover:bg-[var(--b1)] text-[var(--t3)] shrink-0"
        title="Odebrat materiál"
        @click="emit('remove')"
      >
        <X :size="ICON_SIZE.SMALL" />
      </button>
    </div>

    <!-- Collapsible READONLY Details -->
    <div
      v-if="detailsOpen"
      class="border rounded p-3
             bg-[var(--surface)]
             border-[var(--b2)]"
    >
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span class="text-[var(--t3)]">W.Nr:</span>
          <span class="ml-1 text-[var(--t1)]">{{ material.w_nr || '—' }}</span>
        </div>
        <div>
          <span class="text-[var(--t3)]">Skupina:</span>
          <span class="ml-1 text-[var(--t1)]">{{ material.material_group || '—' }}</span>
        </div>
        <div>
          <span class="text-[var(--t3)]">Tvar:</span>
          <span class="ml-1 text-[var(--t1)]">{{ material.shape || '—' }}</span>
        </div>
        <div>
          <span class="text-[var(--t3)]">Rozměry:</span>
          <span class="ml-1 text-[var(--t1)]">{{ dimensionText }}</span>
        </div>
        <div>
          <span class="text-[var(--t3)]">Cenová kategorie:</span>
          <span class="ml-1 text-[var(--t1)]">{{ material.price_category || '—' }}</span>
        </div>
        <div>
          <span class="text-[var(--t3)]">Cena/kg:</span>
          <span class="ml-1 text-[var(--t1)]">
            {{ material.price_per_kg ? `${material.price_per_kg} Kč` : '—' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronUp, ChevronDown, X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { ParsedMaterial } from '@/types/material'
import { formatDimensions, matchTypeBadgeClass } from './materialConstants'

const props = defineProps<{ material: ParsedMaterial }>()
const emit = defineEmits<{ remove: [] }>()

const detailsOpen = ref(false)
const dimensionText = computed(() => formatDimensions(props.material))
</script>
