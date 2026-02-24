<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as filesApi from '@/api/files'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<FileWithLinks[]>([])
const loading = ref(false)
const error = ref(false)
const searchQuery = ref('')

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(f =>
    f.original_filename.toLowerCase().includes(q) ||
    f.file_type.toLowerCase().includes(q),
  )
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function openPreview(id: number) {
  window.open(filesApi.previewUrl(id), '_blank')
}

async function load() {
  loading.value = true
  error.value = false
  try {
    items.value = await filesApi.list()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wfil">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Search -->
      <div class="srch-bar">
        <Input
          v-model="searchQuery"
          bare
          type="text"
          placeholder="Hledat soubor…"
          testid="files-search-input"
          class="srch-inp"
        />
        <span class="srch-count">{{ filtered.length }} / {{ items.length }}</span>
      </div>

      <!-- Empty -->
      <div v-if="!filtered.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">{{ searchQuery ? 'Žádné výsledky' : 'Žádné soubory' }}</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th>Název</th>
              <th style="width:42px">Typ</th>
              <th class="r" style="width:64px">Velikost</th>
              <th style="width:80px">Datum</th>
              <th class="r" style="width:42px">Vazby</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="f in filtered"
              :key="f.id"
              :data-testid="`file-row-${f.id}`"
              class="file-row"
              @click="f.file_type === 'pdf' ? openPreview(f.id) : undefined"
            >
              <td>
                <div class="file-name" :class="{ clickable: f.file_type === 'pdf' }">
                  {{ f.original_filename }}
                </div>
              </td>
              <td>
                <span class="badge">{{ f.file_type.toUpperCase() }}</span>
              </td>
              <td class="r t4">{{ formatSize(f.file_size) }}</td>
              <td class="t4">{{ f.created_at.split('T')[0] }}</td>
              <td class="r t4">{{ f.links.length || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wfil {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

.srch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
/* .srch-inp layout: visual styles come from Input component's .input-ctrl */
.srch-inp { flex: 1; }
.srch-count {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}

.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.t4 { color: var(--t4); }
.r { text-align: right; }

.file-row { cursor: default; }
.file-name { color: var(--t1); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; }
.file-name.clickable { color: var(--t1); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.file-name.clickable:hover { color: var(--t2); }

/* File type badges use global .badge from design-system.css */
</style>
