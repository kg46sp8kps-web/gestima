<template>
  <footer class="app-footer">
    <!-- Left: Window Tabs (only on /windows) -->
    <div class="footer-left">
      <template v-if="route.path === '/windows'">
        <button
          v-for="win in windowsStore.windows"
          :key="win.id"
          @click="handleWindowClick(win.id)"
          class="window-tab"
          :class="{
            'is-active': topWindow?.id === win.id,
            'is-minimized': win.minimized
          }"
          :title="win.title"
        >
          <span
            v-if="win.linkingGroup"
            class="tab-indicator"
            :style="{ backgroundColor: getLinkingGroupColor(win.linkingGroup) }"
          ></span>
          <span class="tab-title">{{ win.title }}</span>
        </button>
      </template>
      <template v-else>
        <img src="/logo.png" alt="KOVO RYBKA" class="footer-logo" />
        <span>KOVO RYBKA</span>
      </template>
    </div>

    <!-- Center: GESTIMA + Motto -->
    <div class="footer-center">
      <span class="footer-brand">
        <span class="brand-red">GESTI</span><span class="brand-gray">MA</span>
      </span>
      <span>v1.12</span>
      <span class="footer-sep">•</span>
      <span class="footer-motto">Be lazy. It's way better than talking to people.</span>
    </div>

    <!-- Right: Time -->
    <div class="footer-right">
      <span>{{ currentTime }}</span>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useWindowsStore } from '@/stores/windows'

const route = useRoute()
const windowsStore = useWindowsStore()

// Get top window
const topWindow = computed(() => {
  if (windowsStore.openWindows.length === 0) return null
  return windowsStore.openWindows.reduce((max, win) =>
    win.zIndex > max.zIndex ? win : max
  )
})

function handleWindowClick(windowId: string) {
  const window = windowsStore.windows.find(w => w.id === windowId)
  if (!window) return

  if (topWindow.value?.id === windowId) {
    windowsStore.minimizeWindow(windowId)
  } else {
    if (window.minimized) {
      windowsStore.restoreWindow(windowId)
    } else {
      windowsStore.bringToFront(windowId)
    }
  }
}

function getLinkingGroupColor(group: string | null): string {
  const colors: Record<string, string> = {
    red: '#ef4444',
    blue: '#3b82f6',
    green: '#10b981',
    yellow: '#f59e0b'
  }
  return colors[group || ''] || '#6b7280'
}

const currentTime = computed(() => {
  const now = new Date()
  return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
})
</script>

<style scoped>
.app-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-default);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.25rem 1rem;
  gap: var(--space-3);
  height: 32px;
  z-index: 10000;
}

/* Left: Window Tabs or Company */
.footer-left {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  overflow-x: auto;
  overflow-y: hidden;
  justify-self: start;
}

.footer-logo {
  height: 14px;
  width: auto;
  opacity: 0.7;
  flex-shrink: 0;
}

.window-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 150px;
}

.window-tab:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.window-tab.is-active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.window-tab.is-minimized {
  opacity: 0.6;
}

.tab-indicator {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Center: GESTIMA + Motto */
.footer-center {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  justify-self: center;
  white-space: nowrap;
}

.footer-brand {
  font-size: var(--text-xs);
  font-weight: 700;
}

.brand-red {
  color: var(--primary-color);
}

.brand-gray {
  color: var(--text-secondary);
}

.footer-motto {
  font-style: italic;
  opacity: 0.7;
}

.footer-sep {
  opacity: 0.5;
}

/* Right: Time */
.footer-right {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: var(--text-2xs);
  justify-self: end;
  font-family: monospace;
  font-weight: 500;
}
</style>
