<template>
  <div class="wg-eng" :class="{ 'wg-eng-editing': editing }">
    <div class="wg-eng-head">
      <span class="wg-eng-title">{{ $t('dashboard.portalEngagement.title') }}</span>
      <div v-if="!editing" class="wg-eng-toggle" role="tablist">
        <button
          type="button"
          class="wg-eng-toggle-btn"
          :class="{ 'is-active': window === 1 }"
          :aria-pressed="window === 1"
          @click="setWindow(1)"
        >
          24h
        </button>
        <button
          type="button"
          class="wg-eng-toggle-btn"
          :class="{ 'is-active': window === 7 }"
          :aria-pressed="window === 7"
          @click="setWindow(7)"
        >
          7j
        </button>
      </div>
    </div>

    <div class="wg-eng-grid">
      <StatTile
        v-for="tile in tiles"
        :key="tile.key"
        :icon="tile.icon"
        :label="$t(tile.labelKey)"
        :value="loading ? '—' : (data[tile.key] ?? 0)"
        :accent="tile.accent"
        :route="tile.route"
        :disabled="editing"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Bookmark, Trophy, MessageSquare, Star } from 'lucide-vue-next'
import { fetchApiResponse } from '@/composables/useApi'
import StatTile from './StatTile.vue'

defineProps({ editing: { type: Boolean, default: false } })

const window = ref(1)
const loading = ref(true)
const data = ref({
  new_lists: 0,
  achievements_unlocked: 0,
  chat_messages: 0,
  reviews: 0,
})

const tiles = computed(() => [
  {
    key: 'new_lists',
    icon: Bookmark,
    accent: 'var(--accent-300)',
    labelKey: 'dashboard.portalEngagement.newLists',
    route: { path: '/admin/portal', query: { tab: 'lists' } },
  },
  {
    key: 'achievements_unlocked',
    icon: Trophy,
    accent: 'var(--color-warning)',
    labelKey: 'dashboard.portalEngagement.achievements',
    route: '/portal/leaderboard',
  },
  {
    key: 'chat_messages',
    icon: MessageSquare,
    accent: 'var(--color-info)',
    labelKey: 'dashboard.portalEngagement.chatMessages',
    route: null,
  },
  {
    key: 'reviews',
    icon: Star,
    accent: 'var(--color-rating)',
    labelKey: 'dashboard.portalEngagement.reviews',
    route: null,
  },
])

async function load() {
  loading.value = true
  try {
    const res = await fetchApiResponse(`/api/portal/admin/engagement?window=${window.value}`, {
      retryOn401: false,
      redirectOn401: false,
    })
    if (res && res.ok) {
      const d = await res.json().catch(() => null)
      if (d) data.value = { ...data.value, ...d }
    }
  } catch {
    /* silent: widget fetch, card stays blank */
  }
  loading.value = false
}

function setWindow(days) {
  if (window.value === days) return
  window.value = days
  load()
}

onMounted(load)
</script>

<style scoped>
.wg-eng {
  background: var(--card-bg);
  border-radius: var(--radius-card);
  padding: var(--space-3) var(--space-3-5);
  border: var(--border-width-thin) solid var(--border-default);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5);
  min-width: 0;
  overflow: hidden;
}

.wg-eng-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-width: 0;
}
.wg-eng-title {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1 1 auto;
  min-width: 0;
}

.wg-eng-toggle {
  display: inline-flex;
  gap: var(--space-1);
  flex-shrink: 0;
}
@media (min-width: 768px) {
  /* Desktop only: clear the absolute ``.widget-badge-icon`` (14px @ right:10px)
     sitting outside the card padding. */
  .wg-eng-toggle {
    margin-right: 22px;
  }
}
.wg-eng-toggle-btn {
  min-height: var(--touch-target);
  padding: 3px var(--space-2-5);
  border-radius: var(--radius-pill);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-3xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition:
    background var(--duration-base) var(--ease-out),
    border-color var(--duration-base) var(--ease-out),
    color var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out),
    transform var(--duration-base) var(--ease-out);
  backdrop-filter: var(--blur-xs);
}
@media (min-width: 768px) {
  .wg-eng-toggle-btn {
    min-height: 26px;
  }
}
.wg-eng-toggle-btn.is-active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: var(--text-primary);
  box-shadow: var(--mk-pill-shadow-sm);
}
@media (hover: hover) {
  .wg-eng-toggle-btn:not(.is-active):hover {
    border-color: rgb(255, 255, 255, 0.18);
    color: rgb(255, 255, 255, 0.85);
    transform: translateY(-1px);
  }
}

.wg-eng-grid {
  display: grid;
  /* Fixed 2×2 keeps tiles balanced at every card width. */
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: min-content;
  align-content: center;
  gap: var(--space-2);
  flex: 1;
  min-height: 0;
}

@media (prefers-reduced-motion: reduce) {
  .wg-eng-toggle-btn {
    transition: none;
  }
}
</style>
