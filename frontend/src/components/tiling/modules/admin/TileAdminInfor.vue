<script setup lang="ts">
/**
 * TileAdminInfor — coordinator wrapper pro Infor integraci
 *
 * Deleguje veškerou logiku do InforIntegrationPanel (15 tabů).
 */
import InforIntegrationPanel from './infor/InforIntegrationPanel.vue'
</script>

<template>
  <InforIntegrationPanel data-testid="tile-admin-infor" />
</template>

<style scoped>
</style>
