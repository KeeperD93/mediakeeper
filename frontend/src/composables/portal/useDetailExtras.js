import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

/**
 * Fetches the "by director", "with actor" and "in franchise" carousels
 * that sit below the media detail page. Kept out of the view so the
 * Vue SFC stays under the 300-line cap.
 */
export function useDetailExtras() {
  const { apiGet } = useApi()

  const directorFilmo = ref({ items: [] })
  const actorFilmo = ref({ items: [] })
  const collection = ref(null)

  function reset() {
    directorFilmo.value = { items: [] }
    actorFilmo.value = { items: [] }
    collection.value = null
  }

  async function load(media) {
    if (!media) { reset(); return }
    const directorId = media.directors?.[0]?.id
    const actorId = media.cast?.[0]?.id
    const collectionId = media.collection?.id
    const [dir, act, col] = await Promise.all([
      directorId ? apiGet(`/api/portal/catalog/person/${directorId}?role=director`).catch(() => null) : null,
      actorId ? apiGet(`/api/portal/catalog/person/${actorId}?role=acting`).catch(() => null) : null,
      collectionId ? apiGet(`/api/portal/catalog/collection/${collectionId}`).catch(() => null) : null,
    ])
    const currentId = media.tmdb_id || media.id
    const isSameAsCurrent = it => (it.tmdb_id || it.id) === currentId
    if (dir?.items) directorFilmo.value = { items: dir.items.filter(i => !isSameAsCurrent(i)) }
    if (act?.items) actorFilmo.value = { items: act.items.filter(i => !isSameAsCurrent(i)) }
    if (col) collection.value = { ...col, items: (col.items || []).filter(i => !isSameAsCurrent(i)) }
  }

  return { directorFilmo, actorFilmo, collection, load, reset }
}
