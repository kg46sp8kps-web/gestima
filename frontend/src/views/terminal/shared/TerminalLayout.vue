<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOperatorStore } from '@/stores/operator'
import ActiveJobBar from './ActiveJobBar.vue'

interface NavItem {
  routeName: string
  label: string
  icon: 'grid' | 'list' | 'clipboard'
}

const router = useRouter()
const auth = useAuthStore()
const operator = useOperatorStore()

// Nav items computed from user role
const items = computed<NavItem[]>(() => {
  const base: NavItem[] = [
    { routeName: 'terminal-dashboard', label: 'Přehled', icon: 'grid' },
    { routeName: 'terminal-queue', label: 'Fronta', icon: 'list' },
  ]
  const role = auth.user?.role
  if (role === 'mistr' || role === 'admin') {
    base.push({ routeName: 'terminal-orders', label: 'Zakázky', icon: 'clipboard' })
  }
  return base
})

// Inactivity auto-logout (10 min)
const INACTIVITY_TIMEOUT = 10 * 60 * 1000
let inactivityTimer: ReturnType<typeof setTimeout> | null = null

function resetInactivity() {
  operator.touchActivity()
  if (inactivityTimer) clearTimeout(inactivityTimer)
  inactivityTimer = setTimeout(() => {
    operator.$reset()
    auth.logout()
    router.push({ name: 'terminal-login' })
  }, INACTIVITY_TIMEOUT)
}

const touchEvents = ['touchstart', 'click', 'keydown']
const onOnline = () => operator.setOnlineStatus(true)
const onOffline = () => operator.setOnlineStatus(false)

onMounted(() => {
  // Start auto-refresh for active jobs
  operator.startAutoRefresh()
  operator.fetchActiveJobs()
  operator.fetchTransactionAlerts()
  operator.fetchWorkcenters()
  operator.setOnlineStatus(typeof navigator !== 'undefined' ? navigator.onLine : true)

  // Inactivity tracking
  touchEvents.forEach(e => document.addEventListener(e, resetInactivity, { passive: true }))
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  resetInactivity()
})

onUnmounted(() => {
  operator.stopAutoRefresh()
  touchEvents.forEach(e => document.removeEventListener(e, resetInactivity))
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  if (inactivityTimer) clearTimeout(inactivityTimer)
})

function doLogout() {
  operator.$reset()
  auth.logout()
  router.push({ name: 'terminal-login' })
}
</script>

<template>
  <div class="terminal">
    <div v-if="!operator.isOnline" class="offline-banner">
      Offline režim: tablet není na Wi-Fi, zápis do Inforu nyní neproběhne.
    </div>

    <!-- Active job bar (top, visible only when job is running) -->
    <ActiveJobBar />

    <!-- Main content -->
    <div class="terminal-content">
      <RouterView />
    </div>

    <!-- Bottom navigation -->
    <nav class="terminal-nav">
      <button
        v-for="item in items"
        :key="item.routeName"
        :class="['nav-btn', { active: $route.name === item.routeName }]"
        @click="router.push({ name: item.routeName })"
      >
        <!-- grid icon -->
        <svg v-if="item.icon === 'grid'" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <rect x="14" y="14" width="7" height="7" rx="1"/>
        </svg>
        <!-- list icon -->
        <svg v-else-if="item.icon === 'list'" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="8" y1="6" x2="21" y2="6"/>
          <line x1="8" y1="12" x2="21" y2="12"/>
          <line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6" stroke-width="3" stroke-linecap="round"/>
          <line x1="3" y1="12" x2="3.01" y2="12" stroke-width="3" stroke-linecap="round"/>
          <line x1="3" y1="18" x2="3.01" y2="18" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <!-- clipboard icon -->
        <svg v-else-if="item.icon === 'clipboard'" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
          <line x1="9" y1="10" x2="15" y2="10"/>
          <line x1="9" y1="14" x2="15" y2="14"/>
          <line x1="9" y1="18" x2="13" y2="18"/>
        </svg>
        <span>{{ item.label }}</span>
      </button>

      <button class="nav-btn logout" @click="doLogout">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        <span>Odhlásit</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
/* Touch-optimized CSS variables */
.terminal {
  --op-fs: 16px;
  --op-touch: 48px;

  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--base);
  color: var(--t1);
  font-size: var(--op-fs);
  overflow: hidden;
}

.terminal-content {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.offline-banner {
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--amber);
  background: rgba(251, 191, 36, 0.15);
  border-bottom: 1px solid rgba(91, 29, 0, 0.22);
}

/* Bottom nav */
.terminal-nav {
  display: flex;
  height: 72px;
  border-top: 1px solid var(--b1);
  background: var(--ground, var(--base));
  flex-shrink: 0;
  /* Safe area for iPhone notch */
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.nav-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--t4);
  font-size: 11px;
  font-family: var(--font);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: color 100ms;
}
.nav-btn:active {
  color: var(--t2);
}
.nav-btn.active {
  color: var(--red, #e53935);
}
.nav-btn.logout {
  color: var(--t4);
}
.nav-btn.logout:active {
  color: var(--red, #e53935);
}
</style>
