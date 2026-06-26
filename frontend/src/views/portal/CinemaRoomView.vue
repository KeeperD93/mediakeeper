<template>
  <div class="pt-cr">
    <div v-if="loading" class="pt-cr-loading">{{ $t('common.loading') }}</div>

    <template v-else-if="event">
      <div class="pt-cr-stage">
        <CinemaRoomStage />

        <!-- Big screen -->
        <div ref="screenFrameEl" class="pt-cr-screen-frame">
          <div class="pt-cr-screen">
            <div
              v-show="!flow.canLaunch.value && carousel.hasTrailer.value"
              ref="playerEl"
              class="pt-cr-screen-video"
            />

            <div
              v-if="!flow.canLaunch.value && carousel.hasTrailer.value"
              class="pt-cr-screen-fade"
              :class="{ 'pt-cr-screen-fade--active': carousel.transitioning.value }"
              :style="carousel.fadeStyle.value"
              aria-hidden="true"
            />

            <button
              v-if="!flow.canLaunch.value && currentTrailer"
              type="button"
              class="pt-cr-info"
              :aria-label="
                $t('portal.cinema.trailerInfoAria', { title: currentTrailer.title || '' })
              "
              :disabled="!currentTrailer.emby_url"
              @click="openTrailerInfo"
            >
              <Info :size="14" :stroke-width="2.5" />
              {{ $t('portal.cinema.trailerInfo') }}
            </button>

            <div v-if="flow.academyActive.value" class="pt-cr-academy">
              <div class="pt-cr-academy-circle">
                <span :key="flow.academyValue.value" class="pt-cr-academy-num">
                  {{ flow.academyValue.value }}
                </span>
              </div>
            </div>

            <div v-else-if="flow.academyDone.value" class="pt-cr-screen-ready">
              <img
                v-if="currentMedia?.poster_url"
                :src="currentMedia.poster_url"
                :alt="currentMedia.title"
                class="pt-cr-screen-poster"
              />
              <span v-else class="pt-cr-screen-ready-text">{{ currentMedia?.title }}</span>
            </div>

            <div
              v-else-if="!flow.canLaunch.value && !carousel.hasTrailer.value"
              class="pt-cr-screen-placeholder"
            >
              <span class="pt-cr-screen-title">{{ event.title }}</span>
            </div>
          </div>
          <div class="pt-cr-screen-halo" />
          <div class="pt-cr-podium" aria-hidden="true" />
        </div>

        <!-- Floating dust in the projector beam -->
        <div class="pt-cr-particles" aria-hidden="true">
          <span v-for="i in 22" :key="`p${i}`" class="pt-cr-particle" />
        </div>

        <CinemaRoomMobile v-if="isMobile" :event="event" />
        <CinemaRoomSeats v-else :event="event" />
        <MarathonProgressPanel :progress="marathonProgress.progress.value" />
      </div>

      <!-- Launch CTA: centred on the virtual screen via syncLaunchPos
           (the screen is not at the viewport centre). -->
      <transition name="pt-cr-cta">
        <div v-if="flow.academyDone.value" class="pt-cr-launch" :style="launchPos">
          <button type="button" class="pt-cr-launch-btn" @click="onLaunchClick">
            <Play :size="22" :stroke-width="2.5" />
            {{ launchLabel }}
          </button>
          <div v-if="event.tmdb_ids.length > 1" class="pt-cr-launch-marathon">
            {{
              $t('portal.cinema.marathonStep', {
                current: myUserStep + 1,
                total: event.tmdb_ids.length,
              })
            }}
          </div>
          <button
            v-if="canAdvanceSelf"
            type="button"
            class="pt-cr-launch-next"
            @click="onAdvanceSelfClick"
          >
            {{ $t('portal.cinema.nextFilm') }}
          </button>
        </div>
      </transition>

      <!-- HUD: docked LEFT -->
      <div class="pt-cr-hud">
        <button class="pt-cr-leave" @click="leave">
          <LogOut :size="18" :stroke-width="2.5" />
          {{ $t('portal.cinema.leave') }}
        </button>
        <div
          class="pt-cr-countdown"
          :class="{ 'pt-cr-countdown--late': flow.countdownNegative.value }"
        >
          <span class="pt-cr-countdown-label">
            {{
              flow.countdownNegative.value
                ? $t('portal.cinema.elapsed')
                : $t('portal.cinema.startsIn')
            }}
          </span>
          <span class="pt-cr-countdown-value">{{ flow.countdownDisplay.value }}</span>
        </div>
        <button
          class="pt-cr-mute"
          :title="muted ? $t('portal.cinema.unmute') : $t('portal.cinema.mute')"
          @click="toggleMute"
        >
          <VolumeX v-if="muted" :size="16" :stroke-width="2.5" />
          <Volume2 v-else :size="16" :stroke-width="2.5" />
          {{ muted ? $t('portal.cinema.unmute') : $t('portal.cinema.mute') }}
        </button>
      </div>

      <EventRoomChat :event-id="event.id" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRooms } from '@/composables/portal/useRooms'
