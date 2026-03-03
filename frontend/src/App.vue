<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useSessionGuard } from '@/composables/useSessionGuard'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const auth = useAuthStore()
useThemeStore() // applies saved theme on startup
useSessionGuard() // periodic session health check → redirect on expired/dead session

onMounted(() => {
  auth.fetchMe()
})
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ConfirmDialog />
</template>

<style scoped>
/* App root fills the viewport */
</style>
