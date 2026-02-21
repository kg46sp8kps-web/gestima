<script setup lang="ts">
/**
 * File Links List - Seznam vazeb souboru na entity
 */

import type { FileLink } from '@/types/file'
import { Star, X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  links: FileLink[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  unlink: [link: FileLink]
}>()
</script>

<template>
  <div class="file-links-list">
    <h4>Vazby</h4>

    <!-- Links list -->
    <div v-if="links.length > 0" class="links-list">
      <div
        v-for="link in links"
        :key="link.id"
        class="link-item"
      >
        <div class="link-info">
          <span class="link-entity">{{ link.entity_name || `${link.entity_type} #${link.entity_id}` }}</span>
          <Star v-if="link.is_primary" :size="ICON_SIZE.SMALL" class="primary-star" />
          <span v-if="link.revision" class="link-revision">Rev {{ link.revision }}</span>
        </div>
        <button
          class="icon-btn icon-btn-danger"
          @click="emit('unlink', link)"
          title="Odpojit vazbu"
        >
          <X :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </div>

    <!-- No links -->
    <div v-else class="no-links">
      <p>Žádné vazby</p>
    </div>
  </div>
</template>

<style scoped>
.file-links-list {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.file-links-list h4 {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.links-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.link-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.link-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.link-entity {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.primary-star {
  color: var(--color-warning);
}

.link-revision {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-base);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.no-links {
  padding: var(--space-4);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

</style>
