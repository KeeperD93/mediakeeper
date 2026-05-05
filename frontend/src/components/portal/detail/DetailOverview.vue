<template>
  <section class="vmd2-section">
    <div class="vmd2-layout">
      <div>
        <h2>{{ $t('portal.detail.synopsis') }}</h2>
        <p class="vmd2-overview">{{ media.overview || $t('portal.detail.noOverview') }}</p>

        <template v-if="media.keywords?.length">
          <h3>{{ $t('portal.detail.keywords') }}</h3>
          <div class="vmd2-keyword-list">
            <span v-for="k in media.keywords.slice(0, 20)" :key="k" class="vmd2-keyword">
              {{ k }}
            </span>
          </div>
        </template>

        <template v-if="allProviders.length">
          <h3>{{ $t('portal.detail.whereToWatch') }}</h3>
          <div class="vmd2-provider-list">
            <div v-for="p in allProviders" :key="p.name" class="vmd2-provider" :title="p.name">
              <img v-if="p.logo" :src="p.logo" :alt="p.name" />
              <span v-else>{{ p.name.slice(0, 2) }}</span>
            </div>
          </div>
        </template>
      </div>

      <aside class="vmd2-sidebar">
        <h3>{{ $t('portal.detail.details') }}</h3>
        <dl class="vmd2-facts-list">
          <template v-if="media.status">
            <dt>{{ $t('portal.detail.status') }}</dt>
            <dd>{{ translatedStatus }}</dd>
          </template>
          <template v-if="media.release_date">
            <dt>{{ $t('portal.detail.releaseDate') }}</dt>
            <dd>{{ formatDate(media.release_date) }}</dd>
          </template>
          <template v-if="media.languages?.length">
            <dt>{{ $t('portal.detail.originalLanguage') }}</dt>
            <dd>{{ media.languages[0] }}</dd>
          </template>
          <template v-if="media.countries?.length">
            <dt>{{ $t('portal.detail.country') }}</dt>
            <dd>{{ media.countries.slice(0, 2).join(', ') }}</dd>
          </template>
          <template v-if="media.budget">
            <dt>{{ $t('portal.detail.budget') }}</dt>
            <dd>${{ formatMoney(media.budget) }}</dd>
          </template>
          <template v-if="media.revenue">
            <dt>{{ $t('portal.detail.revenue') }}</dt>
            <dd>${{ formatMoney(media.revenue) }}</dd>
          </template>
          <template v-if="media.seasons_count">
            <dt>{{ $t('portal.detail.seasons') }}</dt>
            <dd>{{ media.seasons_count }}</dd>
          </template>
          <template v-if="media.episodes_count">
            <dt>{{ $t('portal.detail.episodes') }}</dt>
            <dd>{{ media.episodes_count }}</dd>
          </template>
          <template v-if="media.networks?.length">
            <dt>{{ $t('portal.detail.network') }}</dt>
            <dd>{{ media.networks.join(', ') }}</dd>
          </template>
        </dl>

        <template v-if="media.studios?.length">
          <h3>{{ $t('portal.detail.production') }}</h3>
          <div class="vmd2-keyword-list">
            <span v-for="s in media.studios.slice(0, 6)" :key="s.name" class="vmd2-keyword">
              {{ s.name }}
            </span>
          </div>
        </template>

        <h3>{{ $t('portal.detail.externalLinks') }}</h3>
        <div class="vmd2-external-links">
          <a
            :href="`https://www.themoviedb.org/${media.media_type}/${media.tmdb_id}`"
            target="_blank"
            rel="noopener"
          >
            TMDB
          </a>
          <a
            v-if="media.imdb_id"
            :href="`https://www.imdb.com/title/${media.imdb_id}`"
            target="_blank"
            rel="noopener"
          >
            IMDb
          </a>
          <a v-if="homepageHref" :href="homepageHref" target="_blank" rel="noopener">
            {{ $t('portal.detail.officialSite') }}
          </a>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { safeHref } from '@/utils/safeUrl'

const props = defineProps({
  media: { type: Object, required: true },
})

const { te, t } = useI18n()

// TMDB ``homepage`` is a free-form URL field; refuse anything that is
// not http(s)/mailto so a poisoned entry cannot smuggle ``javascript:``.
const homepageHref = computed(() => safeHref(props.media?.homepage))

// TMDB returns status in English ("Returning Series", "Released", …).
// Map it through the portal.detail.statusValues table; fall back to the
// raw TMDB string when no translation exists yet.
const translatedStatus = computed(() => {
  const raw = props.media.status
  if (!raw) return ''
  const key = `portal.detail.statusValues.${raw}`
  return te(key) ? t(key) : raw
})

const allProviders = computed(() => {
  const w = props.media.watch_providers || {}
  const merged = [...(w.flatrate || []), ...(w.rent || []), ...(w.buy || [])]
  const seen = new Set()
  return merged
    .filter(p => {
      if (!p.name || seen.has(p.name)) return false
      seen.add(p.name)
      return true
    })
    .slice(0, 12)
})

function formatMoney(n) {
  if (!n) return '0'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(0) + 'M'
  return n.toLocaleString()
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
  }
}
</script>
