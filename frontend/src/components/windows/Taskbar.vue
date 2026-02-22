<script setup lang="ts">
/**
 * Taskbar - Bottom bar showing all open windows
 * Click to focus/minimize windows, show status indicators
 */

import { computed } from 'vue'
import { useWindowsStore } from '@/stores/windows'
import { Circle } from 'lucide-vue-next'

const store = useWindowsStore()

// Get top window (highest zIndex)
const topWindow = computed(() => {
  if (store.openWindows.length === 0) return null
  return store.openWindows.reduce((max, win) =>
    win.zIndex > max.zIndex ? win : max
  )
})

function handleWindowClick(windowId: string) {
  const window = store.windows.find(w => w.id === windowId)
  if (!window) return

  // If window is top window, minimize it
  if (topWindow.value?.id === windowId) {
    store.minimizeWindow(windowId)
  } else {
    // Otherwise, bring to front (and restore if minimized)
    if (window.minimized) {
      store.restoreWindow(windowId)
    } else {
      store.bringToFront(windowId)
    }
  }
}

// Get color for linking group dot
function getLinkingGroupColor(group: string | null): string {
  const colors: Record<string, string> = {
    red: 'var(--link-group-red)',
    blue: 'var(--link-group-blue)',
    green: 'var(--link-group-green)',
    yellow: 'var(--link-group-yellow)'
  }
  return colors[group || ''] || 'var(--link-group-neutral)'
}

// Current time
const currentTime = computed(() => {
  const now = new Date()
  return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
})
</script>

<template>
  <div class="taskbar">
    <!-- Window tabs -->
    <div class="taskbar-windows">
      <button
        v-for="win in store.windows"
        :key="win.id"
        @click="handleWindowClick(win.id)"
        class="taskbar-window-tab"
        :class="{
          'is-active': topWindow?.id === win.id,
          'is-minimized': win.minimized
        }"
        :title="win.title"
      >
        <!-- Linking group indicator -->
        <span
          v-if="win.linkingGroup"
          class="tab-indicator"
          :style="{ backgroundColor: getLinkingGroupColor(win.linkingGroup) }"
        ></span>

        <!-- Window title -->
        <span class="tab-title">{{ win.title }}</span>
      </button>

      <!-- Empty state -->
      <div v-if="store.windows.length === 0" class="taskbar-empty">
        No windows open
      </div>
    </div>

    <!-- Status indicators (right side) -->
    <div class="taskbar-status">
      <div class="status-indicator">
        <Circle :size="8" fill="var(--ok)" stroke="none" />
        <span>System Operational</span>
      </div>
      <div class="status-time">
        {{ currentTime }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.taskbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: var(--surface);
  border-top: 1px solid var(--b2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--pad);
  z-index: 999;
  box-shadow: 0 1px 3px rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
}

.taskbar-windows {
  display: flex;
  gap: 4px;
  align-items: center;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
}

.taskbar-windows::-webkit-scrollbar {
  height: 4px;
}

.taskbar-windows::-webkit-scrollbar-thumb {
  background: var(--b2);
  border-radius: var(--rs);
}

.taskbar-window-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px var(--pad);
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t3);
  font-size: var(--fs);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
  white-space: nowrap;
  position: relative;
  min-width: 100px;
  max-width: 200px;
}

.taskbar-window-tab:hover {
  background: var(--b1);
  color: var(--t1);
  border-color: var(--b3);
}

.taskbar-window-tab.is-active {
  background: var(--red);
  color: white;
  border-color: var(--red);
  box-shadow: 0 1px 3px rgba(0,0,0,0.4);
}

.taskbar-window-tab.is-minimized {
  opacity: 0.6;
}

.tab-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.2);
}

.tab-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.taskbar-empty {
  color: var(--t3);
  font-size: var(--fs);
  font-style: italic;
  padding: 0 var(--pad);
}

.taskbar-status {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  margin-left: 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--t3);
  font-size: var(--fs);
}

.status-time {
  color: var(--t3);
  font-size: var(--fs);
  font-family: var(--mono);
  font-weight: 500;
  min-width: 42px;
  text-align: right;
}
</style>
