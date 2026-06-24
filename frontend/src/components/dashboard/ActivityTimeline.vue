<template>
  <div ref="rootRef" class="tl-root">
    <div class="tl-header">
      <p class="tl-title">{{ $t('dashboard.recentActivity') }}</p>
      <div class="tl-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tl-tab"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="tl-track" :class="{ 'tl-expanded': activeTab !== 'all' }">
      <div
        v-for="(item, i) in filteredItems"
        :key="item.key || i"
        class="tl-entry"
        :style="{ animationDelay: i * 30 + 'ms' }"
      >
        <div class="tl-dot" :class="dotClass(item)" />
        <div class="tl-body">
          <p class="tl-text">
            <span class="tl-user">{{ item.user || $t('dashboard.system') }}</span>
            {{ item.action }}
            <span v-if="item.media" ref="mediaRefs" class="tl-media-wrap">
              <span class="tl-media" @click.stop="togglePopover(item, $event)">
                {{ item.media }}
              </span>
            </span>
          </p>
          <p class="tl-meta">
            {{ item.device || '' }}{{ item.device && item.ago ? ' · ' : '' }}{{ item.ago }}
          </p>
        </div>
        <span v-if="item.tag" class="tl-tag" :class="item.tagClass">{{ item.tag }}</span>
      </div>

      <p v-if="filteredItems.length === 0" class="tl-empty">{{ $t('dashboard.noActivity') }}</p>
    </div>

    <!-- TMDB Popover — teleported to <body> so it escapes the
         vue-grid-layout transformed ancestor (which would otherwise
         clip / re-anchor a position:fixed child). Coordinates are
         already in viewport space (see togglePopover). -->
    <Teleport to="body">
      <div
        v-if="popover.visible"
        ref="popoverRef"
        class="pop-card"
        :style="popover.style"
        @click.stop
      >
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
                  {{ popover.data.runtime }} min
                </span>
              </div>
              <div v-if="isTv(popover.data)" class="pop-chips">
                <span v-if="popover.data.seasons_count" class="pop-chip">
                  {{ popover.data.seasons_count }} season{{
                    popover.data.seasons_count > 1 ? 's' : ''
                  }}
                </span>
                <span v-if="popover.data.episodes_count" class="pop-chip">
                  {{ popover.data.episodes_count }} ep.
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
  </div>
</template>

<script setup>
import { useActivityTimeline } from './useActivityTimeline.js'
import { isTv } from '@/constants/media'
import MkSpinner from '@/components/common/MkSpinner.vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  alerts: { type: Array, default: () => [] },
  sessions: { type: Array, default: () => [] },
  seenAlertIds: { type: Set, default: () => new Set() },
  embyBaseUrl: { type: String, default: '' },
})

const {
  activeTab,
  rootRef,
  popoverRef,
  tabs,
  filteredItems,
  popover,
  switchTab,
  togglePopover,
  dotClass,
} = useActivityTimeline(props)
</script>

<style scoped>
.tl-root {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3-5);
  flex-wrap: wrap;
  gap: var(--space-2);
}
.tl-title {
  font-size: var(--text-base);
  font-weight: var(--font-regular);
  color: var(--text-muted);
  margin: 0;
}

.tl-tabs {
  display: flex;
  gap: var(--space-1);
  margin-right: auto;
  flex-wrap: wrap;
}
.tl-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: var(--touch-target);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-strong);
  color: var(--text-muted);
  font-size: var(--text-3xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition:
    var(--transition-bg), var(--transition-border), var(--transition-color),
    var(--transition-transform);
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  white-space: nowrap;
}
@media (min-width: 768px) {
  /* Desktop: compact pill, mouse precision doesn't need the 44px touch
     target. ``--icon-frame-sm`` (28px) feels too tight against the
     standard pill padding — 32px stays inline with the rest of the
     dashboard chips. */
  .tl-tab {
    min-height: 32px;
  }
}
@media (hover: hover) {
  .tl-tab:hover:not(.active) {
    border-color: var(--border-intense);
    color: var(--text-secondary);
    transform: translateY(-1px);
  }
}
.tl-tab.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: var(--text-primary);
  /* Halo intentionally still wired to --mk-pill-shadow-sm. The global
     killswitch --mk-glow: 0 currently flattens it; flipping --mk-glow
     back to 1 restores the halo here without touching this rule. */
  box-shadow: var(--mk-pill-shadow-sm);
}
.tl-track {
  border-left: var(--border-width) solid var(--card-border);
  /* 6px / 18px keep the dot column aligned with the existing layout —
     no spacing token matches both, kept in px since this is a single
     widget. */
  margin-left: 6px;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  transition: max-height var(--duration-slow);
}

.tl-entry {
  position: relative;
  padding: var(--space-2) 0;
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  animation: tl-cascade var(--duration-slow) ease-out both;
}
@keyframes tl-cascade {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tl-dot {
  position: absolute;
  /* -23 / 12 / 9 / 2 are ad-hoc dot-on-rail geometry — no spacing
     token matches and the values only live here. */
  left: -23px;
  top: 12px;
  width: 9px;
  height: 9px;
  border-radius: var(--radius-circle);
  border: 2px solid var(--dash-bg);
}
.dot-active {
  background: var(--color-success);
}
.dot-error {
  background: var(--color-error);
}
.dot-past {
  background: var(--text-muted);
  opacity: 0.5;
}

.tl-body {
  flex: 1;
  min-width: 0;
}
.tl-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0;
  line-height: var(--lh-snug);
}
.tl-user {
  color: var(--text-secondary);
  font-weight: var(--font-regular);
}
.tl-media-wrap {
  position: relative;
}
.tl-media {
  color: var(--text-primary);
  cursor: pointer;
  transition: border-bottom-color var(--duration-fast);
  border-bottom: var(--border-width) dotted var(--text-very-faint);
}
@media (hover: hover) {
  .tl-media:hover {
    border-bottom-color: var(--text-secondary);
  }
}
.tl-meta {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: var(--space-half) 0 0;
}

.tl-tag {
  font-size: var(--text-3xs);
  padding: var(--space-half) var(--space-2);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  margin-top: var(--space-half);
}
.tag-green {
  background: rgb(var(--color-success-rgb), 0.1);
  color: var(--color-success);
}
.tag-yellow {
  background: rgb(var(--color-warning-rgb), 0.1);
  color: var(--color-warning);
}

.tl-empty {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: var(--space-5) 0;
}

.tl-track::-webkit-scrollbar {
  width: var(--scrollbar-width, 4px);
}
.tl-track::-webkit-scrollbar-thumb {
  background: var(--text-muted);
  opacity: 0.4;
  border-radius: 2px;
}

/* ---- TMDB POPOVER ---- */
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
