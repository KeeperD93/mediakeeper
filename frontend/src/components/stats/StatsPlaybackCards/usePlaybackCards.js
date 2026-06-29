import { ref, computed, watch } from 'vue'

export function usePlaybackCards(playback, t, ticksToHours) {
  const rankCards = computed(() => {
    if (!playback.value) return []
    const cards = []
    cards.push({
      id: 'top_movies',
      type: 'rank',
      title: t('stats.topMovies'),
      unit: t('common.plays'),
      items: playback.value.top_movies,
      valKey: 'plays',
      imgKey: 'item_id',
    })
    cards.push({
      id: 'popular_movies',
      type: 'rank',
      title: t('stats.popularMovies'),
      unit: t('stats.users'),
      items: playback.value.popular_movies,
      valKey: 'users',
      imgKey: 'item_id',
    })
    cards.push({
      id: 'top_series',
      type: 'rank',
      title: t('stats.topSeries'),
      unit: t('stats.users'),
      items: playback.value.top_series,
      valKey: 'users',
      imgKey: 'series_id',
    })
    cards.push({
      id: 'popular_series',
      type: 'rank',
      title: t('stats.popularSeries'),
      unit: t('stats.users'),
      items: playback.value.popular_series,
      valKey: 'users',
      imgKey: 'series_id',
    })
    cards.push({
      id: 'top_watchers',
      type: 'rank',
      title: t('stats.topWatchers'),
      unit: t('common.hours'),
      items: playback.value.top_users_hours,
      valFn: it => ticksToHours(it.ticks),
      avatar: true,
    })
    cards.push({
      id: 'active_users',
      type: 'rank',
      title: t('stats.activeUsersCard'),
      unit: t('common.plays'),
      items: playback.value.top_users,
      valKey: 'plays',
      avatar: true,
    })
    cards.push({ id: 'donut', type: 'donut' })
    if (playback.value.top_transcode_users?.length)
      cards.push({
        id: 'top_transcode',
        type: 'rank',
        title: t('stats.topTranscode'),
        unit: t('common.plays'),
        items: playback.value.top_transcode_users,
        valKey: 'plays',
        avatar: true,
      })
    cards.push({
      id: 'libraries',
      type: 'rank',
      title: t('stats.libraries'),
      unit: t('common.plays'),
      items: playback.value.by_library,
      valKey: 'plays',
    })
    cards.push({ id: 'genre', type: 'genre' })
    if (playback.value.by_audio_language?.length)
      cards.push({
        id: 'audio_lang',
        type: 'rank',
        title: t('stats.audioLanguages'),
        unit: t('common.plays'),
        items: playback.value.by_audio_language,
        valKey: 'plays',
      })
    cards.push({
      id: 'clients',
      type: 'rank',
      title: t('stats.clients'),
      unit: t('common.plays'),
      items: playback.value.by_client,
      valKey: 'plays',
    })
    return cards
  })

  const customizeMode = ref(false)
  const cardOrder = ref(null)
  const dragIdx = ref(-1)
  const dragOverIdx = ref(-1)
  const orderedCards = computed(() => {
    const cards = rankCards.value
    if (!cards.length) return cards
    if (!cardOrder.value) return cards
    const order = cardOrder.value
    const ordered = []
    for (const id of order) {
      const c = cards.find(x => x.id === id)
      if (c) ordered.push(c)
    }
    for (const c of cards) if (!ordered.includes(c)) ordered.push(c)
    return ordered
  })
  watch(rankCards, cards => {
    if (!cardOrder.value && cards.length) cardOrder.value = cards.map(c => c.id)
  })

  function onDragStart(i, e) {
    dragIdx.value = i
    e.dataTransfer.effectAllowed = 'move'
  }
  function onDragOver(i) {
    dragOverIdx.value = i
  }
  function onDragEnd() {
    dragIdx.value = -1
    dragOverIdx.value = -1
  }
  function onDrop(toIdx) {
    const fromIdx = dragIdx.value
    if (fromIdx < 0 || fromIdx === toIdx) return
    const cards = orderedCards.value.map(c => c.id)
    const [moved] = cards.splice(fromIdx, 1)
    cards.splice(toIdx, 0, moved)
    cardOrder.value = cards
    dragIdx.value = -1
    dragOverIdx.value = -1
  }

  return {
    customizeMode,
    orderedCards,
    dragIdx,
    dragOverIdx,
    onDragStart,
    onDragOver,
    onDragEnd,
    onDrop,
  }
}
