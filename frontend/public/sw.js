const CACHE_NAME = 'mk-demandes-v2'
const PRECACHE = ['/demandes', '/manifest.json']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // addAll is atomic — any single failure aborts the whole install.
      // Use individual puts so a missing precache entry (e.g. /manifest.json
      // during a broken dev build) doesn't break the SW install.
      Promise.all(
        PRECACHE.map((url) =>
          fetch(url).then((res) => (res.ok ? cache.put(url, res) : null)).catch(() => null)
        )
      )
    )
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Dev mode: never intercept. Vite's HMR, chunk loading, and navigation
  // all break if the SW sits in the middle. We only add value in prod.
  if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') return

  // Only handle same-origin requests — skip cross-origin (TMDB images, etc.)
  if (url.origin !== self.location.origin) return

  // API calls: network only, never cache
  if (url.pathname.startsWith('/api/')) return

  // Navigation: network first, fall back to cached shell, and as a
  // last resort return a plain Response so we never reject respondWith
  // (which is what turned the page blank: respondWith(undefined) → net error).
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .catch(() =>
          caches.match('/demandes').then(
            (cached) => cached || new Response('', { status: 504, statusText: 'Offline' })
          )
        )
    )
    return
  }

  // Same-origin assets: cache first, then network
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached
      return fetch(request)
        .then((response) => {
          if (response.ok && url.pathname.startsWith('/assets/')) {
            const clone = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          }
          return response
        })
        .catch(() => new Response('', { status: 504, statusText: 'Offline' }))
    })
  )
})

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return
  const data = event.data.json()
  event.waitUntil(
    self.registration.showNotification(data.title || 'Demandes', {
      body: data.body || '',
      icon: '/assets/icons/mediakeeper.png',
      badge: '/assets/icons/mediakeeper.png',
      data: data.url ? { url: data.url } : undefined,
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/demandes'
  event.waitUntil(clients.openWindow(url))
})
