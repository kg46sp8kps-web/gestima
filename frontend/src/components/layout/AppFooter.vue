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
      <span class="footer-sep">•</span>
      <img src="/logo.png" alt="KOVO RYBKA" class="footer-logo" />
    </div>

    <!-- Right: Date + Time -->
    <div class="footer-right">
      <span class="date-btn" @click="toggleCalendar">{{ currentDate }}</span>
      <span class="time-sep">•</span>
      <span class="time-display">{{ currentTime }}</span>
    </div>

    <!-- Calendar Popup -->
    <Transition name="calendar-fade">
      <div v-if="showCalendar" class="calendar-popup">
        <div class="calendar-header">
          <button @click="previousMonth" class="nav-btn">‹</button>
          <span class="month-label">{{ monthLabel }}</span>
          <button @click="nextMonth" class="nav-btn">›</button>
        </div>
        <div class="calendar-grid">
          <div v-for="day in weekDays" :key="day" class="calendar-weekday">{{ day }}</div>
          <div
            v-for="(day, index) in calendarDays"
            :key="index"
            class="calendar-day"
            :class="{
              'is-today': day.isToday,
              'is-other-month': day.isOtherMonth,
              'is-empty': !day.date
            }"
          >
            <span v-if="day.date">{{ day.date }}</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Calendar Backdrop -->
    <div v-if="showCalendar" class="calendar-backdrop" @click="closeCalendar"></div>
  </footer>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWindowsStore } from '@/stores/windows'

const route = useRoute()
const windowsStore = useWindowsStore()

// Live clock
const now = ref(new Date())
let clockTimer: ReturnType<typeof setInterval>

onMounted(() => {
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  clearInterval(clockTimer)
})

// Calendar state
const showCalendar = ref(false)
const calendarDate = ref(new Date())

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
    red: 'var(--link-group-red)',
    blue: 'var(--link-group-blue)',
    green: 'var(--link-group-green)',
    yellow: 'var(--link-group-yellow)'
  }
  return colors[group || ''] || 'var(--link-group-neutral)'
}

const currentDate = computed(() => {
  return now.value.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' })
})

const currentTime = computed(() => {
  return now.value.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
})

const monthLabel = computed(() => {
  return calendarDate.value.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' })
})

const weekDays = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']

interface CalendarDay {
  date: number | null
  isToday: boolean
  isOtherMonth: boolean
}

const calendarDays = computed(() => {
  const year = calendarDate.value.getFullYear()
  const month = calendarDate.value.getMonth()

  // First day of month
  const firstDay = new Date(year, month, 1)
  const firstDayOfWeek = (firstDay.getDay() + 6) % 7 // Monday = 0

  // Last day of month
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()

  // Previous month days
  const prevMonthLastDay = new Date(year, month, 0).getDate()

  // Today
  const today = new Date()
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month

  const days: CalendarDay[] = []

  // Previous month days
  for (let i = firstDayOfWeek - 1; i >= 0; i--) {
    days.push({
      date: prevMonthLastDay - i,
      isToday: false,
      isOtherMonth: true
    })
  }

  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({
      date: i,
      isToday: isCurrentMonth && i === today.getDate(),
      isOtherMonth: false
    })
  }

  // Next month days
  const remainingDays = 42 - days.length // 6 rows × 7 days
  for (let i = 1; i <= remainingDays; i++) {
    days.push({
      date: i,
      isToday: false,
      isOtherMonth: true
    })
  }

  return days
})

function toggleCalendar() {
  showCalendar.value = !showCalendar.value
}

function closeCalendar() {
  showCalendar.value = false
}

function previousMonth() {
  calendarDate.value = new Date(calendarDate.value.getFullYear(), calendarDate.value.getMonth() - 1)
}

function nextMonth() {
  calendarDate.value = new Date(calendarDate.value.getFullYear(), calendarDate.value.getMonth() + 1)
}
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
  padding: var(--space-1) var(--space-4);
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
  font-size: var(--text-sm);
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
  font-size: var(--text-sm);
  justify-self: center;
  white-space: nowrap;
}

.footer-brand {
  font-size: var(--text-sm);
  font-weight: 700;
}

.brand-red {
  color: var(--brand-hover);
}

.brand-gray {
  color: var(--text-primary);
}

.footer-motto {
  font-style: italic;
  opacity: 0.7;
}

.footer-sep {
  opacity: 0.5;
}

/* Right: Date + Time */
.footer-right {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  justify-self: end;
  font-family: monospace;
  font-weight: 500;
  opacity: 0.7; /* Same as motto */
}

.date-btn {
  cursor: pointer;
}

.time-sep {
  opacity: 0.5;
}

/* Calendar Popup */
.calendar-popup {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  width: 280px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: var(--space-3);
  z-index: 10003;
}

.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.month-label {
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-transform: capitalize;
}

.nav-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: var(--text-lg);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
  line-height: 1;
}

.nav-btn:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--space-0\.5);
}

.calendar-weekday {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-semibold);
  padding: var(--space-1);
  text-transform: uppercase;
}

.calendar-day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  cursor: default;
}

.calendar-day.is-other-month {
  color: var(--text-tertiary);
}

.calendar-day.is-today {
  background: var(--brand-hover);
  color: white;
  font-weight: var(--font-bold);
}

.calendar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10002;
  background: transparent;
}

/* Calendar Transition */
.calendar-fade-enter-active,
.calendar-fade-leave-active {
  transition: opacity 0.15s ease;
}

.calendar-fade-enter-from,
.calendar-fade-leave-to {
  opacity: 0;
}

</style>
