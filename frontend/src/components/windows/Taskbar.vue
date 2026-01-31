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
    red: '#ef4444',
    blue: '#3b82f6',
    green: '#10b981',
    yellow: '#f59e0b'
  }
  return colors[group || ''] || '#6b7280'
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
        <Circle :size="8" fill="#10b981" stroke="none" />
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
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  z-index: 999;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
}

.taskbar-windows {
  display: flex;
  gap: var(--space-1);
  align-items: center;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
}

.taskbar-windows::-webkit-scrollbar {
  height: 4px;
}

.taskbar-windows::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: var(--radius-sm);
}

.taskbar-window-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
  position: relative;
  min-width: 100px;
  max-width: 200px;
}

.taskbar-window-tab:hover {
  background: var(--state-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.taskbar-window-tab.is-active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  box-shadow: var(--shadow-sm);
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
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  font-style: italic;
  padding: 0 var(--space-3);
}

.taskbar-status {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-shrink: 0;
  margin-left: var(--space-4);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.status-time {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
  min-width: 42px;
  text-align: right;
}
</style>
