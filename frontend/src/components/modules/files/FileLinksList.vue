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
  padding: 12px;
  border-bottom: 1px solid var(--b2);
}

.file-links-list h4 {
  margin: 0 0 var(--pad) 0;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.links-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.link-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.link-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.link-entity {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
}

.primary-star {
  color: var(--warn);
}

.link-revision {
  padding: 4px 6px;
  background: var(--base);
  border-radius: var(--rs);
  font-size: var(--fs);
  color: var(--t3);
}

.no-links {
  padding: 12px;
  text-align: center;
  color: var(--t3);
  font-size: var(--fs);
}

</style>
