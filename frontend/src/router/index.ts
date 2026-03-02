import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'workspace',
      component: () => import('@/views/WorkspaceView.vue'),
    },
    {
      path: '/dilna',
      name: 'dilna',
      component: () => import('@/views/WorkshopView.vue'),
    },
    // === Terminal (operator + mistr — role-based UI) ===
    {
      path: '/terminal/login',
      name: 'terminal-login',
      component: () => import('@/views/terminal/shared/TerminalPinLogin.vue'),
      meta: { public: true },
    },
    {
      path: '/terminal',
      component: () => import('@/views/terminal/shared/TerminalLayout.vue'),
      meta: { terminal: true },
      children: [
        {
          path: '',
          name: 'terminal-dashboard',
          component: () => import('@/views/terminal/operator/OperatorDashboard.vue'),
        },
        {
          path: 'queue',
          name: 'terminal-queue',
          component: () => import('@/views/terminal/operator/OperatorQueue.vue'),
        },
        {
          path: 'job/:job/:oper',
          name: 'terminal-job-detail',
          component: () => import('@/views/terminal/operator/OperatorJobDetail.vue'),
          props: true,
        },
        {
          path: 'orders',
          name: 'terminal-orders',
          component: () => import('@/views/terminal/mistr/MistrOrdersOverview.vue'),
        },
      ],
    },
    // Legacy redirects
    { path: '/operator/login', redirect: '/terminal/login' },
    { path: '/operator', redirect: '/terminal' },
    { path: '/mistr/login', redirect: '/terminal/login' },
    { path: '/mistr', redirect: '/terminal' },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// Check auth once per session — avoids calling /auth/me on every navigation
let authInitialized = false

router.beforeEach(async (to) => {
  // Dynamic import avoids circular dep: router ↔ auth store
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()

  if (!authInitialized) {
    authInitialized = true
    if (!auth.isLoggedIn && !to.meta.public) {
      // Try to restore session from existing HttpOnly cookie
      // Skip on public pages (terminal-login) — no cookie expected
      await auth.fetchMe()
    }
  }

  if (!to.meta.public && !auth.isLoggedIn) {
    // Terminal routes → terminal PIN login
    if (to.matched.some(r => r.meta.terminal)) {
      return { name: 'terminal-login' }
    }
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && auth.isLoggedIn) {
    return { name: 'workspace' }
  }
})

export default router
