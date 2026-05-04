<template>
  <article
    class="arr-row"
    :class="[`arr-row--${req.status}`, { 'arr-row--fresh': isFresh }]"
  >
    <div
      class="arr-row-backdrop"
      :style="backdropStyle"
    />
    <div class="arr-row-bar" />

    <div v-if="index !== null" class="arr-row-index">{{ String(index).padStart(2, '0') }}</div>

    <router-link
      :to="{ name: 'portal-media-detail', params: { type: req.media_type, id: req.tmdb_id } }"
      class="arr-row-poster arr-row-poster--link"
      :aria-label="$t('portal.admin.req.openDetail')"
    >
      <img v-if="req.poster_url" :src="req.poster_url" :alt="req.title" loading="lazy" />
      <div v-else class="arr-row-poster-empty">
        <Film :size="20" :stroke-width="1.5" />
      </div>
    </router-link>

    <div class="arr-row-info">
      <div class="arr-row-meta-top">
        <span v-if="req.year" class="arr-row-year">{{ req.year }}</span>
        <span class="arr-row-type">{{ isTv(req) ? $t('portal.card.series') : $t('portal.card.movie') }}</span>
        <span class="arr-row-status">
          <span class="arr-row-status-dot" />
          {{ $t(`portal.requests.${req.status}`) }}
        </span>
        <span
          v-if="retryBadge"
          class="arr-row-retry arr-row-retry--inline"
          :title="$t('portal.card.retryBadgeTooltip', { count: retryBadge })"
        >x{{ retryBadge }}</span>
      </div>
      <h3 class="arr-row-title">
        <span class="arr-row-title-text">{{ req.title }}</span>
        <button
          class="arr-row-copy"
          type="button"
          :title="copyTitleLabel"
          :aria-label="copyTitleLabel"
          @click.prevent.stop="copyTitle"
        >
          <Copy v-if="!copied" :size="14" :stroke-width="2.2" />
          <Check v-else :size="14" :stroke-width="2.5" />
        </button>
      </h3>
      <div class="arr-row-foot">
        <span v-if="req.requester_deleted" class="arr-row-by arr-row-by--anon">
          <MkAvatar
            :src="null"
            :name="'?'"
            :size="22"
            class="arr-row-by-avatar"
          />
          <span class="arr-who arr-who--deleted">{{ $t('portal.common.deletedUser') }}</span>
          · <strong>{{ formatAgo(req.created_at) }}</strong>
        </span>
        <span v-else-if="req.requester" class="arr-row-by">
          <MkAvatar
            :src="req.requester.avatar_url"
            :name="req.requester.display_name || req.requester.username || ''"
            :size="22"
            class="arr-row-by-avatar"
          />
          <span class="arr-who">{{ req.requester.display_name }}</span>
          · <strong>{{ formatAgo(req.created_at) }}</strong>
        </span>
        <span v-if="req.updated_at && req.updated_at !== req.created_at">
          {{ $t('portal.admin.req.modifiedAt') }} <strong>{{ formatAgo(req.updated_at) }}</strong>
        </span>
        <span v-if="hasSeasons" class="arr-row-seasons">
          <span class="arr-row-seasons-label">{{ seasonLabel }}</span>
          <span
            v-for="s in visibleSeasons"
            :key="s"
            class="arr-row-season-pill"
          >{{ s }}</span>
        </span>
      </div>
    </div>

    <div class="arr-row-actions">
      <template v-if="req.status === REQUEST_STATUS.PENDING">
        <button
          class="arr-action arr-action--icon arr-action--approve"
          type="button"
          :title="$t('portal.admin.approve')"
          :aria-label="$t('portal.admin.approve')"
          @click="$emit('action', REQUEST_STATUS.APPROVED)"
        >
          <Check :size="18" :stroke-width="2.5" />
        </button>
        <button
          class="arr-action arr-action--icon arr-action--reject"
          type="button"
          :title="$t('portal.admin.reject')"
          :aria-label="$t('portal.admin.reject')"
          @click="$emit('action', REQUEST_STATUS.REJECTED)"
        >
          <X :size="18" :stroke-width="2.5" />
        </button>
      </template>
      <template v-else-if="req.status === REQUEST_STATUS.APPROVED">
        <button
          class="arr-action arr-action--icon arr-action--available"
          type="button"
          :title="$t('portal.requests.available')"
          :aria-label="$t('portal.requests.available')"
          @click="$emit('action', 'available')"
        >
          <CircleCheck :size="18" :stroke-width="2.2" />
        </button>
      </template>
      <button
        class="arr-action arr-action--icon arr-action--reject"
        type="button"
        :title="$t('portal.admin.delete')"
        :aria-label="$t('portal.admin.delete')"
        @click="$emit('delete')"
      >
        <Trash2 :size="18" />
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, CircleCheck, Copy, Film, Trash2, X } from 'lucide-vue-next'
import { isTv } from '@/constants/media'
import { REQUEST_STATUS } from '@/constants/requests'
import MkAvatar from '@/components/common/MkAvatar.vue'

const props = defineProps({
  req: { type: Object, required: true },
  index: { type: Number, default: null },
})
defineEmits(['action', 'delete'])

const { t } = useI18n()

const copied = ref(false)
const copyTitleLabel = computed(() =>
  copied.value ? t('common.copied') || 'Copied!' : t('common.copy') || 'Copy',
)

async function copyTitle() {
  try {
    await navigator.clipboard?.writeText(props.req.title || '')
    copied.value = true
    setTimeout(() => { copied.value = false }, 1600)
  } catch {
    /* clipboard blocked (http, old browser) — silent */
  }
}

const backdropStyle = computed(() => ({
  backgroundImage: props.req.backdrop_url ? `url(${props.req.backdrop_url})` : 'none',
}))

const retryBadge = computed(() => {
  const n = Number(props.req.retry_count || 0)
  return n >= 1 ? n + 1 : null
})

const hasSeasons = computed(() =>
  Array.isArray(props.req.requested_seasons) && props.req.requested_seasons.length > 0,
)
const visibleSeasons = computed(() =>
  (props.req.requested_seasons || []).map(s => s.season ?? s).slice(0, 14),
)
const seasonLabel = computed(() =>
  (props.req.requested_seasons || []).length > 1
    ? t('portal.admin.req.seasons') || 'Seasons'
    : t('portal.admin.req.season') || 'Season',
)

const isFresh = computed(() => {
  const ts = props.req.updated_at || props.req.created_at
  if (!ts) return false
  const ageMs = Date.now() - new Date(ts).getTime()
  return ageMs < 3600_000 && props.req.status !== REQUEST_STATUS.PENDING
})

function formatAgo(iso) {
  if (!iso) return ''
  const diff = Math.max(0, Date.now() - new Date(iso).getTime())
  const mins = Math.round(diff / 60_000)
  if (mins < 1) return t('dashboard.justNow') || t('portal.profile.now') || '< 1 min'
  if (mins < 60) return `${mins} min`
  const h = Math.round(mins / 60)
  if (h < 48) return `${h} h`
  const d = Math.round(h / 24)
  if (d < 30) return `${d} d`
  const mo = Math.round(d / 30)
  return `${mo} mo`
}
</script>
