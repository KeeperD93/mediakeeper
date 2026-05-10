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
      <button
        v-for="tile in tiles"
        :key="tile.key"
        class="wg-eng-tile"
        :class="{ 'wg-eng-tile-static': !tile.route }"
        :disabled="editing || !tile.route"
        @click="tile.route && goTo(tile.route)"
      >
        <component :is="tile.icon" :size="16" class="wg-eng-ic" :style="{ color: tile.color }" />
        <span class="wg-eng-val">{{ loading ? '—' : (data[tile.key] ?? 0) }}</span>
        <span class="wg-eng-label">{{ $t(tile.labelKey) }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ListPlus, Trophy, MessageSquare, Star } from 'lucide-vue-next'
import { fetchApiResponse } from '@/composables/useApi'

defineProps({ editing: { type: Boolean, default: false } })

const router = useRouter()

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
    icon: ListPlus,
    color: 'var(--accent-500)',
    labelKey: 'dashboard.portalEngagement.newLists',
    route: { path: '/admin/portal', query: { tab: 'lists' } },
  },
  {
    key: 'achievements_unlocked',
    icon: Trophy,
    color: '#fbbf24',
    labelKey: 'dashboard.portalEngagement.achievements',
    route: '/portal/leaderboard',
  },
  {
    key: 'chat_messages',
    icon: MessageSquare,
    color: '#60a5fa',
    labelKey: 'dashboard.portalEngagement.chatMessages',
    route: null,
  },
  {
    key: 'reviews',
    icon: Star,
    color: '#f472b6',
    labelKey: 'dashboard.portalEngagement.reviews',
    route: null,
  },
])

function goTo(target) {
  router.push(target)
}

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
  background: var(--card-bg, var(--surface-1));
  border-radius: var(--radius-card);
  padding: 12px 14px;
  border: 0.5px solid var(--border-default);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
}

.wg-eng-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}
.wg-eng-title {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wg-eng-toggle {
  display: inline-flex;
  gap: 4px;
  margin-right: 16px;
}
.wg-eng-toggle-btn {
  min-height: 26px;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  background: rgb(255, 255, 255, 0.03);
  border: 1px solid var(--border-strong);
  color: rgb(255, 255, 255, 0.6);
  font-size: var(--text-3xs);
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: all 0.18s;
  backdrop-filter: var(--blur-xs);
}
.wg-eng-toggle-btn.is-active {
  background: var(--gradient-pill-active);
  border-color: var(--accent-500);
  color: #fff;
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
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  grid-auto-rows: min-content;
  align-content: center;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.wg-eng-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 12px;
  background: rgb(255, 255, 255, 0.02);
  border: 1px solid rgb(255, 255, 255, 0.05);
  border-radius: var(--radius-card);
  color: inherit;
  cursor: pointer;
  text-align: center;
  min-width: 0;
  min-height: 44px;
  overflow: hidden;
  transition:
    border-color var(--duration-base),
    background var(--duration-base),
    transform var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.wg-eng-tile:disabled {
  cursor: default;
}
.wg-eng-tile-static {
  cursor: default;
}
@media (hover: hover) {
  .wg-eng-tile:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--accent-500) 35%, transparent);
    background: rgb(var(--accent-rgb), 0.05);
  }
}
.wg-eng-tile:not(:disabled):active {
  transform: scale(0.98);
}

.wg-eng-ic {
  flex-shrink: 0;
}
.wg-eng-val {
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  line-height: 1.1;
  color: var(--text-primary);
}
.wg-eng-label {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
</style>
