/**
 * GESTIMA Vue Router
 *
 * Routes, navigation guards, and access control.
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// ============================================================================
// ROUTE DEFINITIONS
// ============================================================================

const routes: RouteRecordRaw[] = [
  // Public routes
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: {
      public: true,
      title: 'Přihlášení'
    }
  },

  // Default — redirect to workspace
  {
    path: '/',
    redirect: '/workspace'
  },

  // Partners
  {
    path: '/partners',
    name: 'partners',
    component: () => import('@/views/partners/PartnersView.vue'),
    meta: {
      title: 'Partneři'
    }
  },

  // Settings
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/settings/SettingsView.vue'),
    meta: {
      title: 'Nastavení'
    }
  },

  // Workspace (tiling layout)
  {
    path: '/workspace',
    name: 'workspace',
    component: () => import('@/components/tiling/TilingWorkspace.vue'),
    meta: {
      title: 'Workspace'
    }
  },

  // Legacy redirect
  {
    path: '/windows',
    redirect: '/workspace'
  },

  // Catch-all 404 - redirect to workspace
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// ============================================================================
// ROUTER INSTANCE
// ============================================================================

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Restore scroll position on back/forward
    if (savedPosition) {
      return savedPosition
    }
    // Scroll to top on new routes
    return { top: 0 }
  }
})

// ============================================================================
// NAVIGATION GUARDS
// ============================================================================

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // Fetch user if not loaded yet (app init)
  if (!auth.user && !to.meta.public) {
    try {
      await auth.fetchCurrentUser()
    } catch (err) {
      // User not authenticated - will redirect below
    }
  }

  // Check authentication
  if (!to.meta.public && !auth.isAuthenticated) {
    return next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
  }

  // Redirect to windows if already logged in and trying to access login
  if (to.name === 'login' && auth.isAuthenticated) {
    const redirectPath = to.query.redirect as string
    if (redirectPath) {
      return next(redirectPath)
    }
    return next({ name: 'workspace' })
  }

  // Check admin access
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    console.warn('[Router] Admin access required - redirecting to workspace')
    return next({ name: 'workspace' })
  }

  // Check operator access
  if (to.meta.requiresOperator && !auth.isOperator) {
    console.warn('[Router] Operator access required - redirecting to workspace')
    return next({ name: 'workspace' })
  }

  // Update document title
  if (to.meta.title) {
    document.title = `${to.meta.title} | GESTIMA`
  } else {
    document.title = 'GESTIMA'
  }

  next()
})

// ============================================================================
// TYPES - Route Meta
// ============================================================================

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    title?: string
    requiresAdmin?: boolean
    requiresOperator?: boolean
  }
}

export default router
