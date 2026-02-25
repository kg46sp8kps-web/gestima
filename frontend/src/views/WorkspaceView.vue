<script setup lang="ts">
import { onMounted } from 'vue'
import TilingWorkspace from '@/components/tiling/TilingWorkspace.vue'
import { usePrefetch } from '@/composables/usePrefetch'

const { prefetchAll } = usePrefetch()
onMounted(() => void prefetchAll())
</script>

<template>
  <TilingWorkspace />
</template>
