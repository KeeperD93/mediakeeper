<template>
  <Teleport to="body">
    <transition name="ddd-fade">
      <div
        v-if="visible"
        class="ddd-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('portal.dailyDigest.title')"
        @click.self="dismissToday"
      >
        <div class="ddd-backdrop-fx" aria-hidden="true" />
        <div ref="panelRef" class="ddd-panel" tabindex="-1">
          <button
            ref="closeBtnRef"
            class="ddd-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="dismissToday"
          >
            <X :size="18" />
          </button>

          <div class="ddd-panel-scroll">
            <header class="ddd-hero">
              <span class="ddd-hero-eyebrow">{{ formattedDate }}</span>
              <h1 class="ddd-hero-title">{{ greeting }}</h1>
              <p class="ddd-hero-sub">{{ $t('portal.dailyDigest.subtitle') }}</p>
            </header>

            <div v-if="loading" class="ddd-state">{{ $t('common.loading') }}</div>
            <div v-else-if="error" class="ddd-state ddd-state--error">
              {{ $t('portal.dailyDigest.errorLoad') }}
            </div>
            <div v-else-if="!digest || digest.empty" class="ddd-state ddd-state--empty">
              {{ $t('portal.dailyDigest.empty') }}
            </div>

            <div v-else class="ddd-body">
              <section
                v-if="statCards.length"
                class="ddd-stats"
                :aria-label="$t('portal.dailyDigest.aria.stats')"
              >
                <div v-for="s in statCards" :key="s.key" class="ddd-stat" :class="s.cls">
                  <component :is="s.icon" class="ddd-stat-icon" :size="22" />
                  <span class="ddd-stat-label">{{ s.label }}</span>
                  <div class="ddd-stat-value">
                    <span>{{ s.value }}</span>
                    <span v-if="s.delta" class="ddd-stat-delta" :class="s.deltaClass">
                      {{ s.delta }}
                    </span>
                  </div>
                  <span v-if="s.caption" class="ddd-stat-caption">{{ s.caption }}</span>
                </div>
              </section>

              <section v-if="digest.level" class="ddd-level">
                <div class="ddd-level-badge">{{ digest.level.level }}</div>
                <div class="ddd-level-content">
                  <span class="ddd-level-eyebrow">
                    {{ $t('portal.dailyDigest.level.eyebrow') }}
                  </span>
                  <h2 class="ddd-level-title">
                    {{ $t('portal.profile.titles.' + digest.level.title_key) }}
                  </h2>
                  <div class="ddd-level-progress">
                    <div
                      class="ddd-level-progress-fill"
                      :style="{ width: digest.level.percent + '%' }"
                    />
                  </div>
                  <div class="ddd-level-meta">
                    <span>
                      {{ digest.level.xp_into_level }} /
                      {{ digest.level.xp_next_level - digest.level.xp_current_level }} XP
                    </span>
                    <span class="ddd-level-remaining">
                      {{
                        $t('portal.dailyDigest.level.toNext', {
                          xp: Math.max(0, digest.level.xp_next_level - digest.level.xp),
                          level: digest.level.level + 1,
                        })
                      }}
                    </span>
                  </div>
                </div>
              </section>

              <section
                v-if="digest.ranking?.top3?.length"
                class="ddd-section ddd-section--leaderboard"
              >
                <h3 class="ddd-section-title">{{ $t('portal.dailyDigest.sections.top3') }}</h3>
                <LeaderboardCard :entries="digest.ranking.top3" widget />
              </section>

              <section v-if="digest.next_achievement" class="ddd-ach-hero">
                <div class="ddd-ach-badge">
                  <Trophy :size="30" />
                </div>
                <div class="ddd-ach-content">
                  <span class="ddd-ach-eyebrow">
                    {{ $t('portal.dailyDigest.sections.nextAchievement') }}
                  </span>
                  <h2 class="ddd-ach-title">{{ $t(digest.next_achievement.name_key) }}</h2>
                  <p v-if="digest.next_achievement.description_key" class="ddd-ach-desc">
                    {{ $t(digest.next_achievement.description_key) }}
                  </p>
                  <div class="ddd-progress">
                    <div class="ddd-progress-fill" :style="{ width: achPercent + '%' }" />
                  </div>
                  <div class="ddd-ach-meta">
                    <span class="ddd-ach-count">
                      {{ digest.next_achievement.progress }} /
                      {{ digest.next_achievement.threshold }}
                    </span>
                    <span class="ddd-ach-remaining">
                      {{
                        $t('portal.dailyDigest.achievement.remaining', {
                          count: digest.next_achievement.remaining,
                        })
                      }}
                    </span>
                  </div>
                </div>
              </section>

              <section v-if="digest.recent_adds.length" class="ddd-section">
                <div class="ddd-section-head">
                  <h3 class="ddd-section-title">
                    {{ $t('portal.dailyDigest.sections.recentAdds') }}
                  </h3>
                  <span class="ddd-section-count">{{ digest.recent_adds.length }}</span>
                </div>
                <div class="ddd-posters-wrap">
                  <button
                    v-show="canScrollLeft"
                    type="button"
                    class="ddd-posters-arrow ddd-posters-arrow--left"
                    :aria-label="$t('portal.dailyDigest.aria.scrollLeft')"
                    @click="scrollPosters(-1)"
                  >
                    <ChevronLeft :size="20" />
                  </button>
                  <div
                    ref="postersRef"
                    class="ddd-posters"
                    :aria-label="$t('portal.dailyDigest.aria.recentAdds')"
                    @scroll="updateArrows"
                  >
                    <button
                      v-for="item in digest.recent_adds"
                      :key="`${item.media_type}-${item.tmdb_id}`"
                      type="button"
                      class="ddd-poster"
                      @click="openMedia(item)"
                    >
                      <img
                        v-if="item.poster_url"
                        :src="item.poster_url"
                        :alt="item.title"
                        loading="lazy"
                      />
                      <span v-else class="ddd-poster-fallback">{{ item.title?.[0] || '?' }}</span>
                      <div class="ddd-poster-shade" />
                      <div class="ddd-poster-meta">
                        <span class="ddd-poster-title">{{ item.title }}</span>
                        <span v-if="item.year" class="ddd-poster-year">{{ item.year }}</span>
                      </div>
                    </button>
                  </div>
                  <button
                    v-show="canScrollRight"
                    type="button"
                    class="ddd-posters-arrow ddd-posters-arrow--right"
                    :aria-label="$t('portal.dailyDigest.aria.scrollRight')"
                    @click="scrollPosters(1)"
                  >
                    <ChevronRight :size="20" />
                  </button>
                </div>
              </section>

              <section v-if="digest.events.length" class="ddd-section">
                <h3 class="ddd-section-title">{{ $t('portal.dailyDigest.sections.events') }}</h3>
                <div class="ddd-events">
                  <article v-for="ev in digest.events" :key="ev.id" class="ddd-event">
                    <div class="ddd-event-date" :class="`ddd-event-${ev.kind}`">
                      <span class="ddd-event-day">{{ formatEventDay(ev.scheduled_at) }}</span>
                      <span class="ddd-event-month">{{ formatEventMonth(ev.scheduled_at) }}</span>
                    </div>
                    <div class="ddd-event-body">
                      <span class="ddd-event-kind">
                        {{ $t('portal.dailyDigest.events.' + ev.kind) }}
                      </span>
                      <h4 class="ddd-event-title">{{ ev.title }}</h4>
                      <span class="ddd-event-time">{{ formatEventTime(ev.scheduled_at) }}</span>
                    </div>
                  </article>
                </div>
              </section>
            </div>

            <footer class="ddd-footer">
              <button type="button" class="ddd-btn-primary" @click="dismissToday">
                {{ $t('common.close') }}
              </button>
            </footer>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useDailyDigestPresenters } from '@/composables/portal/useDailyDigestPresenters'
