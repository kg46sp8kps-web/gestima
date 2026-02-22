<script setup lang="ts">
import { computed } from 'vue'
import { Maximize2Icon, Minimize2Icon, XIcon } from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { MODULE_REGISTRY } from '@/types/workspace'
import type { LeafNode } from '@/types/workspace'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  node: LeafNode
  maximized: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'maximize': []
  'close': []
  'drag-start': []
  'open-module-picker': []
}>()

const ws = useWorkspaceStore()
const moduleDef = computed(() => MODULE_REGISTRY[props.node.module])

function onDragStart(e: DragEvent) {
  ws.startDrag(props.node.id, props.node.module)
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', props.node.id)
    e.dataTransfer.effectAllowed = 'move'
  }
  emit('drag-start')
}

function onDragEnd() {
  ws.endDrag()
}
</script>

<template>
  <div
    class="ph"
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
  >
    <!-- Module dot + title -->
    <div class="pht" @click="emit('open-module-picker')">
      <span
        class="ph-dot"
        :style="{ background: moduleDef.dotColor }"
      />
      <span class="ph-label">{{ moduleDef.label }}</span>
      <span v-if="node.ctx === 'cb'" class="ph-ctx">B</span>
    </div>

    <div class="phf" />

    <!-- Controls -->
    <button
      class="pc"
      :title="maximized ? 'Obnovit' : 'Maximalizovat'"
      data-testid="panel-maximize"
      @click.stop="emit('maximize')"
    >
      <Maximize2Icon v-if="!maximized" :size="ICON_SIZE_SM - 2" />
      <Minimize2Icon v-else :size="ICON_SIZE_SM - 2" />
    </button>
    <button
      class="pc x"
      title="Zavřít panel"
      data-testid="panel-close"
      @click.stop="emit('close')"
    >
      <XIcon :size="ICON_SIZE_SM - 2" />
    </button>
  </div>
</template>

<style scoped>
.ph {
  height: 28px;
  background: rgba(255,255,255,0.025);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  padding: 0 var(--pad);
  gap: 4px;
  flex-shrink: 0;
  user-select: none;
  cursor: grab;
}
.ph:active { cursor: grabbing; }

.pht {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--rs);
  transition: background 0.08s;
}
.pht:hover { background: var(--b1); }

.ph-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ph-label {
  font-size: var(--fsl);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  pointer-events: none;
}
.ph-ctx {
  font-family: var(--mono);
  font-size: 9px;
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: 2px;
}

.phf { flex: 1; }

.pc {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: var(--t4);
  cursor: pointer;
  transition: all 0.06s;
  font-family: var(--font);
}
.pc:hover { background: var(--b1); color: var(--t1); }
.pc.x:hover { background: rgba(248,113,113,0.12); color: var(--err); }
.pc:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 1px; }
</style>
