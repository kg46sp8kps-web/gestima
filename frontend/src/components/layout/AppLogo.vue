<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspace'

const router = useRouter()
const route = useRoute()
const workspaceStore = useWorkspaceStore()

function handleLogoClick() {
  if (route.path !== '/workspace') {
    router.push('/workspace')
  } else if (workspaceStore.defaultViewId) {
    workspaceStore.loadView(workspaceStore.defaultViewId)
  } else {
    workspaceStore.switchWorkspace('part')
  }
}
</script>

<template>
  <div class="header-center">
    <button class="logo-link" @click="handleLogoClick" data-testid="logo-btn">
      <img src="/logo.png" alt="Logo" class="hlogo" />
      <div class="logo-text">
        <em class="logo-red">GESTI</em><span class="logo-white">MA</span>
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
  gap: 6px;
  text-decoration: none;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

.hlogo {
  width: 21px;
  height: 21px;
  border-radius: 50%;
  flex-shrink: 0;
  filter: drop-shadow(0 0 6px rgba(229,57,53,0.2));
  transition: filter 0.2s var(--ease);
}

.logo-link:hover .hlogo {
  filter: drop-shadow(0 0 10px rgba(229,57,53,0.4));
}

.logo-text {
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  user-select: none;
}

.logo-red {
  color: var(--red);
  font-style: normal;
}

.logo-white {
  color: var(--t1);
}
</style>
