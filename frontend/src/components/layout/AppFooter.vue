<template>
  <footer class="app-footer">
    <!-- Left: Connection status + Company info + active workspace -->
    <div class="footer-left">
      <span class="connection-dot"></span>
      <span class="connection-label">Připojeno</span>
      <img src="/logo.png" alt="KOVO RYBKA" class="footer-logo" />
      <span class="footer-company">KOVO RYBKA</span>
      <span v-if="isWorkspaceRoute" class="footer-sep">•</span>
      <span v-if="isWorkspaceRoute" class="footer-workspace">{{ workspaceLabel }}</span>
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
import { useWorkspaceStore } from '@/stores/workspace'
import type { WorkspaceType } from '@/types/workspace'

const route = useRoute()
const workspaceStore = useWorkspaceStore()

const isWorkspaceRoute = computed(() => route.path === '/workspace')

const workspaceLabels: Record<WorkspaceType, string> = {
  part: 'Díly',
  manufacturing: 'Výroba',
  quotes: 'Nabídky',
  partners: 'Partneři',
  materials: 'Materiály',
  files: 'Soubory',
  accounting: 'Účetnictví',
  timevision: 'TimeVision',
  admin: 'Správa',
}

const workspaceLabel = computed(() =>
  workspaceLabels[workspaceStore.activeWorkspace] || ''
)

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
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--b1);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 10px;
  gap: 7px;
  height: 22px;
  z-index: 10000;
  opacity: 0;
  animation: footer-slide-up 0.3s 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes footer-slide-up {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Left: Connection status + Company + Workspace indicator */
.footer-left {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-self: start;
  white-space: nowrap;
  color: var(--t4);
  font-size: 10.5px;
}

.connection-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ok);
  animation: pulse-dot 3s infinite;
  flex-shrink: 0;
}

.connection-label {
  color: var(--t3); /* v2: .sl { color: var(--t3) } — slightly brighter than rest */
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.footer-logo {
  height: 14px;
  width: auto;
  opacity: 0.7;
  flex-shrink: 0;
}

.footer-company {
  opacity: 0.7;
}

.footer-workspace {
  color: var(--t1);
  font-weight: 500;
}

/* Center: GESTIMA + Motto */
.footer-center {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--t4);
  font-size: 10.5px;
  justify-self: center;
  white-space: nowrap;
}

.footer-brand {
  font-size: var(--fsl);
  font-weight: 700;
}

.brand-red {
  color: var(--red);
}

.brand-gray {
  color: var(--t1);
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
  color: var(--t4);
  font-size: 10.5px;
  justify-self: end;
  font-family: var(--mono);
  font-weight: 500;
  opacity: 0.7;
}

.date-btn {
  cursor: pointer;
}

.time-display {
  font-family: var(--mono);
  color: var(--t3);
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
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
  padding: var(--pad);
  z-index: 10003;
}

.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--pad);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--b2);
}

.month-label {
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 600;
  text-transform: capitalize;
}

.nav-btn {
  background: transparent;
  border: none;
  color: var(--t3);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--rs);
  transition: all 100ms cubic-bezier(0,0,0.2,1);
  line-height: 1;
}

.nav-btn:hover {
  background: var(--b1);
  color: var(--t1);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.calendar-weekday {
  text-align: center;
  font-size: var(--fs);
  color: var(--t3);
  font-weight: 600;
  padding: 4px;
  text-transform: uppercase;
}

.calendar-day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs);
  color: var(--t1);
  border-radius: var(--rs);
  cursor: default;
}

.calendar-day.is-other-month {
  color: var(--t3);
}

.calendar-day.is-today {
  background: var(--red);
  color: white;
  font-weight: 700;
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
