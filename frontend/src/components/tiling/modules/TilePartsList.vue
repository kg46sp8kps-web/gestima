<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, RotateCw, Search, X } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import type { ContextGroup } from '@/types/workspace'
import type { Part, PartCreate } from '@/types/part'
import { partStatusLabel } from '@/utils/partStatus'
import Spinner from '@/components/ui/Spinner.vue'
import Modal from '@/components/ui/Modal.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import { ICON_SIZE, ICON_SIZE_SM } from '@/config/design'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ui = useUiStore()

const searchVal = ref('')
const showCreate = ref(false)
const createName = ref('')
const createArticle = ref('')
const creating = ref(false)

let searchTimer: ReturnType<typeof setTimeout>
function onSearchInput(val: string) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    parts.search = val
    parts.fetchAll()
  }, 300)
}

const filtered = computed(() => {
  const q = searchVal.value.toLowerCase().trim()
  if (!q) return parts.items
  return parts.items.filter(p =>
    p.part_number.toLowerCase().includes(q) ||
    (p.name ?? '').toLowerCase().includes(q) ||
    (p.article_number ?? '').toLowerCase().includes(q) ||
    (p.drawing_number ?? '').toLowerCase().includes(q)
  )
})

const focused = computed(() => parts.getFocusedPartNumber(props.ctx))

function selectPart(p: Part) {
  parts.focusPart(p.part_number, props.ctx)
}

function statusClass(status: string): string {
  switch (status) {
    case 'active': return 'badge-dot-ok'
    case 'archived': return 'badge-dot-neutral'
    case 'draft': return 'badge-dot-warn'
    case 'quote': return 'badge-dot-brand'
    default: return 'badge-dot-neutral'
  }
}

async function handleCreate() {
  if (!createName.value.trim() && !createArticle.value.trim()) {
    ui.showError('Zadejte alespoň název nebo číslo artiklu')
    return
  }
  creating.value = true
  const payload: PartCreate = {
    name: createName.value.trim(),
    article_number: createArticle.value.trim(),
  }
  const part = await parts.createPart(payload)
  creating.value = false
  if (part) {
    showCreate.value = false
    createName.value = ''
    createArticle.value = ''
    parts.focusPart(part.part_number, props.ctx)
  }
}

function openCreate() {
  showCreate.value = true
}

onMounted(() => {
  if (!parts.hasParts) {
    parts.fetchAll()
  }
})

watch(() => parts.statusFilter, () => {
  parts.fetchAll()
})
</script>

<template>
  <div class="plist">
    <!-- Toolbar -->
    <div class="plist-toolbar">
      <div class="plist-search-wrap">
        <Search :size="ICON_SIZE_SM" class="plist-search-icon" />
        <input
          v-model="searchVal"
          class="plist-search"
          placeholder="Hledat díl..."
          data-testid="parts-search"
          @input="onSearchInput(searchVal)"
        />
        <button
          v-if="searchVal"
          class="plist-clear"
          data-testid="parts-search-clear"
          @click="searchVal = ''; parts.search = ''; parts.fetchAll()"
        >
          <X :size="ICON_SIZE_SM" />
        </button>
      </div>

      <div class="plist-actions">
        <button
          class="icon-btn"
          title="Obnovit"
          data-testid="parts-refresh"
          @click="parts.fetchAll()"
        >
          <RotateCw :size="ICON_SIZE_SM" />
        </button>
        <button
          class="icon-btn icon-btn-brand"
          title="Nový díl"
          data-testid="parts-create"
          @click="openCreate"
        >
          <Plus :size="ICON_SIZE" />
        </button>
      </div>
    </div>

    <!-- Status filter chips -->
    <div class="plist-chips">
      <button
        :class="['plist-chip', parts.statusFilter === '' ? 'active' : '']"
        data-testid="filter-all"
        @click="parts.statusFilter = ''"
      >
        Vše
      </button>
      <button
        :class="['plist-chip', parts.statusFilter === 'active' ? 'active' : '']"
        data-testid="filter-active"
        @click="parts.statusFilter = 'active'"
      >
        Aktivní
      </button>
      <button
        :class="['plist-chip', parts.statusFilter === 'draft' ? 'active' : '']"
        data-testid="filter-draft"
        @click="parts.statusFilter = 'draft'"
      >
        Rozpr.
      </button>
      <button
        :class="['plist-chip', parts.statusFilter === 'archived' ? 'active' : '']"
        data-testid="filter-archived"
        @click="parts.statusFilter = 'archived'"
      >
        Arch.
      </button>
    </div>

    <!-- Loading -->
    <div v-if="parts.loading" class="plist-state">
      <Spinner size="sm" text="Načítám díly..." />
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="plist-state plist-empty">
      {{ searchVal ? 'Žádný díl nevyhovuje hledání' : 'Žádné díly' }}
    </div>

    <!-- List -->
    <div v-else class="plist-list">
      <button
        v-for="p in filtered"
        :key="p.part_number"
        :class="['prow', { 'prow-active': focused === p.part_number }]"
        :data-testid="`part-row-${p.part_number}`"
        @click="selectPart(p)"
      >
        <div class="prow-num">{{ p.part_number }}</div>
        <div class="prow-info">
          <div class="prow-name">{{ p.name || p.article_number || '—' }}</div>
          <div v-if="p.article_number && p.name" class="prow-art">{{ p.article_number }}</div>
        </div>
        <div class="prow-badge">
          <span class="badge">
            <span :class="['badge-dot', statusClass(p.status)]" />
            {{ partStatusLabel(p.status) }}
          </span>
        </div>
      </button>
    </div>

    <!-- Count -->
    <div v-if="!parts.loading && filtered.length" class="plist-footer">
      {{ filtered.length }} / {{ parts.total }} dílů
    </div>

    <!-- Create modal -->
    <Modal v-model="showCreate" title="Nový díl" size="sm">
      <div class="create-form">
        <Input
          v-model="createName"
          label="Název dílu"
          placeholder="např. Hřídel frézovaná"
          data-testid="create-part-name"
        />
        <Input
          v-model="createArticle"
          label="Číslo artiklu"
          placeholder="např. ART-12345"
          data-testid="create-part-article"
        />
      </div>
      <template #footer>
        <Button variant="ghost" @click="showCreate = false">Zrušit</Button>
        <Button
          variant="primary"
          :loading="creating"
          data-testid="create-part-submit"
          @click="handleCreate"
        >
          Vytvořit díl
        </Button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.plist {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  container-type: inline-size;
}

