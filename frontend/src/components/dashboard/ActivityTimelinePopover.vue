<template>
  <!-- TMDB Popover — teleported to <body> so it escapes the
       vue-grid-layout transformed ancestor (which would otherwise
       clip / re-anchor a position:fixed child). Coordinates are
       already in viewport space (see togglePopover). -->
  <Teleport to="body">
    <div v-if="popover.visible" ref="cardRef" class="pop-card" :style="popover.style" @click.stop>
      <div v-if="popover.loading" class="pop-loading">
        <MkSpinner size="sm" />
      </div>
      <div v-else-if="popover.error" class="pop-loading">
        <span class="pop-error-text">{{ popover.error }}</span>
      </div>
      <template v-else-if="popover.data">
        <div class="pop-top">
          <div v-if="popover.data.poster" class="pop-poster">
            <img
              :src="popover.data.poster"
              @error="$event => ($event.target.style.display = 'none')"
            />
          </div>
          <div class="pop-info">
            <h3 class="pop-title">{{ popover.data.title }}</h3>
            <div class="pop-chips">
              <span v-if="popover.data.year" class="pop-chip">{{ popover.data.year }}</span>
              <span v-if="popover.data.vote" class="pop-chip pop-chip-vote">
                ⭐ {{ popover.data.vote }}
              </span>
              <span v-if="popover.data.runtime" class="pop-chip">
                {{ $t('dashboard.runtimeMinutes', { n: popover.data.runtime }) }}
              </span>
            </div>
            <div v-if="isTv(popover.data)" class="pop-chips">
              <span v-if="popover.data.seasons_count" class="pop-chip">
                {{
                  $t(
                    'dashboard.seasonsCount',
                    { n: popover.data.seasons_count },
                    popover.data.seasons_count,
                  )
                }}
              </span>
              <span v-if="popover.data.episodes_count" class="pop-chip">
                {{ $t('dashboard.episodesCount', { n: popover.data.episodes_count }) }}
              </span>
            </div>
            <div v-if="popover.data.genres?.length" class="pop-genres">
              <span v-for="g in popover.data.genres.slice(0, 3)" :key="g" class="pop-genre">
                {{ g }}
              </span>
            </div>
          </div>
        </div>
        <p v-if="popover.data.overview" class="pop-overview">{{ popover.data.overview }}</p>
      </template>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { isTv } from '@/constants/media'
import MkSpinner from '@/components/common/MkSpinner.vue'

defineProps({
  popover: { type: Object, required: true },
})

// Exposed so the parent's click-outside handler (useActivityTimeline.onDocClick)
// can test whether a click landed inside the teleported card.
const cardRef = ref(null)
defineExpose({ contains: target => cardRef.value?.contains(target) })
</script>

<style scoped>
.pop-card {
  /* ``position: fixed`` so the popover escapes the parent ``.vgl-item``
   * overflow:hidden clip. Coordinates are computed in viewport space
   * by useActivityTimeline togglePopover. z-index lifts above the
   * dashboard chrome (sidebar/topbar are lower). */
  position: fixed;
  z-index: var(--z-dropdown, 100);
  width: 340px;
  max-width: calc(100vw - 48px);
  background: var(--bg-primary);
  backdrop-filter: var(--blur-md);
  border: var(--border-width) solid var(--card-border, var(--border-default));
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  animation: pop-in var(--duration-fast) ease-out;
}
@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.pop-loading {
  padding: var(--space-8) var(--space-5);
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-xs);
}
.pop-error-text {
  color: var(--color-error);
  font-size: var(--text-xs);
}
.pop-top {
  display: flex;
  gap: var(--space-3-5);
  padding: var(--space-4) var(--space-4) 0;
}
.pop-poster {
  flex-shrink: 0;
  width: 80px;
}
.pop-poster img {
  width: 100%;
  border-radius: var(--radius-btn);
  box-shadow: var(--shadow-sm);
}
.pop-info {
  flex: 1;
  min-width: 0;
}
.pop-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 var(--space-1);
  line-height: var(--lh-compact);
}
.pop-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}
.pop-chip {
  font-size: var(--text-3xs);
  padding: var(--space-half) 7px;
  border-radius: var(--radius-sm);
  background: var(--heat-0, var(--surface-3));
  color: var(--text-muted);
}
.pop-chip-vote {
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
}
.pop-genres {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.pop-genre {
  /* 9px font + 3px radius are pop-genre-only — too small for the
     standard ``--text-3xs`` (~10px) and ``--radius-sm``. */
  font-size: 9px;
  padding: var(--space-half) 6px;
  border-radius: 3px;
  /* Neutral chip — genres are not semantically coloured (no "good"
     or "bad" genre), and the accent tint pulled the global hue onto
     decorative tags. */
  background: var(--surface-2);
  color: var(--text-secondary);
}
.pop-overview {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--lh-normal);
  margin: 0;
  /* Bottom padding matches the .pop-top top padding so the overview
     text never touches the tooltip border. ``-webkit-line-clamp``
     handles the 5-line truncation on its own — the previous
     ``max-height: 100px`` was capping the box BEFORE the padding could
     render, defeating the bottom space entirely. */
  padding: var(--space-2-5) var(--space-4) var(--space-5);
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
