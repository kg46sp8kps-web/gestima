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
    if (!auth.isLoggedIn) {
      // Try to restore session from existing HttpOnly cookie
      await auth.fetchMe()
    }
  }

  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && auth.isLoggedIn) {
    return { name: 'workspace' }
  }
})

export default router
