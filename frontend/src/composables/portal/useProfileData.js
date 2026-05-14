import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useRequestStatus } from '@/composables/portal/useRequestStatus'
import { TROPHY_STATUS } from '@/constants/achievements'

const SHOWN_TROPHY_TOAST_KEY = 'portal_shown_trophy_unlocks_v1'

function getShownTrophyIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SHOWN_TROPHY_TOAST_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

export function markTrophyShown(id) {
  if (id == null) return
  const ids = getShownTrophyIds()
  ids.add(id)
  // Cap at 50 IDs so the storage entry never grows unbounded across years.
  localStorage.setItem(SHOWN_TROPHY_TOAST_KEY, JSON.stringify([...ids].slice(-50)))
}

/**
 * Profile-page data loader — owns every ref the Portal profile page
 * mounts in parallel (stats, ranking, trophies, recommendation
 * carousels, continue-watching strip).
 *
 * Loading is split in two waves:
 *   1. **core** (``loading``): the "above the fold" payload — stats,
 *      ranking, trophies, recent/my/next lists. The page renders as
 *      soon as this is in so the KPI count-up animations fire quickly.
 *   2. **lists** (``loadingLists``): recommendation carousels, continue
 *      watching, availability + request-status cache warming. These
 *      pieces fill in behind the hero without blocking it.
 */
export function useProfileData() {
  const { apiGet } = useApi()
  const { checkAvailability } = useAvailability()
  const { checkStatus: checkRequestStatus } = useRequestStatus()

  const loading = ref(true)
  const loadingLists = ref(true)
  const hero = ref(null)
  const stats = ref({
    total_plays: 0,
    total_minutes: 0,
    streak: 0,
    record_day: { date: null, count: 0 },
    most_rewatched: null,
    most_rewatched_movie: null,
    most_rewatched_series: null,
    top_genres: [],
    day_stats: null,
  })
  const recoItems = ref([])
  const genreIds = ref([])
  const recentWatches = ref([])
  const myRequests = ref([])
  const nextToFinish = ref([])
  const continueWatching = ref([])
  const ranking = ref({ position: 0, total: 0, percentile: 0, movement: 0, leaderboard: [] })
  const titleKey = ref('spectator')
  const rankTier = ref('bronze')
  const trophies = ref({ items: [], unlocked_count: 0, total_count: 0, next_achievement: null })
  // Trophy unlocked in the last 5 min — the SFC wires this into the
  // useTrophyDisplay toast ref (owning that state there would create
  // two sources of truth).
  const recentUnlock = ref(null)

  const recommended = ref([])
  const becauseYouWatchedTv = ref({ pivot: null, items: [] })
  const becauseYouWatchedMovie = ref({ pivot: null, items: [] })
  const preferencesBased = ref([])

  async function _loadCore() {
    const [profileRes, trophyRes] = await Promise.all([
      apiGet('/api/portal/catalog/profile-full').catch(() => null),
      apiGet('/api/portal/achievements/me').catch(() => null),
    ])

    if (profileRes) {
      stats.value = profileRes.stats || stats.value
      ranking.value = profileRes.ranking || ranking.value
      titleKey.value = profileRes.title_key || 'spectator'
      rankTier.value = profileRes.rank_tier || 'bronze'
      recentWatches.value = (profileRes.recent_watches || []).map(w => ({
        ...w,
        id: w.emby_item_id,
        poster: w.poster_url,
      }))
      myRequests.value = (profileRes.my_requests || []).map(r => ({
        ...r,
        id: r.tmdb_id,
        poster: r.poster_url,
        _request_status: r.status,
        _retry_count: r.retry_count || 0,
        _reject_reason: r.reject_reason || null,
      }))
      nextToFinish.value = (profileRes.next_to_finish || []).map(n => ({
        ...n,
        id: n.emby_item_id,
        poster: n.poster_url,
      }))
    }
    if (trophyRes) {
      trophies.value = {
        items: trophyRes.items || [],
        unlocked_count: trophyRes.unlocked_count || 0,
        total_count: trophyRes.total_count || 0,
        next_achievement: trophyRes.next_achievement || null,
      }
      const now = Date.now()
      const shownIds = getShownTrophyIds()
      recentUnlock.value =
        (trophyRes.items || []).find(
          a =>
            a.status === TROPHY_STATUS.UNLOCKED &&
            a.unlocked_at &&
            !shownIds.has(a.id) &&
            now - new Date(a.unlocked_at).getTime() < 300000,
        ) || null
    }
  }

  async function _loadLists() {
    const [recoRes, continueRes, homeRecoRes, bywTvRes, bywMovieRes, prefRes] = await Promise.all([
      apiGet('/api/portal/catalog/recommendations-full').catch(() => null),
      apiGet('/api/portal/library/continue?limit=10').catch(() => null),
      apiGet('/api/portal/catalog/recommended-for-me').catch(() => null),
      apiGet('/api/portal/catalog/because-you-watched?media_type=tv').catch(() => null),
      apiGet('/api/portal/catalog/because-you-watched?media_type=movie').catch(() => null),
      apiGet('/api/portal/catalog/preferences-based').catch(() => null),
    ])

    if (recoRes) {
      hero.value = recoRes.hero || null
      recoItems.value = recoRes.items || []
      genreIds.value = recoRes.genre_ids || []
    }
    if (continueRes) continueWatching.value = continueRes.items || []
    if (homeRecoRes) recommended.value = homeRecoRes.items || []
    if (bywTvRes) {
      becauseYouWatchedTv.value = {
        pivot: bywTvRes.pivot || null,
        items: bywTvRes.items || [],
      }
    }
    if (bywMovieRes) {
      becauseYouWatchedMovie.value = {
        pivot: bywMovieRes.pivot || null,
        items: bywMovieRes.items || [],
      }
    }
    if (prefRes) preferencesBased.value = prefRes.items || []

    // Warm availability + request-status caches so every carousel's
    // cards render with the right dots / badges without each one
    // firing its own batch request.
    const enrich = [
      ...recoItems.value,
      ...recommended.value,
      ...(becauseYouWatchedTv.value.items || []),
      ...(becauseYouWatchedMovie.value.items || []),
      ...preferencesBased.value,
      ...myRequests.value,
    ]
    if (enrich.length) {
      await Promise.all([checkAvailability(enrich), checkRequestStatus(enrich)])
    }
  }

  async function load() {
    loading.value = true
    loadingLists.value = true
    try {
      await _loadCore()
    } finally {
      loading.value = false
    }
    // Fire the secondary wave in the background — don't await it so
    // the caller can already render the profile card + KPIs. The
    // `loadingLists` flag lets sections show a skeleton in the meantime.
    _loadLists().finally(() => {
      loadingLists.value = false
    })
  }

  return {
    loading,
    loadingLists,
    hero,
    stats,
    recoItems,
    genreIds,
    recentWatches,
    myRequests,
    nextToFinish,
    continueWatching,
    ranking,
    titleKey,
    rankTier,
    trophies,
    recentUnlock,
    markTrophyShown,
    recommended,
    becauseYouWatchedTv,
    becauseYouWatchedMovie,
    preferencesBased,
    load,
  }
}