/* ─── Toolbar ─── */
.plist-toolbar {
  display: flex;
  align-items: center;
  gap: var(--gap);
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

.plist-search-wrap {
  flex: 1;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
}
.plist-search-icon {
  position: absolute;
  left: 6px;
  color: var(--t4);
  pointer-events: none;
  flex-shrink: 0;
}
.plist-search {
  width: 100%;
  background: var(--raised);
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  padding: 4px 24px 4px 24px;
  font-size: var(--fs);
  font-family: var(--font);
  color: var(--t1);
  outline: none;
  transition: border-color 100ms var(--ease);
}
.plist-search::placeholder { color: var(--t4); }
.plist-search:focus { border-color: var(--b3); }
.plist-clear {
  position: absolute;
  right: 4px;
  background: none;
  border: none;
  color: var(--t4);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 2px;
  border-radius: var(--rs);
}
.plist-clear:hover { color: var(--t2); }

.plist-actions {
  display: flex;
  gap: var(--gap);
  flex-shrink: 0;
}

/* ─── Status chips ─── */
.plist-chips {
  display: flex;
  gap: 2px;
  padding: 4px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.plist-chip {
  background: none;
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  padding: 2px 7px;
  font-size: var(--fsl);
  font-family: var(--font);
  color: var(--t3);
  cursor: pointer;
  transition: all 80ms var(--ease);
}
.plist-chip:hover { border-color: var(--b2); color: var(--t2); }
.plist-chip.active {
  background: var(--raised);
  border-color: var(--b3);
  color: var(--t1);
}

/* ─── State ─── */
.plist-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.plist-empty { color: var(--t4); font-size: var(--fs); }

/* ─── List ─── */
.plist-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Part row ─── */
.prow {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  width: 100%;
  background: none;
  border: none;
  border-bottom: 1px solid var(--b1);
  cursor: pointer;
  text-align: left;
  transition: background 60ms;
  color: inherit;
}
.prow:last-child { border-bottom: none; }
.prow:hover { background: rgba(255,255,255,0.03); }
.prow-active { background: rgba(255,255,255,0.06); }
.prow-active:hover { background: rgba(255,255,255,0.08); }

.prow-num {
  font-family: var(--mono);
  font-size: var(--fsl);
  color: var(--t3);
  flex-shrink: 0;
  width: 72px;
}
.prow-info {
  flex: 1;
  min-width: 0;
}
.prow-name {
  font-size: var(--fs);
  color: var(--t1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.prow-art {
  font-size: var(--fsl);
  color: var(--t4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.prow-badge { flex-shrink: 0; }

/* ─── Footer ─── */
.plist-footer {
  padding: 4px var(--pad);
  font-size: var(--fsl);
  color: var(--t4);
  border-top: 1px solid var(--b1);
  flex-shrink: 0;
  text-align: right;
}

/* ─── Create form ─── */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
