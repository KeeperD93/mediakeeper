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
          <span
            v-if="tab.id === 'lectures' && sessionsCount > 0 && !lecturesTabSeen"
            class="tl-tab-count"
          >
            {{ sessionsCount }}
          </span>
          <span
            v-else-if="tab.id === 'alertes' && unreadAlerts > 0 && !alertesTabSeen"
            class="tl-tab-count tl-tab-count-alert"
          >
            {{ unreadAlerts }}
          </span>
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

    <!-- TMDB Popover -->
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
  lecturesTabSeen,
  alertesTabSeen,
  sessionsCount,
  unreadAlerts,
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
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 8px;
}
.tl-title {
  font-size: var(--text-base);
  font-weight: var(--font-regular);
  color: var(--text-secondary);
  margin: 0;
}

.tl-tabs {
  display: flex;
  gap: 6px;
  margin-right: auto;
  flex-wrap: wrap;
}
.tl-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-3xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
  -webkit-tap-highlight-color: transparent;
  white-space: nowrap;
}
@media (hover: hover) {
  .tl-tab:hover:not(.active) {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}
.tl-tab.active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: #fff;
  box-shadow: var(--mk-pill-shadow-sm);
}
.tl-tab-count {
  font-size: 9px;
  background: rgb(99, 102, 241, 0.3);
  color: var(--accent-400);
  padding: 1px 6px;
  border-radius: var(--radius-pill);
  font-weight: var(--font-bold);
  min-width: 14px;
  text-align: center;
}
.tl-tab.active .tl-tab-count {
  background: rgb(255, 255, 255, 0.2);
  color: #fff;
}
.tl-tab-count-alert {
  background: rgb(var(--color-error-rgb), 0.2) !important;
  color: var(--color-error) !important;
}
.tl-tab.active .tl-tab-count-alert {
  background: rgb(255, 255, 255, 0.2) !important;
  color: #fff !important;
}

.tl-track {
  border-left: 1px solid var(--card-border, var(--border-default));
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
  padding: 8px 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
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
  left: -23px;
  top: 12px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid var(--dash-bg, #0a0e1a);
}
.dot-active {
  background: #22c55e;
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
  line-height: 1.4;
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
  border-bottom: 1px dotted rgb(255, 255, 255, 0.25);
}
.tl-media:hover {
  border-bottom-color: rgb(255, 255, 255, 0.6);
}
.tl-meta {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: 2px 0 0;
}

.tl-tag {
  font-size: var(--text-3xs);
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-top: 2px;
}
.tag-green {
  background: rgb(34, 197, 94, 0.1);
  color: var(--color-success);
}
.tag-yellow {
  background: rgb(250, 204, 21, 0.1);
  color: #facc15;
}

.tl-empty {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 20px 0;
}

.tl-track::-webkit-scrollbar {
  width: 4px;
}
.tl-track::-webkit-scrollbar-thumb {
  background: var(--text-muted);
  opacity: 0.4;
  border-radius: 2px;
}

/* ---- TMDB POPOVER ---- */
.pop-card {
  position: absolute;
  z-index: 50;
  width: 340px;
  max-width: calc(100vw - 48px);
  background: var(--pop-bg, rgb(15, 20, 35, 0.97));
  backdrop-filter: blur(16px);
  border: 1px solid var(--card-border, rgb(255, 255, 255, 0.1));
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: 0 12px 40px rgb(0, 0, 0, 0.5);
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
  padding: 32px 20px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: var(--text-xs);
}
.pop-error-text {
  color: var(--color-error);
  font-size: var(--text-xs);
}
.pop-top {
  display: flex;
  gap: 14px;
  padding: 16px 16px 0;
}
.pop-poster {
  flex-shrink: 0;
  width: 80px;
}
.pop-poster img {
  width: 100%;
  border-radius: var(--radius-btn);
  box-shadow: 0 2px 12px rgb(0, 0, 0, 0.3);
}
.pop-info {
  flex: 1;
  min-width: 0;
}
.pop-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 6px;
  line-height: var(--lh-compact);
}
.pop-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}
.pop-chip {
  font-size: var(--text-3xs);
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--heat-0, var(--surface-3));
  color: var(--text-muted);
}
.pop-chip-vote {
  background: rgb(250, 204, 21, 0.12);
  color: #facc15;
}
.pop-genres {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pop-genre {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgb(99, 102, 241, 0.12);
  color: var(--accent-400);
}
.pop-overview {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--lh-normal);
  margin: 0;
  padding: 10px 16px 14px;
  max-height: 100px;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