import { useAvailability } from '@/composables/portal/useAvailability'
import { useCinemaTrailerCarousel } from '@/composables/portal/useCinemaTrailerCarousel'
import { useCinemaRoomFlow } from '@/composables/portal/useCinemaRoomFlow'
import { useCinemaRoomLaunch } from '@/composables/portal/useCinemaRoomLaunch'
import { useCinemaRoomMembership } from '@/composables/portal/useCinemaRoomMembership'
import { useMarathonProgress } from '@/composables/portal/useMarathonProgress'
import { usePresenceHeartbeat } from '@/composables/portal/usePresenceHeartbeat'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useToast } from '@/composables/useToast'
import EventRoomChat from '@/components/portal/EventRoomChat.vue'
import CinemaRoomSeats from '@/components/portal/cinema/CinemaRoomSeats.vue'
import CinemaRoomMobile from '@/components/portal/cinema/CinemaRoomMobile.vue'
import CinemaRoomStage from '@/components/portal/cinema/CinemaRoomStage.vue'
import MarathonProgressPanel from '@/components/portal/cinema/MarathonProgressPanel.vue'
import { useMobile } from '@/composables/useMobile'
import { PORTAL_TAB } from '@/constants/portal'
import { TOAST_TYPE } from '@/constants/toast'
import { safeHref } from '@/utils/safeUrl'
import { Info, LogOut, Play, Volume2, VolumeX } from 'lucide-vue-next'

import '@/assets/styles/portal/cinema-room-stage.css'
import '@/assets/styles/portal/cinema-room-screen.css'
import '@/assets/styles/portal/cinema-room-seats.css'
import '@/assets/styles/portal/cinema-room-hud.css'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { enterRoom, getOne, advanceSelf } = useRooms()
const { profile } = usePortalAuth()
const { showToast } = useToast()
// Mobile breakpoint — viewports ≤ 767 px swap the desktop 3D cinema
// seats for ``CinemaRoomMobile`` (flat avatar grid). The full screen
// + HUD + launch + chat keep working, only the seats layout changes.
const { isMobile } = useMobile()

const event = ref(null)
const loading = ref(true)
const muted = ref(true)
const eventIdParam = parseInt(route.params.id, 10)
const marathonProgress = useMarathonProgress(eventIdParam)

// Heartbeat composable handles its own lifecycle (interval mount,
// beforeunload + unmount leave). Wire it as soon as the event id is
// known so peers see the avatar appear right after enter_room.
const eventIdRef = computed(() => eventIdParam || null)
usePresenceHeartbeat(eventIdRef)
// The MKEventMedia payload stored on tmdb_ids does not carry an
// ``emby_url`` (the create-event schema only persists tmdb_id, type,
// title, poster, runtime). Resolve the launch URL on demand via the
// shared availability composable — same lookup the home carousels and
// PortalMediaDetail already use, with its 60 s cache + microtask
// coalescing so we don't burn extra Emby index calls.
const { checkAvailability, getAvailability } = useAvailability()

const scheduledTime = computed(() =>
  event.value ? new Date(event.value.scheduled_at).getTime() : 0,
)
const flow = useCinemaRoomFlow(scheduledTime)

const playerEl = ref(null)
const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl, initialMuted: muted.value })
const currentTrailer = computed(() => carousel.currentTrailer.value)

// Launch CTA (label/enable, open-in-Emby, advance-self, centring) plus
// the per-user marathon step / current-media derivation it owns.
const {
  screenFrameEl,
  launchPos,
  currentMedia,
  myUserStep,
  launchLabel,
  canAdvanceSelf,
  onLaunchClick,
  onAdvanceSelfClick,
} = useCinemaRoomLaunch({
  event,
  profile,
  flow,
  marathonProgress,
  advanceSelf,
  checkAvailability,
  getAvailability,
  t,
  showToast,
})

