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
              v-show="!canLaunch && carousel.hasTrailer.value"
              ref="playerEl"
              class="pt-cr-screen-video"
            />

            <div
              v-if="!canLaunch && carousel.hasTrailer.value"
              class="pt-cr-screen-fade"
              :class="{ 'pt-cr-screen-fade--active': carousel.transitioning.value }"
              :style="carousel.fadeStyle.value"
              aria-hidden="true"
            />

            <button
              v-if="!canLaunch && currentTrailer"
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

            <div v-if="academyActive" class="pt-cr-academy">
              <div class="pt-cr-academy-circle">
                <span :key="academyValue" class="pt-cr-academy-num">{{ academyValue }}</span>
              </div>
            </div>

            <div v-else-if="academyDone" class="pt-cr-screen-ready">
              <img
                v-if="currentMedia?.poster_url"
                :src="currentMedia.poster_url"
                :alt="currentMedia.title"
                class="pt-cr-screen-poster"
              />
              <span v-else class="pt-cr-screen-ready-text">{{ currentMedia?.title }}</span>
            </div>

            <div
              v-else-if="!canLaunch && !carousel.hasTrailer.value"
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
      </div>

      <!-- Launch CTA: appears ABOVE the screen after the academy countdown -->
      <transition name="pt-cr-cta">
        <div v-if="academyDone" class="pt-cr-launch">
          <button
            type="button"
            class="pt-cr-launch-btn"
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
        <div class="pt-cr-countdown" :class="{ 'pt-cr-countdown--late': countdownNegative }">
          <span class="pt-cr-countdown-label">
            {{ countdownNegative ? $t('portal.cinema.elapsed') : $t('portal.cinema.startsIn') }}
          </span>
          <span class="pt-cr-countdown-value">{{ countdownDisplay }}</span>
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
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRooms } from '@/composables/portal/useRooms'
import { useCinemaTrailerCarousel } from '@/composables/portal/useCinemaTrailerCarousel'
import EventRoomChat from '@/components/portal/EventRoomChat.vue'
import CinemaRoomSeats from '@/components/portal/cinema/CinemaRoomSeats.vue'
import CinemaRoomStage from '@/components/portal/cinema/CinemaRoomStage.vue'
import { isTv as isTvMedia } from '@/constants/media'
import { PORTAL_TAB } from '@/constants/portal'
import { Info, LogOut, Play, Volume2, VolumeX } from 'lucide-vue-next'

import '@/assets/styles/portal/cinema-room-stage.css'
import '@/assets/styles/portal/cinema-room-screen.css'
import '@/assets/styles/portal/cinema-room-seats.css'
import '@/assets/styles/portal/cinema-room-hud.css'

const route = useRoute()
const router = useRouter()
const { enterRoom, getOne } = useRooms()

const event = ref(null)
const loading = ref(true)
const now = ref(Date.now())
const marathonStep = ref(0)
const muted = ref(true)

const academyActive = ref(false)
const academyValue = ref(10)
const academyDone = ref(false)

const playerEl = ref(null)
const carousel = useCinemaTrailerCarousel({ playerElRef: playerEl, initialMuted: muted.value })
const currentTrailer = computed(() => carousel.currentTrailer.value)

let tickTimer = null
let academyTimer = null

const scheduledTime = computed(() =>
  event.value ? new Date(event.value.scheduled_at).getTime() : 0,
)
const remainingMs = computed(() => scheduledTime.value - now.value)
const countdownNegative = computed(() => remainingMs.value < 0)
const canLaunch = computed(() => remainingMs.value <= 0)

const countdownDisplay = computed(() => {
  const ms = Math.abs(remainingMs.value)
  const total = Math.floor(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

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

watch(canLaunch, v => {
  if (v && !academyActive.value && !academyDone.value) {
    carousel.destroy()
    startAcademy()
  }
})

function startAcademy() {
  academyActive.value = true
  academyValue.value = 10
  academyTimer = setInterval(() => {
    academyValue.value -= 1
    if (academyValue.value <= 0) {
      clearInterval(academyTimer)
      academyTimer = null
      academyActive.value = false
      academyDone.value = true
    }
  }, 1000)
}

async function load() {
  loading.value = true
  try {
    const id = parseInt(route.params.id, 10)
    const enterRes = await enterRoom(id).catch(() => null)
    if (enterRes && !enterRes.error) {
      event.value = enterRes.event
    } else {
      event.value = await getOne(id)
    }
  } finally {
    loading.value = false
  }
  if (canLaunch.value) {
    if (!academyDone.value && !academyActive.value) startAcademy()
  } else {
    carousel.start().catch(() => {})
  }
}

function leave() {
  if (window.opener) window.close()
  else router.push({ name: PORTAL_TAB.HOME })
}

function onLaunchClick() {
  if (!event.value) return
  if (marathonStep.value < event.value.tmdb_ids.length - 1) {
    setTimeout(() => {
      marathonStep.value += 1
      academyDone.value = false
      academyActive.value = false
      startAcademy()
    }, 500)
  }
}

onMounted(() => {
  load()
  tickTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
  if (academyTimer) clearInterval(academyTimer)
})
</script>