import { X, Trophy, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import LeaderboardCard from '@/components/portal/profile/LeaderboardCard.vue'
import '@/assets/styles/portal/daily-digest.css'
import '@/assets/styles/portal/daily-digest-content.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  auto: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])

const { apiGet, apiPost } = useApi()
const { profile } = usePortalAuth()
const router = useRouter()

const visible = ref(false)
const panelRef = ref(null)
const closeBtnRef = ref(null)
const postersRef = ref(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const loading = ref(false)
const error = ref(false)
const digest = ref(null)
const dismissed = ref(false)

const {
  formattedDate,
  greeting,
  statCards,
  achPercent,
  formatEventDay,
  formatEventMonth,
  formatEventTime,
} = useDailyDigestPresenters(digest, profile)

async function load({ force = false, bypassDismissed = false } = {}) {
  loading.value = true
  error.value = false
  try {
    const url = force ? '/api/portal/daily-digest?force=true' : '/api/portal/daily-digest'
    const data = await apiGet(url)
    dismissed.value = !!data?.dismissed
    digest.value = data?.digest || null
    if (!bypassDismissed && (dismissed.value || !digest.value || digest.value.empty)) {
      return false
    }
    visible.value = true
    await nextTick()
    panelRef.value?.focus?.()
    return true
  } catch {
    error.value = true
    return false
  } finally {
    loading.value = false
  }
}

async function dismissToday() {
  try {
    await apiPost('/api/portal/daily-digest/dismiss', {})
  } catch {
    /* silent: dismiss marker is best-effort */
  }
  close()
}

function close() {
  visible.value = false
  emit('close')
}

function openMedia(item) {
  if (!item.tmdb_id) return
  // Treat opening a media as a dismissal too — the user has seen
  // the digest and engaged with it; coming back the same day would
  // be redundant.
  dismissToday()
  router.push({
    name: 'portal-media-detail',
    params: { type: item.media_type || 'movie', id: item.tmdb_id },
  })
}

function updateArrows() {
  const el = postersRef.value
  if (!el) {
    canScrollLeft.value = false
    canScrollRight.value = false
    return
  }
  canScrollLeft.value = el.scrollLeft > 4
  canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4
}

function scrollPosters(dir) {
  const el = postersRef.value
  if (!el) return
  const step = Math.max(180, el.clientWidth * 0.7)
  el.scrollBy({ left: dir * step, behavior: 'smooth' })
}

watch([digest, visible], async () => {
  await nextTick()
  updateArrows()
})

// Lock body scroll while the overlay is open. Without this, a wheel
// or touch gesture that lands on the dim backdrop scrolls the page
// behind, and reaching the inner scroll boundary chains the gesture
// back to the document. The previous overflow value is restored on
// close so the page resumes whatever scroll state it had before.
let previousBodyOverflow = ''
function lockBody() {
  if (typeof document === 'undefined') return
  previousBodyOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
}
function unlockBody() {
  if (typeof document === 'undefined') return
  document.body.style.overflow = previousBodyOverflow
}
watch(visible, v => {
  if (v) lockBody()
  else unlockBody()
})
onBeforeUnmount(() => {
  if (visible.value) unlockBody()
})

watch(
  () => props.open,
  v => {
    if (v) load({ force: true, bypassDismissed: true })
  },
)

useFocusTrap({
  active: visible,
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: dismissToday,
})

if (props.auto) {
  load()
}
</script>
