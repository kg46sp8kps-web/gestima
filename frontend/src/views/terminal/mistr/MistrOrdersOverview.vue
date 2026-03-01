<script setup lang="ts">
// Thin wrapper — reuses TileOrdersOverview directly with dummy tile props
</script>

<template>
  <TileOrdersOverview leaf-id="terminal" ctx="ca" />
</template>

<script lang="ts">
import TileOrdersOverview from '@/components/tiling/modules/TileOrdersOverview.vue'

export default {
  components: { TileOrdersOverview },
}
</script>