// Seat presence + per-user step sync (15 s membership re-pull + 3 s
// progress-poll merge). ``start()`` arms the timer once the room loads.
const membership = useCinemaRoomMembership({
  event,
  eventId: eventIdParam,
  getOne,
  marathonProgress,
})

function toggleMute() {
  muted.value = !muted.value
  carousel.applyMute(muted.value)
}

function openTrailerInfo() {
  const url = safeHref(currentTrailer.value?.emby_url)
  if (!url) return
  window.open(url, '_blank', 'noopener')
}

watch(flow.canStartAcademy, v => {
  // Fire the 10-second academy intro 10 s before the deadline so its
  // final ``0`` lines up with the main countdown hitting zero — the
  // viewer reaches T-0 with the screen ready, not 10 s late.
  if (v && !flow.academyActive.value && !flow.academyDone.value) {
    carousel.destroy()
    flow.startAcademy()
  }
})

// Safety net: once the poster screen is up (academy finished or the
// latecomer fast-path fired), tear down any leftover YouTube iframe so
// the trailer cannot keep playing in the background — a refresh past
// T0 used to reach this state with the iframe still spinning.
watch(
  () => flow.academyDone.value,
  done => {
    if (done) carousel.destroy()
  },
)

async function load() {
  loading.value = true
  try {
    const id = parseInt(route.params.id, 10)
    const enterRes = await enterRoom(id).catch(() => null)
    if (enterRes && !enterRes.error) {
      event.value = enterRes.event
    } else if (enterRes?.error === 'event_ended') {
      // Stale notification or a refresh on a long-finished event:
      // bounce back to the portal home with a clear toast instead of
      // stranding the user on an empty (or worse, ghosted) cinema room.
      showToast(t('portal.cinema.errors.event_ended'), TOAST_TYPE.WARN)
      router.replace({ name: PORTAL_TAB.HOME })
      return
    } else if (enterRes?.error === 'not_member') {
      // A user clicking the room URL without an accepted invitation
      // must not be allowed to wander into the cinema, even read-only
      // (their avatar wouldn't render, the chat would refuse posts,
      // and the seat allocation is membership-gated server-side).
      showToast(t('portal.cinema.errors.not_member'), TOAST_TYPE.WARN)
      router.replace({ name: PORTAL_TAB.HOME })
      return
    } else {
      event.value = await getOne(id)
    }
  } finally {
    loading.value = false
  }
  // Defence in depth: the ``enter_room`` path already bounces on
  // ``event_ended``, but the ``getOne`` fallback (room full, forbidden,
  // network glitch) — or a cutoff crossed between the two requests —
  // can still surface a terminated event. Keep the cinema view from
  // rendering zombie seats and bubbles in that case.
  if (event.value?.is_terminated) {
    showToast(t('portal.cinema.errors.event_ended'), TOAST_TYPE.WARN)
    router.replace({ name: PORTAL_TAB.HOME })
    return
  }
  if (event.value?.tmdb_ids?.length) {
    // Warm the availability cache for every media of the event so the
    // launch CTA resolves its emby_url without a round trip when clicked.
    // ``checkAvailability`` returns undefined when every id is already
    // fresh, so wrap it before ``.catch`` to stay safe on a warm re-entry.
    Promise.resolve(checkAvailability(event.value.tmdb_ids)).catch(() => {})
  }
  // Marathon step is now tracked per-user via ``invitations[i].user_step``
  // — no shared marker to mirror locally. Single-film events still get
  // the poll wired up so the playback timeline (``MarathonProgressPanel``)
  // can surface a viewer's session as soon as it appears in the next
  // tick — used to require a manual refresh otherwise.
  if (event.value) {
    marathonProgress.start()
    membership.start()
  }
  if (flow.canLaunch.value) {
    // Latecomer joining after T0: skip the academy intro and land
    // straight on the launch CTA. The above watcher will also fire
    // ``carousel.destroy()`` once academyDone flips, but we never
    // started the carousel in this branch anyway.
    flow.skipToReady()
  } else if (flow.canStartAcademy.value) {
    if (!flow.academyDone.value && !flow.academyActive.value) {
      flow.startAcademy()
    }
  } else {
    carousel.start().catch(() => {})
  }
}

function leave() {
  // The presence composable's ``onBeforeUnmount`` will fire ``leaveRoom``
  // automatically as we navigate away, so peers see the avatar
  // disappear without waiting for the 15 s presence window.
  if (window.opener) window.close()
  else router.push({ name: PORTAL_TAB.HOME })
}

onMounted(() => {
  load()
  flow.startTicker()
})
</script>
