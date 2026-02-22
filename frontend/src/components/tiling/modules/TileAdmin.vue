<script setup lang="ts">
import { ref } from 'vue'
import type { ContextGroup } from '@/types/workspace'
import TileAdminUsers from './admin/TileAdminUsers.vue'
import TileAdminNorms from './admin/TileAdminNorms.vue'
import TileAdminMatGroups from './admin/TileAdminMatGroups.vue'
import TileAdminPriceCategories from './admin/TileAdminPriceCategories.vue'
import TileAdminWorkCenters from './admin/TileAdminWorkCenters.vue'
import TileAdminCuttingConditions from './admin/TileAdminCuttingConditions.vue'
import TileAdminInfor from './admin/TileAdminInfor.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

type AdminTab = 'users' | 'norms' | 'mat-groups' | 'price-cats' | 'work-centers' | 'cutting' | 'infor'

const activeTab = ref<AdminTab>('users')

const TABS: { id: AdminTab; label: string }[] = [
  { id: 'users',        label: 'Uživatelé' },
  { id: 'norms',        label: 'Mat. normy' },
  { id: 'mat-groups',   label: 'Mat. skupiny' },
  { id: 'price-cats',   label: 'Cen. kategorie' },
  { id: 'work-centers', label: 'Pracoviště' },
  { id: 'cutting',      label: 'Řezné podmínky' },
  { id: 'infor',        label: 'Infor' },
]
</script>

<template>
  <div class="wadm">
    <!-- Tab strip -->
    <div class="ptabs">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        :class="['ptab', activeTab === tab.id ? 'on' : '']"
        :data-testid="`admin-tab-${tab.id}`"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab content — KeepAlive preserves state when switching -->
    <KeepAlive>
      <TileAdminUsers        v-if="activeTab === 'users'"        :key="'users'" />
      <TileAdminNorms        v-else-if="activeTab === 'norms'"   :key="'norms'" />
      <TileAdminMatGroups    v-else-if="activeTab === 'mat-groups'" :key="'mat-groups'" />
      <TileAdminPriceCategories v-else-if="activeTab === 'price-cats'" :key="'price-cats'" />
      <TileAdminWorkCenters  v-else-if="activeTab === 'work-centers'" :key="'work-centers'" />
      <TileAdminCuttingConditions v-else-if="activeTab === 'cutting'" :key="'cutting'" />
      <TileAdminInfor        v-else-if="activeTab === 'infor'"   :key="'infor'" />
    </KeepAlive>
  </div>
</template>

<style scoped>
.wadm {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.ptabs {
  display: flex;
  gap: 1px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
  background: rgba(255,255,255,0.015);
  overflow-x: auto;
  scrollbar-width: none;
}
.ptabs::-webkit-scrollbar { display: none; }

.ptab {
  padding: 3px 7px;
  font-size: 10.5px;
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  font-family: var(--font);
  white-space: nowrap;
  flex-shrink: 0;
}
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
</style>
