<script setup lang="ts">
/**
 * GESTIMA Root Component
 * Global layout with AppHeader/AppFooter on all pages except login
 */
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useDarkMode } from '@/composables/useDarkMode'
import { useUiStore } from '@/stores/ui'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import AlertDialog from '@/components/ui/AlertDialog.vue'
import CssDebugOverlay from '@/components/dev/CssDebugOverlay.vue'

const route = useRoute()
const ui = useUiStore()

// Initialize dark mode (will load from localStorage)
const { isDark } = useDarkMode()

// Dev mode check for CSS Debug Overlay
const isDev = import.meta.env.DEV

// Initialize design tokens from localStorage
function initDesignTokens() {
  const saved = localStorage.getItem('gestima_design_tokens')
  if (saved) {
    try {
      const tokens = JSON.parse(saved)
      Object.entries(tokens).forEach(([name, value]) => {
        const cssVar = `--${name}`
        const numValue = value as number
        // Font sizes and spacing in rem, row-height in px
        if (name.startsWith('text-') || name.startsWith('space-')) {
          document.documentElement.style.setProperty(cssVar, `${numValue / 16}rem`)
        } else if (name === 'density-row-height') {
          document.documentElement.style.setProperty(cssVar, `${numValue}px`)
        } else {
          document.documentElement.style.setProperty(cssVar, `${numValue / 16}rem`)
        }
      })
    } catch (e) {
      console.error('Failed to load design tokens:', e)
    }
  }
}

// Initialize density and design tokens on app start
onMounted(() => {
  ui.initDensity()
  initDesignTokens()
})

// Hide header/footer on login page
const isLoginPage = computed(() => route.name === 'login')
</script>

<template>
  <div id="app" class="app-layout">
    <!-- Global header (except login) -->
    <AppHeader v-if="!isLoginPage" />

    <!-- Main content -->
    <main class="app-main" :class="{ 'with-chrome': !isLoginPage }">
      <RouterView />
    </main>

    <!-- Global footer (except login) -->
    <AppFooter v-if="!isLoginPage" />

    <!-- Global toast notifications -->
    <ToastContainer />

    <!-- Global dialogs -->
    <ConfirmDialog />
    <AlertDialog />

    <!-- CSS Debug Overlay (Ctrl+Shift+D) -->
    <CssDebugOverlay v-if="isDev" />
  </div>
</template>

<style>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  position: relative;
}

.app-main.with-chrome {
  /* No margin/padding - starts right after header */
}
</style>
