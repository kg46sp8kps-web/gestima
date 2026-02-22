<script setup lang="ts">
import { computed } from 'vue'
import type { TileNode, LeafNode, SplitNode } from '@/types/workspace'
import TilePanel from './TilePanel.vue'
import TileSplitDivider from './TileSplitDivider.vue'

interface Props {
  node: TileNode
  instant?: boolean
}

const props = defineProps<Props>()

const isLeaf = computed(() => props.node.type === 'leaf')
const isSplit = computed(() => props.node.type === 'split')

const child0Style = computed(() => {
  if (props.node.type !== 'split') return {}
  const ratio = props.node.ratio
  return props.node.direction === 'horizontal'
    ? { width: `${ratio * 100}%`, minWidth: '0', minHeight: '0' }
    : { height: `${ratio * 100}%`, minWidth: '0', minHeight: '0' }
})

const child1Style = computed(() => {
  if (props.node.type !== 'split') return {}
  return { flex: '1', minWidth: '0', minHeight: '0' }
})
</script>

<template>
  <!-- Leaf: renders a panel -->
  <div
    v-if="isLeaf"
    class="tree-leaf"
  >
    <TilePanel :node="(node as LeafNode)" :instant="instant" />
  </div>

  <!-- Split: renders two children with a divider -->
  <div
    v-else-if="isSplit"
    class="tree-split"
    :class="(node as SplitNode).direction === 'horizontal' ? 'h' : 'v'"
  >
    <div :style="child0Style">
      <TileNode :node="(node as SplitNode).children[0]" :instant="instant" />
    </div>

    <TileSplitDivider
      :split-id="node.id"
      :direction="(node as SplitNode).direction"
      :ratio="(node as SplitNode).ratio"
    />

    <div :style="child1Style">
      <TileNode :node="(node as SplitNode).children[1]" :instant="instant" />
    </div>
  </div>
</template>

<style scoped>
.tree-leaf {
  min-width: 0;
  min-height: 0;
  position: relative;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.tree-split {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1;
}
.tree-split.h { flex-direction: row; }
.tree-split.v { flex-direction: column; }
</style>
