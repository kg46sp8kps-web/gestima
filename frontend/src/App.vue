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
const route = useRoute()
const ui = useUiStore()

// Initialize dark mode (will load from localStorage)
const { isDark } = useDarkMode()

// Initialize design tokens from localStorage
function initDesignTokens() {
  const saved = localStorage.getItem('gestima_design_tokens')
  if (saved) {
    try {
      const tokens = JSON.parse(saved)
      Object.entries(tokens).forEach(([name, value]) => {
        const cssVar = `--${name}`
        const numValue = value as number
        if (name.startsWith('text-')) {
          // Font sizes in px (matching design-system.css)
          document.documentElement.style.setProperty(cssVar, `${numValue}px`)
        } else if (name.startsWith('space-')) {
          // Spacing in rem (matching design-system.css)
          document.documentElement.style.setProperty(cssVar, `${numValue / 16}rem`)
        } else {
          // Density values in px
          document.documentElement.style.setProperty(cssVar, `${numValue}px`)
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
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <!-- Global footer (except login) -->
    <AppFooter v-if="!isLoginPage" />

    <!-- Global toast notifications -->
    <ToastContainer />

    <!-- Global dialogs -->
    <ConfirmDialog />
    <AlertDialog />

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

/* === ROUTE TRANSITIONS === */
.page-enter-active,
.page-leave-active {
  transition: opacity 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.page-enter-from,
.page-leave-to {
  opacity: 0;
}
</style>
