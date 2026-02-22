<script setup lang="ts">
import { computed } from 'vue'
import type { TileNode, LeafNode, SplitNode } from '@/types/workspace'
import TilePanel from './TilePanel.vue'
import TileSplitDivider from './TileSplitDivider.vue'

interface Props {
  node: TileNode
  instant?: boolean
  /** Flex ratio applied to THIS node's root element (set by parent split).
   *  When undefined this is the root node — fill available space via CSS flex:1.
   */
  flexRatio?: number
}

const props = defineProps<Props>()

const isLeaf = computed(() => props.node.type === 'leaf')
const isSplit = computed(() => props.node.type === 'split')

/**
 * Reference pattern from tiling-preview-v3.html:
 *   childA.style.flex = `${ra} ${ra} 0%`
 *   childB.style.flex = `${rb} ${rb} 0%`
 * Children are DIRECT flex items inside .tree-split — no wrapper divs.
 * Root node has no flexRatio → relies on CSS `flex: 1` from .tree-leaf/.tree-split.
 */
const nodeStyle = computed(() => {
  if (props.flexRatio === undefined) return {}
  const r = props.flexRatio
  return { flex: `${r} ${r} 0%`, minWidth: '0', minHeight: '0' }
})

const split = computed(() =>
  props.node.type === 'split' ? (props.node as SplitNode) : null,
)
</script>

<template>
  <!-- Leaf: renders a panel directly inside parent split (no wrapper div) -->
  <div
    v-if="isLeaf"
    class="tree-leaf"
    :style="nodeStyle"
  >
    <TilePanel :node="(node as LeafNode)" :instant="instant" />
  </div>

  <!-- Split: its children are direct flex items (no extra wrappers) -->
  <div
    v-else-if="isSplit && split"
    class="tree-split"
    :class="split.direction === 'horizontal' ? 'h' : 'v'"
    :style="nodeStyle"
  >
    <TileNode
      :key="split.children[0].id"
      :node="split.children[0]"
      :instant="instant"
      :flex-ratio="split.ratio"
    />

    <TileSplitDivider
      :split-id="node.id"
      :direction="split.direction"
      :ratio="split.ratio"
    />

    <TileNode
      :key="split.children[1].id"
      :node="split.children[1]"
      :instant="instant"
      :flex-ratio="1 - split.ratio"
    />
  </div>
</template>

<style scoped>
/* Both leaf and split fill available space by default (CSS flex:1 for root node).
   When inside a split, inline :style overrides flex with the ratio value.
   flex-grow/shrink transitions smooth out panel resizes when modules are added/moved. */
.tree-leaf {
  flex: 1;
  min-width: 0;
  min-height: 0;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tree-split {
  flex: 1;
  display: flex;
  min-width: 0;
  min-height: 0;
}
.tree-split.h { flex-direction: row; }
.tree-split.v { flex-direction: column; }
</style>
