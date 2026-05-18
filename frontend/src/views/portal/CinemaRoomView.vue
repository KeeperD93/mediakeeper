<template>
  <div class="pt-cr">
    <div v-if="loading" class="pt-cr-loading">{{ $t('common.loading') }}</div>

    <template v-else-if="event">
      <div class="pt-cr-stage">
        <CinemaRoomStage />

        <!-- Big screen -->
        <div class="pt-cr-screen-frame">
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
                <span :key="flow.academyValue.value" class="pt-cr-academy-num">{{ flow.academyValue.value }}</span>
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

        <CinemaRoomSeats :event="event" />
        <MarathonProgressPanel :progress="marathonProgress.progress.value" />
      </div>

      <!-- Launch CTA: appears ABOVE the screen after the academy countdown -->
      <transition name="pt-cr-cta">
        <div v-if="flow.academyDone.value" class="pt-cr-launch">
          <button
            type="button"
            class="pt-cr-launch-btn"
            :disabled="event.tmdb_ids.length > 1 && !marathonProgress.ready.value"
            @click="onLaunchClick"
          >
            <Play :size="22" :stroke-width="2.5" />
            {{ launchLabel }}
          </button>
          <div v-if="event.tmdb_ids.length > 1" class="pt-cr-launch-marathon">
            {{
              $t('portal.cinema.marathonStep', {
                current: marathonStep + 1,
                total: event.tmdb_ids.length,
              })
            }}
          </div>
        </div>
      </transition>

      <!-- HUD: docked LEFT -->
      <div class="pt-cr-hud">
        <button class="pt-cr-leave" @click="leave">
          <LogOut :size="18" :stroke-width="2.5" />
          {{ $t('portal.cinema.leave') }}
        </button>
        <div class="pt-cr-countdown" :class="{ 'pt-cr-countdown--late': flow.countdownNegative.value }">
          <span class="pt-cr-countdown-label">
            {{ flow.countdownNegative.value ? $t('portal.cinema.elapsed') : $t('portal.cinema.startsIn') }}
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
import { useCinemaTrailerCarousel } from '@/composables/portal/useCinemaTrailerCarousel'
import { useCinemaRoomFlow } from '@/composables/portal/useCinemaRoomFlow'
import { useMarathonProgress } from '@/composables/portal/useMarathonProgress'
import { useToast } from '@/composables/useToast'
import { fetchApiResponse } from '@/composables/apiClient'
import EventRoomChat from '@/components/portal/EventRoomChat.vue'
import CinemaRoomSeats from '@/components/portal/cinema/CinemaRoomSeats.vue'
import CinemaRoomStage from '@/components/portal/cinema/CinemaRoomStage.vue'
import MarathonProgressPanel from '@/components/portal/cinema/MarathonProgressPanel.vue'
import { isTv as isTvMedia } from '@/constants/media'
import { PORTAL_TAB } from '@/constants/portal'
import { TOAST_TYPE } from '@/constants/toast'
import { Info, LogOut, Play, Volume2, VolumeX } from 'lucide-vue-next'

import '@/assets/styles/portal/cinema-room-stage.css'
import '@/assets/styles/portal/cinema-room-screen.css'
import '@/assets/styles/portal/cinema-room-seats.css'
import '@/assets/styles/portal/cinema-room-hud.css'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { enterRoom, getOne } = useRooms()
const { showToast } = useToast()

const event = ref(null)
const loading = ref(true)
const marathonStep = ref(0)
const muted = ref(true)
const eventIdParam = parseInt(route.params.id, 10)
const marathonProgress = useMarathonProgress(eventIdParam)

const scheduledTime = computed(() =>
  event.value ? new Date(event.value.scheduled_at).getTime() : 0,
)
const flow = useCinemaRoomFlow(scheduledTime)

const playerEl = ref(null)
const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl, initialMuted: muted.value })
const currentTrailer = computed(() => carousel.currentTrailer.value)

const currentMedia = computed(() => event.value?.tmdb_ids?.[marathonStep.value] || null)
const launchLabel = computed(() => {
  if (!currentMedia.value) return ''
  return isTvMedia(currentMedia.value) ? 'Start the series' : 'Start the movie'
})

function toggleMute() {
  muted.value = !muted.value
  carousel.applyMute(muted.value)
}

function openTrailerInfo() {
  const url = currentTrailer.value?.emby_url
  if (!url) return
  window.open(url, '_blank', 'noopener')
}

watch(flow.canLaunch, v => {
  if (v && !flow.academyActive.value && !flow.academyDone.value) {
    carousel.destroy()
    flow.startAcademy()
  }
})

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
    } else {
      event.value = await getOne(id)
    }
  } finally {
    loading.value = false
  }
  if (event.value && (event.value.tmdb_ids?.length || 0) > 1) {
    marathonStep.value = event.value.current_step || 0
    marathonProgress.start()
  }
  if (flow.canLaunch.value) {
    if (!flow.academyDone.value && !flow.academyActive.value) flow.startAcademy()
  } else {
    carousel.start().catch(() => {})
  }
}

watch(
  () => marathonProgress.progress.value?.current_step,
  step => {
    if (typeof step === 'number' && step !== marathonStep.value) {
      marathonStep.value = step
    }
  },
)

function leave() {
  if (window.opener) window.close()
  else router.push({ name: PORTAL_TAB.HOME })
}

async function onLaunchClick() {
  if (!event.value) return
  const total = event.value.tmdb_ids?.length || 0
  // Single-film event: no server-side advance to do. Playback starts
  // in Emby — the button here is decorative.
  if (total <= 1) return
  const res = await fetchApiResponse(
    `/api/portal/events/rooms/${event.value.id}/advance`,
    {
      method: 'POST',
      body: JSON.stringify({ expected_step: marathonStep.value }),
    },
  )
  if (!res) return
  if (res.ok) {
    const data = await res.json().catch(() => null)
    if (data?.ok && data.event) {
      event.value = data.event
      marathonStep.value = data.current_step
      flow.resetAcademy()
    }
    return
  }
  if (res.status === 412) {
    showToast(t('portal.cinema.marathon.notReady'), TOAST_TYPE.WARN)
  } else if (res.status === 409) {
    showToast(t('portal.cinema.marathon.staleStep'), TOAST_TYPE.WARN)
  } else {
    showToast(t('common.error'), TOAST_TYPE.ERR)
  }
}

onMounted(() => {
  load()
  flow.startTicker()
})
</script>
