<template>
  <PortalDiscoverPage :key="$route.params.slug" :title="title" :endpoint="endpoint" />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PortalDiscoverPage from './PortalDiscoverPage.vue'

// Single source of truth for provider slugs <-> TMDB IDs + display
// name. Mirrors the platform lists in PortalHome.vue. The backend
// defaults to `watch_region=FR`, so we only set an explicit `region`
// when a platform is not available in France (e.g. Hulu is US-only)
// and we'd otherwise get an empty result set.
//
// To verify / update these IDs, hit:
//   GET /api/portal/catalog/watch-providers?region=FR&media_type=movie
const PROVIDERS = {
  // International majors
  netflix: { id: 8, name: 'Netflix' },
  prime: { id: 119, name: 'Prime Video' }, // FR: Amazon Prime Video
  disney: { id: 337, name: 'Disney+' },
  max: { id: 1899, name: 'Max' }, // FR: HBO Max (rebranded "Max")
  apple: { id: 350, name: 'Apple TV+' },
  paramount: { id: 531, name: 'Paramount+' },
  // French & specialised
  crunchyroll: { id: 283, name: 'Crunchyroll' },
  adn: { id: 415, name: 'ADN' }, // FR: Animation Digital Network
  canal: { id: 381, name: 'Canal+' },
  arte: { id: 234, name: 'Arte' },
  mubi: { id: 11, name: 'MUBI' },
  tf1plus: { id: 1754, name: 'TF1+' },
  // US-only — Hulu has no FR watch_region in TMDB. Without the
  // override, the page would always be empty for French users.
  hulu: { id: 15, name: 'Hulu', region: 'US' },
}

const route = useRoute()

const provider = computed(() => PROVIDERS[route.params.slug] || PROVIDERS.netflix)
const title = computed(() => provider.value.name)
const endpoint = computed(() => {
  const base = `/api/portal/catalog/browse-provider/${provider.value.id}`
  // Only append `?region=...` when the provider explicitly overrides
  // it; otherwise the backend's FR default kicks in.
  const region = provider.value.region
  return region ? `${base}?region=${region}` : base
})
</script>
