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

  // Protected routes
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/dashboard/DashboardView.vue'),
    meta: {
      title: 'Dashboard'
    }
  },

  // Work Centers (Admin only - accessed via /admin/master-data)
  {
    path: '/admin/work-centers/new',
    name: 'work-center-create',
    component: () => import('@/views/workCenters/WorkCenterEditView.vue'),
    meta: {
      title: 'Nové pracoviště',
      requiresAdmin: true
    }
  },
  {
    path: '/admin/work-centers/:workCenterNumber',
    name: 'work-center-edit',
    component: () => import('@/views/workCenters/WorkCenterEditView.vue'),
    meta: {
      title: 'Úprava pracoviště',
      requiresAdmin: true
    }
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

  // Admin
  {
    path: '/admin/master-data',
    name: 'admin-master-data',
    component: () => import('@/views/admin/MasterDataView.vue'),
    meta: {
      title: 'Kmenová data',
      requiresAdmin: true
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

  // Windows (floating windows)
  {
    path: '/windows',
    name: 'windows',
    component: () => import('@/views/windows/WindowsView.vue'),
    meta: {
      title: 'Windows'
    }
  },

  // Catch-all 404 - redirect to dashboard
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
    console.log('[Router] Unauthenticated - redirecting to login')
    return next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
  }

  // Redirect to dashboard if already logged in and trying to access login
  if (to.name === 'login' && auth.isAuthenticated) {
    const redirectPath = to.query.redirect as string
    if (redirectPath) {
      console.log(`[Router] Already authenticated - redirecting to ${redirectPath}`)
      return next(redirectPath)
    }
    console.log('[Router] Already authenticated - redirecting to dashboard')
    return next({ name: 'dashboard' })
  }

  // Check admin access
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    console.warn('[Router] Admin access required - redirecting to dashboard')
    return next({ name: 'dashboard' })
  }

  // Check operator access
  if (to.meta.requiresOperator && !auth.isOperator) {
    console.warn('[Router] Operator access required - redirecting to dashboard')
    return next({ name: 'dashboard' })
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
