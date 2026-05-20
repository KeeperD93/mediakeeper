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
    redirect: to => ({
      name: 'login',
      query: {
        redirect: typeof to.query.redirect === 'string' ? to.query.redirect : '/portal',
      },
    }),
  },
  {
    // Portal root.
    path: '/portal',
    component: () => import('@/components/portal/PortalLayout.vue'),
    meta: { requiresPortalAuth: true },
    children: portalRoutes,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true, titleKey: 'errors.notFoundTitle' },
  },
]

// Dev-only visual matrix for the PosterCard component. Gated behind
// import.meta.env.DEV so the route never reaches a production bundle
// (Vite strips both the import and the entry under `npm run build`).
// Inserted before the catch-all, otherwise the wildcard would swallow it.
if (import.meta.env.DEV) {
  const catchAllIdx = routes.findIndex(r => r.name === 'not-found')
  const devRoute = {
    path: '/portal/_dev/posters',
    name: 'portal-dev-posters',
    component: () => import('@/views/portal/PosterCardPreview.vue'),
    meta: { public: true },
  }
  if (catchAllIdx >= 0) routes.splice(catchAllIdx, 0, devRoute)
  else routes.push(devRoute)
}

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      // Some pages (PortalSettings tabs) use ``#identity`` / ``#appearance``
      // / ... as state markers — they don't map to a DOM anchor. Skip the
      // scroll silently when nothing matches so Vue Router doesn't log a
      // "couldn't find element" warning on every tab switch.
      if (typeof document !== 'undefined' && document.querySelector(to.hash)) {
        return { el: to.hash, behavior: 'smooth' }
      }
      return false
    }
    return { top: 0, behavior: 'instant' }
  },
})

// Auth guard
// - Portal routes accept either an rq_token session or, for a logged-in
//   backoffice admin, an auto-provisioned Portal session.
// - MediaKeeper routes still require the regular mk_token session.
// - When ``maintenance.enabled`` is on, every non-admin portal navigation
//   is redirected to /portal/maintenance. Admins keep full access.
router.beforeEach(async to => {
  // Portal maintenance gate — runs before auth so anonymous visitors
  // land on the holding page instead of the login screen. The target
  // page itself (``portal-maintenance``) is whitelisted to avoid loops.
  if (to.meta.portal && to.name !== 'portal-maintenance') {
    const { useMaintenance } = await import('@/composables/portal/useMaintenance')
    const { fetchMaintenanceState } = useMaintenance()
    const state = await fetchMaintenanceState()
    if (state?.enabled) {
      const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
      const portalAuth = usePortalAuth()
      if (!portalAuth.isPortalAuth.value) {
        await portalAuth.checkPortalAuth()
      }
      const role = portalAuth.profile.value?.role
      if (role !== 'admin') {
        return { name: 'portal-maintenance' }
      }
    }
  }

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
    const isAdmin = isAuthenticated.value || (await checkAuth())
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
