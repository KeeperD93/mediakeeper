/**
 * All the data-loading + hero-rotation plumbing for the Portal home.
 *
 * The home page renders ~15 horizontal carousels plus a rotating hero
 * banner. Keeping this many refs + the Promise.all loader + the hero
 * interval all in the view file pushed it well past the 300-line rule.
 * This composable owns the state and the refresh cycle; the view stays
 * focused on layout + user interactions.
 */
import { ref, computed, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'

// Minimum dwell time between two hero items — covers the background
// rotation interval AND the throttle applied to early ``video-ended``
// events. Tuned at 45 s so the YouTube IFrame backend doesn't see a
// barrage of ``player.loadVideoById`` calls when short trailers chain
// together, which used to trip YouTube's anti-abuse cooldown on this
// domain.
const HERO_MIN_INTERVAL_MS = 45000

export function usePortalHomeData() {
  const { apiGet } = useApi()
  const { checkAvailability, getAvailability } = useAvailability()
  const { checkStatus: checkRequestStatus, clearCache: clearRequestCache } = useRequestStatus()

  // Carousel sources (one ref per row so Vue can react granularly
  // and we avoid re-rendering the whole page when any single endpoint
  // responds). Names mirror backend endpoints for easier tracing.
  const trending = ref([])
  const featured = ref([])
  const top20 = ref([])
  const popularMovies = ref([])
  const popularTv = ref([])
  const recentEmby = ref([])
  const upcoming = ref([])
  const topRatedYear = ref([])
  const recommended = ref([])
  const oscars = ref([])
  const family = ref([])
  const animation = ref([])
  const becauseYouWatched = ref({ pivot: null, items: [] })
  const loadingAll = ref(true)

  // Admin-configurable hero size (0 = hidden, 20 = max). Featured items
  // eat into this budget: if hero_trend_count is 15 and there are 3
  // featured, only 12 trending slots remain. Default 10 until the
  // backend responds with the real value.
  const heroTrendCount = ref(10)
  const heroIndex = ref(0)
  const heroPaused = ref(false)
  let heroTimer = null
  // Tracks the last actual ``heroIndex`` switch so ``nextHero`` can
  // delay an early ``video-ended`` to honour HERO_MIN_INTERVAL_MS.
  let lastHeroSwitchTs = Date.now()
  let pendingNextHeroTimer = null

  // Hero: manual featured first, then trending. `heroTrendCount` caps
  // the total items. Featured items take priority and eat into the
  // trending quota so setting the count to 15 with 3 featured leaves
  // 12 trending slots.
  const heroItems = computed(() => {
    const cap = heroTrendCount.value
    if (cap <= 0) return []
    const manual = featured.value.filter(f => f.active !== false)
    const auto = trending.value.filter(tr => !manual.some(m => m.tmdb_id === (tr.tmdb_id || tr.id)))
    return [...manual, ...auto].slice(0, cap)
  })

  const featuredCount = computed(() => featured.value.filter(f => f.active !== false).length)

  function advanceHero() {
    if (heroItems.value.length <= 1) return
    heroIndex.value = (heroIndex.value + 1) % heroItems.value.length
    lastHeroSwitchTs = Date.now()
    pendingNextHeroTimer = null
  }

  // Manual jump from the dot strip — refresh the anti-skip sentinel and
  // cancel any pending early rotation so the user always sees the full
  // HERO_MIN_INTERVAL_MS window on the slide they picked.
  function gotoHero(index) {
    const items = heroItems.value
    if (items.length <= 1) return
    if (!Number.isInteger(index) || index < 0 || index >= items.length) return
    if (pendingNextHeroTimer) {
      clearTimeout(pendingNextHeroTimer)
      pendingNextHeroTimer = null
    }
    heroIndex.value = index
    lastHeroSwitchTs = Date.now()
  }

  function startHeroRotation() {
    stopHeroRotation()
    heroTimer = setInterval(() => {
      if (heroItems.value.length > 1 && !heroPaused.value) {
        nextHero()
      }
    }, HERO_MIN_INTERVAL_MS)
  }
  function stopHeroRotation() {
    if (heroTimer) {
      clearInterval(heroTimer)
      heroTimer = null
    }
    if (pendingNextHeroTimer) {
      clearTimeout(pendingNextHeroTimer)
      pendingNextHeroTimer = null
    }
  }
  function nextHero() {
    if (heroItems.value.length <= 1) return
    if (pendingNextHeroTimer) return
    const elapsed = Date.now() - lastHeroSwitchTs
    const delay = Math.max(0, HERO_MIN_INTERVAL_MS - elapsed)
    if (delay === 0) {
      advanceHero()
    } else {
      pendingNextHeroTimer = setTimeout(advanceHero, delay)
    }
  }

  // Back-fill emby_url / availability on a list after its availability
  // check has resolved. Hero strips read these fields directly instead
  // of going through `getAvailability(id)` on every render.
  function stampAvailability(list) {
    list.forEach(it => {
      const id = it.tmdb_id || it.id
      if (!id) return
      const av = getAvailability(id)
      if (av) {
        it.emby_url = av.emby_url || it.emby_url
        it.availability = av.availability || it.availability
      }
    })
  }

  async function loadAllData() {
    // Reset the request-status cache so each Home visit re-fetches
    // fresh data from the backend. This is how the admin's latest
    // `anonymize_requests` toggle reaches connected users without
    // requiring a full page reload on their side.
    clearRequestCache()
    loadingAll.value = true

    // Fire every endpoint in parallel but apply each result AS SOON
    // as it resolves — the slowest request no longer blocks the rest
    // of the page. Each row renders the moment its source is ready.
    const runRow = async (url, target, { isHeroList = false, extraApply } = {}) => {
      const data = await apiGet(url).catch(() => null)
      const items = data?.items || []
      target.value = items
      if (extraApply) extraApply(data)
      if (items.length) {
        await Promise.all([checkAvailability(items), checkRequestStatus(items)])
        // Hero strips (featured / trending / recentEmby) embed the
        // emby_url + availability on each item so the banner can render
        // the "Regarder" CTA without going through the availability
        // cache on each keypress. Other rows pull those fields on demand.
        if (isHeroList) stampAvailability(target.value)
      }
    }

    const tasks = [
      runRow('/api/portal/featured', featured, {
        isHeroList: true,
        extraApply: d => {
          if (d?.hero_trend_count != null) heroTrendCount.value = d.hero_trend_count
        },
      }),
      runRow('/api/portal/catalog/trending', trending, { isHeroList: true }),
      runRow('/api/portal/top20', top20),
      runRow('/api/portal/catalog/popular', popularMovies),
      runRow('/api/portal/catalog/popular-tv', popularTv),
      runRow('/api/portal/library/recent', recentEmby, { isHeroList: true }),
      runRow('/api/portal/catalog/upcoming', upcoming),
      runRow('/api/portal/catalog/top-rated-year', topRatedYear),
      runRow('/api/portal/catalog/recommended-for-me', recommended),
      runRow('/api/portal/catalog/oscars', oscars),
      runRow('/api/portal/catalog/family', family),
      runRow('/api/portal/catalog/category/animation?page=1&sort=popularity', animation),
      // because-you-watched returns a non-standard shape: { pivot, items }
      (async () => {
        const data = await apiGet('/api/portal/catalog/because-you-watched').catch(() => null)
        becauseYouWatched.value = data || { pivot: null, items: [] }
        const items = becauseYouWatched.value.items || []
        if (items.length) {
          await Promise.all([checkAvailability(items), checkRequestStatus(items)])
        }
      })(),
    ]

    // Start the hero rotation as soon as the first hero-capable source
    // (featured or trending) arrives — don't wait for the slowest row.
    Promise.race([
      tasks[0], // featured
      tasks[1], // trending
    ]).then(() => {
      startHeroRotation()
    })

    try {
      await Promise.all(tasks)
    } finally {
      loadingAll.value = false
    }
  }

  onUnmounted(stopHeroRotation)

  return {
    // Carousels
    trending,
    featured,
    top20,
    popularMovies,
    popularTv,
    recentEmby,
    upcoming,
    topRatedYear,
    recommended,
    oscars,
    family,
    animation,
    becauseYouWatched,
    loadingAll,
    // Hero
    heroItems,
    heroIndex,
    heroPaused,
    featuredCount,
    nextHero,
    gotoHero,
    startHeroRotation,
    stopHeroRotation,
    // Loader
    loadAllData,
  }
}
