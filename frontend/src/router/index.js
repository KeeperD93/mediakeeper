import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { fetchApiResponse } from '@/composables/useApi'
import { adminRoutes } from './routes/admin'
import { portalRoutes } from './routes/portal'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, titleKey: 'login.title' },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: adminRoutes,
  },
  {
    path: '/portal/login',
    redirect: (to) => ({
      name: 'login',
      query: {
        redirect: typeof to.query.redirect === 'string' ? to.query.redirect : '/portal',
      },
    }),
  },
  {
    // Requests module root.
    path: '/portal',
    component: () => import('@/components/portal/PortalLayout.vue'),
    meta: { requiresPortalAuth: true },
    children: portalRoutes,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard
// - Portal routes accept either an rq_token session or, for a logged-in
//   backoffice admin, an auto-provisioned Portal session.
// - MediaKeeper routes still require the regular mk_token session.
router.beforeEach(async (to) => {
  // Fully public (login pages, etc.) — let them through.
  if (to.meta.public) return true

  // --- Portal branch ---------------------------------------------------
  if (to.meta.requiresPortalAuth) {
    const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
    const portalAuth = usePortalAuth()
    const { isPortalAuth, checkPortalAuth } = portalAuth
    if (isPortalAuth.value) return true
    let ok = await checkPortalAuth()
    if (ok) return true

    const { checkAuth, isAuthenticated } = useAuth()
    const isAdmin = isAuthenticated.value || await checkAuth()
    if (isAdmin) {
      try {
        const res = await fetchApiResponse('/api/portal/admin/requests/enter', {
          method: 'POST',
        })
        if (res.ok) {
          ok = await portalAuth.checkPortalAuth()
          if (ok) return true
        }
      } catch {
        // Fall through to the shared login page.
      }
    }

    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // --- MediaKeeper branch ----------------------------------------------
  const { checkAuth, isAuthenticated } = useAuth()
  if (isAuthenticated.value) return true
  const ok = await checkAuth()
  if (!ok) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router
