<template>
  <Teleport to="body">
    <div class="pt-rmodal-overlay" @click.self="$emit('close')">
      <div class="pt-rmodal">
        <div class="pt-rmodal-header">
          <h2>{{ $t('portal.request.title') }}</h2>
          <button
            class="pt-rmodal-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="$emit('close')"
          >
            <X :size="14" />
          </button>
        </div>

        <div class="pt-rmodal-media">
          <img
            v-if="item.poster_url || item.poster"
            :src="item.poster_url || item.poster"
            class="pt-rmodal-poster"
          />
          <div class="pt-rmodal-media-info">
            <h3>{{ item.title }}</h3>
            <span class="pt-rmodal-year">
              {{ item.year }} ·
              {{ isTv(item) ? $t('portal.card.series') : $t('portal.card.movie') }}
            </span>
          </div>
          <span
            v-if="partialAvailability"
            class="pt-rmodal-partial-pill"
            :title="$t('portal.request.partialTooltip')"
          >
            <span class="pt-rmodal-partial-dot" />
            {{ $t('portal.request.partialPill') }}
          </span>
        </div>

        <div class="pt-rmodal-body">
          <!-- TV: season/episode selector -->
          <div v-if="isTv(item) && seasons.length" class="pt-rmodal-section">
            <label>{{ $t('portal.request.selectSeasons') }}</label>

            <!-- Select-all shortcut: picks every season that still has
                 missing episodes (skips fully available + fully ignored
                 seasons, and leaves available/ignored episodes untouched
                 inside mixed seasons). -->
            <label v-if="hasAnyRequestable" class="pt-rmodal-select-all">
              <input
                type="checkbox"
                class="pt-rmodal-chk"
                :checked="allRequestableSelected"
                @change="toggleSelectAll"
              />
              <span>{{ $t('portal.request.selectAll') }}</span>
            </label>

            <div class="pt-rmodal-seasons">
              <div
                v-for="s in seasons"
                :key="s.number"
                class="pt-rmodal-season"
                :class="{ 'pt-rmodal-season--full': isSeasonFullyAvailable(s.number) }"
              >
                <div class="pt-rmodal-season-header" @click="toggleExpand(s.number)">
                  <input
                    type="checkbox"
                    class="pt-rmodal-chk"
                    :checked="isSeasonSelected(s.number)"
                    :disabled="isSeasonFullyAvailable(s.number)"
                    @click.stop
                    @change="toggleSeason(s.number)"
                  />
                  <span class="pt-rmodal-season-name">
                    {{ $t('portal.request.season') }} {{ s.number }}
                  </span>
                  <span
                    v-if="isSeasonFullyAvailable(s.number)"
                    class="pt-rmodal-tag pt-rmodal-tag--ok"
                  >
                    <span class="pt-rmodal-tag-dot" />
                    {{ $t('portal.request.available') }}
                  </span>
                  <span
                    v-else-if="seasonLockedCount(s.number) > 0"
                    class="pt-rmodal-tag pt-rmodal-tag--partial"
                  >
                    {{ seasonLockedCount(s.number) }}/{{ s.episodes }}
                    {{ $t('portal.request.availableShort') }}
                  </span>
                  <span class="pt-rmodal-ep-count">
                    {{ s.episodes }} {{ $t('portal.request.episodes') }}
                  </span>
                </div>

                <div v-if="expanded.has(s.number)" class="pt-rmodal-episodes">
                  <label
                    v-for="ep in getEpisodes(s.number)"
                    :key="ep.number"
                    class="pt-rmodal-episode"
                    :class="{ 'pt-rmodal-episode--avail': isEpisodeLocked(s.number, ep.number) }"
                  >
                    <input
                      type="checkbox"
                      class="pt-rmodal-chk"
                      :checked="isEpisodeSelected(s.number, ep.number)"
                      :disabled="isEpisodeLocked(s.number, ep.number)"
                      @change="toggleEpisode(s.number, ep.number)"
                    />
                    <span
                      class="pt-rmodal-episode-label"
                      :title="ep.name ? `E${ep.number} — ${ep.name}` : `E${ep.number}`"
                    >
                      E{{ ep.number }}
                      <template v-if="ep.name">— {{ ep.name }}</template>
                    </span>
                    <span class="pt-rmodal-episode-status">
                      <span
                        v-if="isEpisodeAvailable(s.number, ep.number)"
                        class="pt-rmodal-dot pt-rmodal-dot--ok"
                        :title="$t('portal.request.available')"
                      />
                      <span
                        v-else-if="isEpisodeIgnored(s.number, ep.number)"
                        class="pt-rmodal-dot pt-rmodal-dot--ignored"
                        :title="$t('portal.request.ignoredTooltip')"
                      />
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Admin: pick user (placed under the season selector so the
               primary choice — which seasons/episodes — is made first). -->
          <div v-if="isAdmin" class="pt-rmodal-section">
            <label>{{ $t('portal.request.onBehalfOf') }}</label>
            <select v-model="selectedUserId" class="pt-input">
              <option v-for="u in users" :key="u.user_id" :value="u.user_id">
                {{ u.display_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="pt-rmodal-footer">
          <button class="pt-rmodal-btn" :disabled="submitting || !canSubmit" @click="submit">
            {{ $t('portal.request.submit') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useRequestSelection } from '@/composables/portal/useRequestSelection'
import { useI18n } from 'vue-i18n'
import { MEDIA_TYPE, isTv } from '@/constants/media'
import { X } from 'lucide-vue-next'

import '@/assets/styles/portal/request-modal.css'

const props = defineProps({
  item: { type: Object, required: true },
  isAdmin: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'done'])
const { apiGet, apiPost } = useApi()
const { showToast } = useToast()
const { t } = useI18n()

const users = ref([])
const selectedUserId = ref(null)
const submitting = ref(false)

const {
  seasons,
  episodesMap,
  selectedSeasons,
  expanded,
  getEpisodes,
  isEpisodeAvailable,
  isEpisodeIgnored,
  isEpisodeLocked,
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
} = useRequestSelection()

const canSubmit = computed(() => {
  if (!isTv(props.item)) return true
  if (!seasons.value.length) return true // metadata still loading — let backend validate
  return hasAnySelection()
})

async function loadSeasons() {
  if (!isTv(props.item)) return
  const id = props.item.tmdb_id || props.item.id
  // Pull the full season list in one shot (TMDB's /tv/{id} endpoint
  // already exposes per-season episode counts, so the UI can render
  // the "X/Y dispo." badges before any /season/{n} call returns).
  const list = await apiGet(`/api/portal/catalog/tv/${id}/seasons`).catch(() => null)
  if (Array.isArray(list) && list.length) {
    for (const s of list) {
      if (s.number > 0) {
        seasons.value.push({ number: s.number, episodes: s.episodes || 0 })
      }
    }
  }
  // Fetch episode details in parallel — the season list above is
  // authoritative for counts, so these calls only enrich the expanded
  // episode view. Failing individually is harmless.
  await Promise.all(
    seasons.value.map(async s => {
      const epRes = await apiGet(`/api/portal/catalog/tv/${id}/season/${s.number}`).catch(
        () => null,
      )
      if (epRes && Array.isArray(epRes)) {
        episodesMap.value[s.number] = epRes
        if (!s.episodes) s.episodes = epRes.length
      }
    }),
  )
}

async function loadAvailability() {
  if (!isTv(props.item)) return
  const id = props.item.tmdb_id || props.item.id
  const res = await apiGet(`/api/portal/availability/tv/${id}/episodes`).catch(() => null)
  if (!res) return
  // Even when the series is NOT indexed in Emby (``in_emby: false``)
  // the endpoint still returns any ignored episodes so the modal can
  // flag them correctly when a new season drops.
  const availMap = {}
  const ignMap = {}
  for (const [key, bucket] of Object.entries(res.seasons || {})) {
    const sNum = Number(key)
    if (bucket.available?.length) availMap[sNum] = new Set(bucket.available)
    if (bucket.ignored?.length) ignMap[sNum] = new Set(bucket.ignored)
  }
  setAvailability(availMap, ignMap)
}

async function submit() {
  submitting.value = true
  const reqData = {
    tmdb_id: props.item.tmdb_id || props.item.id,
    media_type: props.item.media_type || MEDIA_TYPE.MOVIE,
    title: props.item.title,
    year: props.item.year ? parseInt(props.item.year) : null,
    poster_url: props.item.poster_url || props.item.poster || '',
    backdrop_url: props.item.backdrop_url || props.item.backdrop || '',
  }

  if (isTv(props.item) && selectedSeasons.size > 0) {
    const seasonsData = []
    for (const [sNum, sel] of selectedSeasons) {
      if (sel === 'full') {
        seasonsData.push({ season: sNum, episodes: 'all' })
      } else if (Array.isArray(sel) && sel.length > 0) {
        seasonsData.push({ season: sNum, episodes: sel })
      }
    }
    reqData.requested_seasons = seasonsData
  }

  if (props.isAdmin && selectedUserId.value) {
    reqData.on_behalf_of = selectedUserId.value
  }

  const res = await apiPost('/api/portal/requests', reqData).catch(() => null)
  submitting.value = false
  if (res?.success) {
    if (res.quota) {
      const { used, max } = res.quota
      if (used >= max) {
        showToast(t('portal.request.quotaReached', { used, max }), TOAST_TYPE.WARN, 5000)
      } else {
        showToast(t('portal.request.quotaInfo', { used, max }), TOAST_TYPE.OK, 4000)
      }
    } else {
      const successKey =
        res.retry_count && res.retry_count >= 1
          ? 'portal.request.resubmitSuccess'
          : 'common.success'
      showToast(t(successKey), TOAST_TYPE.OK)
    }
    emit('done', { retry_count: res.retry_count || 0, id: res.id })
    emit('close')
  } else {
    // Map backend error codes → human-readable messages.
    const code = res?.detail || res?.error
    const i18nKey = code ? `portal.request.errors.${code}` : null
    const msg = i18nKey && t(i18nKey) !== i18nKey ? t(i18nKey) : code || t('common.error')
    showToast(msg, TOAST_TYPE.ERR)
  }
}

onMounted(async () => {
  if (props.isAdmin) {
    const res = await apiGet('/api/portal/admin/users?limit=200').catch(() => null)
    if (res) {
      users.value = res.items
      if (users.value.length) selectedUserId.value = users.value[0].user_id
    }
  }
  await Promise.all([loadSeasons(), loadAvailability()])
})
</script>
