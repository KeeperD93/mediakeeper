<template>
  <!--
    Fullscreen "Surprise me" overlay.

    Flow:
      1. Pick a kind (movie / tv / manga / documentary).
      2. Backend returns ~50 random Emby items for that kind.
      3. User clicks "Lancer". A highlight sprints through the grid,
         slowing down over 5s, and lands on one card.
      4. That card flips to reveal its real poster, zooms in, and
         an info panel appears (title, year, runtime, rating,
         synopsis, "Watch trailer", "Launch on Emby").
      5. "Je retente ma chance" flips the card back and restarts.
  -->
  <Teleport to="body">
    <div class="so" role="dialog" aria-modal="true" @click.self="close">
      <button class="so-close" :aria-label="$t('common.close')" @click="close">
        <X :size="22" :stroke-width="2.5" />
      </button>

      <div class="so-tabs">
        <button
          v-for="k in KINDS"
          :key="k.key"
          class="so-tab"
          :class="{ 'so-tab--active': kind === k.key }"
          :disabled="rolling"
          @click="selectKind(k.key)"
        >
          {{ $t(k.label) }}
        </button>
      </div>

      <div ref="gridWrapRef" class="so-grid-wrap">
        <div v-if="revealed" class="so-reveal" :class="{ 'so-reveal--show': revealed }">
          <div class="so-reveal-card">
            <img
              v-if="winner?.poster_url"
              :src="winner.poster_url"
              :alt="winner.title"
              class="so-reveal-poster"
            />
          </div>
          <div class="so-reveal-info">
            <h2>{{ winner?.title }}</h2>
            <div class="so-reveal-meta">
              <span v-if="winner?.vote" class="so-reveal-vote">★ {{ winner.vote }}</span>
              <span v-if="winner?.release_date">{{ winner.release_date?.slice(0, 4) }}</span>
              <span v-if="winner?.runtime">{{ formatRuntime(winner.runtime) }}</span>
            </div>
            <p v-if="winner?.overview" class="so-reveal-overview">{{ winner.overview }}</p>
            <div class="so-reveal-actions">
              <button v-if="winner" class="so-btn so-btn--ghost" @click="openTrailer">
                <Video :size="18" />
                {{ $t('portal.detail.watchTrailer') }}
              </button>
              <a
                v-if="winner?.emby_url"
                :href="winner.emby_url"
                target="_blank"
                class="so-btn so-btn--primary"
              >
                <img src="/assets/icons/emby.svg" alt="" class="so-btn-emby" />
                {{ $t('portal.hero.play') }}
              </a>
            </div>
          </div>
        </div>

        <div
          v-else
          class="so-grid"
          :style="{
            '--so-cell': cellSize + 'px',
            '--so-gap': gap + 'px',
            '--so-cols': colCount,
          }"
        >
          <div
            v-for="(item, idx) in pool"
            :key="idx"
            class="so-cell"
            :class="{ 'so-cell--active': activeIdx === idx }"
          >
            <span class="so-cell-q">?</span>
          </div>
          <div v-if="loading" class="so-loading">{{ $t('common.loading') }}</div>
        </div>
      </div>

      <div class="so-footer">
        <button
          v-if="!revealed"
          class="so-roll"
          :disabled="rolling || !pool.length"
          @click="launchRoll"
        >
          <Dices :size="22" />
          {{ $t('portal.surprise.roll') }}
        </button>
        <button v-else class="so-retry" @click="retry">
          <Dice1 :size="18" />
          {{ $t('portal.surprise.retry') }}
        </button>
        <!-- Sound toggle sits right next to the roll/retry button so
             the user can mute the tick during the draw. -->
        <button
          class="so-mute"
          :class="{ 'so-mute--off': !soundOn }"
          :title="soundOn ? $t('portal.surprise.soundOn') : $t('portal.surprise.soundOff')"
          @click="toggleSound"
        >
          <Volume2 v-if="soundOn" :size="18" />
          <VolumeX v-else :size="18" />
        </button>
      </div>
    </div>

    <TrailerLightbox
      v-if="lightboxOpen && trailer"
      :trailer="trailer"
      @close="lightboxOpen = false"
    />
  </Teleport>
</template>

<script setup>
import TrailerLightbox from './TrailerLightbox.vue'
import { useSurpriseOverlay } from './useSurpriseOverlay.js'
import { Dice1, Dices, Video, Volume2, VolumeX, X } from 'lucide-vue-next'

import '@/assets/styles/portal/surprise-overlay.css'

const emit = defineEmits(['close'])

const {
  KINDS,
  kind,
  pool,
  loading,
  winner,
  revealed,
  lightboxOpen,
  gridWrapRef,
  cellSize,
  gap,
  colCount,
  rolling,
  activeIdx,
  soundOn,
  trailer,
  toggleSound,
  selectKind,
  launchRoll,
  retry,
  openTrailer,
  formatRuntime,
  close,
} = useSurpriseOverlay(emit)
</script>
