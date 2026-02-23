<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import type { ContextGroup } from '@/types/workspace'
import type { Part, PartCreate } from '@/types/part'
import Spinner from '@/components/ui/Spinner.vue'
import Modal from '@/components/ui/Modal.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'

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
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    parts.search = searchVal.value
    parts.fetchAll()
  }, 300)
}

const filtered = computed(() => {
  const q = searchVal.value.toLowerCase().trim()
  if (!q) return parts.items
  return parts.items.filter(
    (p) =>
      p.part_number.toLowerCase().includes(q) ||
      (p.name ?? '').toLowerCase().includes(q) ||
      (p.article_number ?? '').toLowerCase().includes(q) ||
      (p.drawing_number ?? '').toLowerCase().includes(q),
  )
})

const focused = computed(() => parts.getFocusedPartNumber(props.ctx))

function selectPart(p: Part) {
  parts.focusPart(p.part_number, props.ctx)
}

/** Returns CSS class for the 5px status dot — reference .pd pattern */
function dotClass(status: string): string {
  if (status === 'active') return 'pd ok'
  if (status === 'draft') return 'pd w'
  if (status === 'archived') return 'pd e'
  return 'pd o' // quote / unknown
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

onMounted(() => {
  if (!parts.hasParts) parts.fetchAll()
})

watch(
  () => parts.statusFilter,
  () => parts.fetchAll(),
)
</script>

<template>
  <div class="plist-root">
    <!-- Search + actions -->
    <div class="srch-w">
      <div class="srch-wrap">
        <svg class="srch-ico" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="6.5" cy="6.5" r="4" stroke="currentColor" stroke-width="1.5" />
          <path d="M10 10L13.5 13.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <input
          v-model="searchVal"
          class="srch"
          placeholder="Hledat díl..."
          data-testid="parts-search"
          @input="onSearchInput"
        />
        <button
          v-if="searchVal"
          class="icon-btn srch-clr"
          data-testid="parts-search-clear"
          @click="searchVal = ''; parts.search = ''; parts.fetchAll()"
        >×</button>
      </div>
      <button class="icon-btn" title="Obnovit" data-testid="parts-refresh" @click="parts.fetchAll()">
        <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M2.5 8a5.5 5.5 0 1 0 1-3.18M2.5 2v4h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <button class="icon-btn icon-btn-brand" title="Nový díl" data-testid="parts-create" @click="showCreate = true">
        <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- Status filter tabs — reference .ptab pattern -->
    <div class="ptabs">
      <button :class="['ptab', parts.statusFilter === '' ? 'on' : '']" data-testid="filter-all" @click="parts.statusFilter = ''">
        Vše <span class="n">{{ parts.total }}</span>
      </button>
      <button :class="['ptab', parts.statusFilter === 'active' ? 'on' : '']" data-testid="filter-active" @click="parts.statusFilter = 'active'">Aktivní</button>
      <button :class="['ptab', parts.statusFilter === 'draft' ? 'on' : '']" data-testid="filter-draft" @click="parts.statusFilter = 'draft'">Rozpr.</button>
      <button :class="['ptab', parts.statusFilter === 'archived' ? 'on' : '']" data-testid="filter-archived" @click="parts.statusFilter = 'archived'">Arch.</button>
    </div>

    <!-- Loading -->
    <div v-if="parts.loading" class="plist-state">
      <Spinner size="sm" />
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="plist-state">
      <span class="empty-hint">{{ searchVal ? 'Žádný díl nevyhovuje hledání' : 'Žádné díly' }}</span>
    </div>

    <!-- Parts list — exact reference .pi pattern -->
    <ul v-else class="plist">
      <li
        v-for="p in filtered"
        :key="p.part_number"
        :class="['pi', { sel: focused === p.part_number }]"
        :data-testid="`part-row-${p.part_number}`"
        @click="selectPart(p)"
      >
        <span class="pn">{{ p.part_number }}</span>
        <span class="pm">{{ p.name || p.article_number || '—' }}</span>
        <span :class="dotClass(p.status)" />
      </li>
    </ul>

    <!-- Create modal -->
    <Modal v-model="showCreate" title="Nový díl" size="sm">
      <div class="create-form">
        <Input v-model="createName" label="Název dílu" placeholder="např. Hřídel frézovaná" data-testid="create-part-name" />
        <Input v-model="createArticle" label="Číslo artiklu" placeholder="např. ART-12345" data-testid="create-part-article" />
      </div>
      <template #footer>
        <Button variant="ghost" @click="showCreate = false">Zrušit</Button>
        <Button variant="primary" :loading="creating" data-testid="create-part-submit" @click="handleCreate">Vytvořit díl</Button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.plist-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Search row — reference .srch-w ─── */
.srch-w {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.srch-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}
.srch-ico {
  position: absolute;
  left: 7px;
  width: 11px;
  height: 11px;
  color: var(--t4);
  pointer-events: none;
}
.srch {
  width: 100%;
  height: 26px;
  padding: 0 20px 0 24px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  transition: border-color 0.1s;
}
.srch::placeholder { color: var(--t4); }
.srch:focus { border-color: var(--b3); background: rgba(255,255,255,0.05); }
/* search clear — positioned inside search wrap */
.srch-clr {
  position: absolute;
  right: 4px;
  font-size: var(--fsh);
  line-height: 1;
  padding: 0 3px;
}

/* ─── Filter tabs — reference .ptabs / .ptab ─── */
.ptabs {
  display: flex;
  gap: 1px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.ptab {
  padding: 3px 7px;
  font-size: var(--fsx);
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  font-family: var(--font);
  display: flex;
  align-items: center;
  gap: 3px;
}
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
/* Count badge inside tab */
.n {
  
  font-size: var(--fsm);
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: 2px;
}

/* ─── States ─── */
.plist-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.empty-hint { font-size: var(--fs); color: var(--t4); }

/* ─── Parts list — reference .plist / .pi ─── */
.plist {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.pi {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px var(--pad);
  cursor: pointer;
  position: relative;
  min-height: 28px;
  border-bottom: 1px solid rgba(255,255,255,0.025);
}
.pi:hover { background: var(--b1); }
.pi.sel { background: rgba(229,57,53,0.06); }
.pi.sel::after {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 2px;
  width: 2px;
  background: var(--red);
  border-radius: 0 1px 1px 0;
}

/* Part number — reference .pn */
.pn {
  
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  min-width: 66px;
  flex-shrink: 0;
}

/* Part name — reference .pm */
.pm {
  font-size: var(--fs);
  color: var(--t3);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status dot — reference .pd */
.pd {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pd.ok { background: var(--ok); }
.pd.w  { background: var(--warn); }
.pd.e  { background: var(--err); }
.pd.o  { background: var(--t4); }

/* ─── Create form ─── */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
