<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import * as filesApi from '@/api/files'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const files = ref<FileWithLinks[]>([])
const loading = ref(false)
const error = ref(false)
const selectedFileId = ref<number | null>(null)

const selectedFile = computed(() => {
  if (selectedFileId.value != null) {
    return files.value.find(f => f.id === selectedFileId.value) ?? null
  }
  return files.value[0] ?? null
})

const previewSrc = computed(() =>
  selectedFile.value ? filesApi.previewUrl(selectedFile.value.id) : null,
)

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

watch(
  part,
  async (p) => {
    files.value = []
    selectedFileId.value = null
    if (!p) return
    loading.value = true
    error.value = false
    try {
      files.value = await filesApi.listByEntity('part', p.id)
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="wdrw">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!files.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné soubory</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- File list — shown when multiple files -->
      <div v-if="files.length > 1" class="file-list">
        <button
          v-for="f in files"
          :key="f.id"
          :class="['file-item', { active: f.id === selectedFile?.id }]"
          :data-testid="`file-item-${f.id}`"
          @click="selectedFileId = f.id"
        >
          <span class="file-type">{{ f.file_type.toUpperCase() }}</span>
          <span class="file-name">{{ f.original_filename }}</span>
          <span class="file-size">{{ formatBytes(f.file_size) }}</span>
        </button>
      </div>

      <!-- Preview area -->
      <div class="preview-wrap">
        <!-- PDF iframe -->
        <iframe
          v-if="selectedFile?.mime_type === 'application/pdf' && previewSrc"
          :src="previewSrc"
          :title="selectedFile.original_filename"
          class="pdf-frame"
          frameborder="0"
        />

        <!-- Non-PDF: file info + download -->
        <div v-else-if="selectedFile" class="mod-placeholder">
          <div class="mod-dot" />
          <div class="file-info-name">{{ selectedFile.original_filename }}</div>
          <div class="file-info-meta">
            {{ selectedFile.file_type.toUpperCase() }} · {{ formatBytes(selectedFile.file_size) }}
          </div>
          <a
            :href="`/api/files/${selectedFile.id}/download`"
            class="dl-link"
            target="_blank"
            :data-testid="`file-download-${selectedFile.id}`"
          >
            Stáhnout soubor
          </a>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wdrw {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Placeholder ─── */
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
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── File selector list ─── */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-bottom: 1px solid var(--b1);
  max-height: 110px;
  overflow-y: auto;
  flex-shrink: 0;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--t2);
  font-size: var(--fs);
  transition: background 0.1s;
}
.file-item:hover { background: var(--b1); }
.file-item.active { background: var(--b1); color: var(--t1); }

.file-type {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: var(--rs);
  background: var(--b2);
  color: var(--t3);
  flex-shrink: 0;
}
.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  font-size: 10px;
  color: var(--t4);
  flex-shrink: 0;
}

/* ─── Preview ─── */
.preview-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.pdf-frame {
  flex: 1;
  width: 100%;
  min-height: 0;
  border: none;
  background: var(--ground);
}

/* ─── Non-PDF fallback ─── */
.file-info-name {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
}
.file-info-meta {
  font-size: 10px;
  color: var(--t4);
}
.dl-link {
  margin-top: 4px;
  padding: 5px 14px;
  border-radius: var(--rs);
  border: 1px solid var(--b2);
  color: var(--t2);
  font-size: var(--fs);
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s;
}
.dl-link:hover { border-color: var(--b3); color: var(--t1); }
</style>
