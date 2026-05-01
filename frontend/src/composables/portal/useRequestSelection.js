import { ref, reactive, computed } from 'vue'

/**
 * Season/episode selection state for the RequestModal.
 *
 * Handles three intertwined concerns:
 *  - Which seasons/episodes the user has picked (the `selectedSeasons`
 *    Map keyed by season number; values are 'full' or an explicit list
 *    of episode numbers).
 *  - Which seasons/episodes are already on Emby (the `availabilityMap`,
 *    fed by the /availability/tv/{id}/episodes endpoint).
 *  - How the two interact: available items are never selectable, and
 *    "toggle season" skips them so we never re-request episodes the
 *    library already has.
 *
 * Kept outside the SFC to stay under the 300-line rule and because
 * the logic is reusable for any future "edit my pending request" flow.
 */
export function useRequestSelection() {
  const seasons = ref([])
  const episodesMap = ref({})
  // availabilityMap[seasonNumber] = Set<episodeNumber> already in Emby.
  const availabilityMap = ref({})
  // ignoredMap[seasonNumber]     = Set<episodeNumber> ignored by the
  // admin in the Watchlist module. Treated as "locked" for selection
  // purposes but rendered with a dedicated grey tag.
  const ignoredMap = ref({})
  const selectedSeasons = reactive(new Map())
  const expanded = reactive(new Set())

  function getEpisodes(sNum) {
    return episodesMap.value[sNum] || []
  }

  function availableSet(sNum) {
    return availabilityMap.value[sNum] || null
  }

  function ignoredSet(sNum) {
    return ignoredMap.value[sNum] || null
  }

  function isEpisodeAvailable(sNum, epNum) {
    const set = availableSet(sNum)
    return !!(set && set.has(epNum))
  }

  function isEpisodeIgnored(sNum, epNum) {
    const set = ignoredSet(sNum)
    return !!(set && set.has(epNum))
  }

  // "Locked" = can't be requested (already in Emby, or ignored by admin).
  // Used to gate checkbox enablement and to decide whether a whole
  // season is effectively done.
  function isEpisodeLocked(sNum, epNum) {
    return isEpisodeAvailable(sNum, epNum) || isEpisodeIgnored(sNum, epNum)
  }

  function seasonAvailableCount(sNum) {
    const set = availableSet(sNum)
    return set ? set.size : 0
  }

  function seasonIgnoredCount(sNum) {
    const set = ignoredSet(sNum)
    return set ? set.size : 0
  }

  function seasonLockedCount(sNum) {
    return seasonAvailableCount(sNum) + seasonIgnoredCount(sNum)
  }

  function isSeasonFullyAvailable(sNum) {
    const s = seasons.value.find(x => x.number === sNum)
    if (!s || !s.episodes) return false
    return seasonLockedCount(sNum) >= s.episodes
  }

  // Show the orange "Partially available" pill when at least one episode
  // is locked (available or ignored) AND at least one episode is still
  // requestable. Either-extreme cases (all locked / all missing) don't
  // qualify as "partial".
  const partialAvailability = computed(() => {
    let anyLocked = false
    let anyMissing = false
    for (const s of seasons.value) {
      const locked = seasonLockedCount(s.number)
      if (locked > 0) anyLocked = true
      if (locked < (s.episodes || 0)) anyMissing = true
      if (anyLocked && anyMissing) return true
    }
    return false
  })

  function isSeasonSelected(sNum) {
    return selectedSeasons.has(sNum) && selectedSeasons.get(sNum) === 'full'
  }

  function isEpisodeSelected(sNum, epNum) {
    if (isEpisodeLocked(sNum, epNum)) return false
    const sel = selectedSeasons.get(sNum)
    if (sel === 'full') return true
    if (Array.isArray(sel)) return sel.includes(epNum)
    return false
  }

  function hasAnyEpisodeSelected(sNum) {
    const sel = selectedSeasons.get(sNum)
    return sel === 'full' || (Array.isArray(sel) && sel.length > 0)
  }

  // When a season has some episodes locked (either on Emby already
  // or ignored by admin), checking the season checkbox should only
  // select the MISSING episodes — never attempt to re-request what's
  // already there or what was explicitly ignored.
  function missingEpisodesIn(sNum) {
    return getEpisodes(sNum)
      .map(e => e.number)
      .filter(n => !isEpisodeLocked(sNum, n))
  }

  function toggleSeason(sNum) {
    if (isSeasonFullyAvailable(sNum)) return
    if (isSeasonSelected(sNum) || hasAnyEpisodeSelected(sNum)) {
      selectedSeasons.delete(sNum)
      return
    }
    const missing = missingEpisodesIn(sNum)
    const total = getEpisodes(sNum).length
    // If nothing is already on Emby we can send "all" shorthand; otherwise
    // we enumerate only the missing episode numbers to avoid re-requesting
    // ones the library already has.
    if (missing.length === total) {
      selectedSeasons.set(sNum, 'full')
    } else if (missing.length > 0) {
      selectedSeasons.set(sNum, missing)
    }
  }

  function toggleEpisode(sNum, epNum) {
    if (isEpisodeLocked(sNum, epNum)) return
    const sel = selectedSeasons.get(sNum)
    if (sel === 'full') {
      const allEps = missingEpisodesIn(sNum).filter(n => n !== epNum)
      selectedSeasons.set(sNum, allEps)
      return
    }
    if (Array.isArray(sel)) {
      if (sel.includes(epNum)) {
        const filtered = sel.filter(n => n !== epNum)
        if (filtered.length === 0) selectedSeasons.delete(sNum)
        else selectedSeasons.set(sNum, filtered)
      } else {
        const updated = [...sel, epNum]
        const missing = missingEpisodesIn(sNum)
        if (missing.length > 0 && updated.length >= missing.length) {
          // All missing episodes picked — collapse into "full" only when
          // the entire season is also missing (so the backend gets the
          // most compact payload). Otherwise keep the explicit list.
          const total = getEpisodes(sNum).length
          selectedSeasons.set(sNum, missing.length === total ? 'full' : updated)
        } else {
          selectedSeasons.set(sNum, updated)
        }
      }
      return
    }
    selectedSeasons.set(sNum, [epNum])
  }

  function toggleExpand(sNum) {
    if (expanded.has(sNum)) expanded.delete(sNum)
    else expanded.add(sNum)
  }

  function hasAnySelection() {
    for (const sel of selectedSeasons.values()) {
      if (sel === 'full') return true
      if (Array.isArray(sel) && sel.length > 0) return true
    }
    return false
  }

  // "Requestable" = seasons that still have at least one episode the
  // user could ask for (i.e. not fully available and not fully ignored).
  // Used by the "Select all" shortcut above the season list.
  function requestableSeasons() {
    return seasons.value.filter(s => {
      if (!s.episodes) return false
      return seasonLockedCount(s.number) < s.episodes
    })
  }

  const hasAnyRequestable = computed(() => requestableSeasons().length > 0)

  const allRequestableSelected = computed(() => {
    const list = requestableSeasons()
    if (!list.length) return false
    for (const s of list) {
      const sel = selectedSeasons.get(s.number)
      const picked = sel === 'full' || (Array.isArray(sel) && sel.length > 0)
      if (!picked) return false
    }
    return true
  })

  function toggleSelectAll() {
    if (allRequestableSelected.value) {
      for (const s of requestableSeasons()) {
        selectedSeasons.delete(s.number)
      }
      return
    }
    for (const s of requestableSeasons()) {
      if (isSeasonSelected(s.number)) continue
      // Use the same shortcut-selection logic as toggleSeason so
      // partially-locked seasons only get their missing episodes.
      if (hasAnyEpisodeSelected(s.number)) continue
      const missing = missingEpisodesIn(s.number)
      const total = getEpisodes(s.number).length
      if (missing.length === total || total === 0) {
        selectedSeasons.set(s.number, 'full')
      } else if (missing.length > 0) {
        selectedSeasons.set(s.number, missing)
      }
    }
  }

  function setAvailability(availMap, ignMap = {}) {
    availabilityMap.value = availMap
    ignoredMap.value = ignMap
  }

  return {
    seasons,
    episodesMap,
    selectedSeasons,
    expanded,
    getEpisodes,
    isEpisodeAvailable,
    isEpisodeIgnored,
    isEpisodeLocked,
    seasonAvailableCount,
    seasonIgnoredCount,
    seasonLockedCount,
    isSeasonFullyAvailable,
    partialAvailability,
    isSeasonSelected,
    isEpisodeSelected,
    toggleSeason,
    toggleEpisode,
    toggleExpand,
    hasAnySelection,
    hasAnyRequestable,
    allRequestableSelected,
    toggleSelectAll,
    setAvailability,
  }
}
