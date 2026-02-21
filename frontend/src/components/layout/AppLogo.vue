<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useWindowsStore } from '@/stores/windows'

const router = useRouter()
const route = useRoute()
const windowsStore = useWindowsStore()

function handleLogoClick() {
  if (route.path !== '/windows') {
    router.push('/windows')
  } else if (windowsStore.defaultLayoutId) {
    // Už jsme na /windows — resetuj na default layout
    windowsStore.loadView(windowsStore.defaultLayoutId)
  } else {
    windowsStore.closeAllWindows()
  }
}
</script>

<template>
  <div class="header-center">
    <button class="logo-link" @click="handleLogoClick">
      <div class="logo-text">
        <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
      </div>
    </button>
  </div>
</template>

<style scoped>
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
}

.logo-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

.logo-text {
  font-size: calc(var(--text-2xl) * 2);
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: var(--color-danger);
}

.logo-black {
  color: var(--text-primary);
}
</style>
