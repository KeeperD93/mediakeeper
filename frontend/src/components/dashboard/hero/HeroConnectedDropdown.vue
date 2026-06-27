<template>
  <div v-if="activeCount > 0" ref="connectedRef" class="hero-connected-wrap">
    <div class="hero-connected hero-connected-clickable" @click.stop="toggleDropdown">
      <span class="hero-connected-dot" />
      <span>{{ $t('dashboard.activeCount', { count: activeCount }) }}</span>
    </div>
  </div>
  <Teleport to="body">
    <div v-if="showPopup" class="hero-dropdown" :style="ddPos" @click.stop>
      <div class="hero-dropdown-header">
        {{ $t('dashboard.users') }} ({{ connectedUsers.length }})
      </div>
      <div class="hero-dropdown-list">
        <div v-for="(u, i) in connectedUsers" :key="i" class="hero-dropdown-row">
          <span class="hero-dropdown-dot" :class="u.isActive ? 'dot-green' : 'dot-gray'" />
          <div class="hero-dropdown-info">
            <span class="hero-dropdown-name">{{ u.name }}</span>
            <span class="hero-dropdown-device">{{ u.device || '—' }}</span>
          </div>
          <span class="hero-dropdown-status" :class="u.isActive ? 'status-active' : 'status-idle'">
            {{ u.isActive ? $t('dashboard.statusActive') : $t('dashboard.statusIdle') }}
          </span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { rootZoom } from '@/utils/zoom'

const props = defineProps({
  allSessions: { type: Array, default: () => [] },
})

const { t } = useI18n()
const showPopup = ref(false)
const connectedRef = ref(null)
const ddPos = ref({})

const connectedUsers = computed(() => {
  const seen = new Map()
  for (const s of props.allSessions) {
    const name = s.user || s.UserName || t('common.unknown')
    if (!seen.has(name))
      seen.set(name, {
        name,
        device: s.device || s.client || '',
        isActive: s.is_playing || s.is_paused,
      })
  }
  return [...seen.values()].sort((a, b) => b.isActive - a.isActive)
})

const activeCount = computed(() => connectedUsers.value.filter(u => u.isActive).length)

function toggleDropdown() {
  if (showPopup.value) {
    showPopup.value = false
    return
  }
  if (connectedRef.value) {
    const z = rootZoom() // admin zoom: divide the final position (utils/zoom)
    const rect = connectedRef.value.getBoundingClientRect()
    ddPos.value = {
      position: 'fixed',
      top: (rect.bottom + 8) / z + 'px',
      right: (window.innerWidth - rect.right) / z + 'px',
      zIndex: 9999,
    }
  }
  showPopup.value = true
}

function onClickOutside(e) {
  if (showPopup.value && connectedRef.value && !connectedRef.value.contains(e.target)) {
    const dd = document.querySelector('.hero-dropdown')
    if (dd && dd.contains(e.target)) return
    showPopup.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') showPopup.value = false
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.hero-connected-wrap {
  position: absolute;
  top: var(--space-3-5);
  right: var(--space-5);
  z-index: 20;
}
.hero-connected {
  display: flex;
  align-items: center;
  /* 6 px between dot and label — between --space-1 and --space-2. */
  gap: 6px;
  font-size: var(--text-2xs);
  color: var(--text-faint);
  background: rgb(0, 0, 0, 0.3);
  backdrop-filter: var(--blur-xs);
  /* 5 / 12 px chip padding — hero-only chip, between --space-1 and
     --space-2 vertically and --space-3 horizontally. */
  padding: 5px var(--space-3);
  border-radius: var(--radius-card);
}
.hero-connected-dot {
  /* 6 px dot — too small for --icon-* (12+). */
  width: 6px;
  height: 6px;
  border-radius: var(--radius-circle);
  background: var(--color-online);
  animation: hero-conn-pulse var(--duration-pulse) ease-in-out infinite;
}
.hero-connected-clickable {
  cursor: pointer;
}
@keyframes hero-conn-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .hero-connected-dot {
    animation: none;
  }
}
</style>
<!-- Non-scoped block intentional: dropdown content uses <Teleport to="body">,
     so scoped-CSS data-v attributes never reach it. All selectors are prefixed
     with .hero-dropdown* to keep the namespace unique. -->
<style>
.hero-dropdown {
  position: fixed;
  /* 300 / 340 px dropdown — hero-only chrome, doesn't follow the
     container-* scale. */
  width: 300px;
  max-height: 340px;
  background: var(--bg-primary);
  backdrop-filter: var(--blur-md);
  border: var(--border-width) solid var(--border-strong);
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: var(--shadow-dropdown);
  animation: dd-in var(--duration-fast) var(--ease-out);
}
@keyframes dd-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.hero-dropdown-header {
  padding: var(--space-3) var(--space-4);
  border-bottom: var(--border-width) solid var(--border-default);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}
.hero-dropdown-list {
  /* 280 px = dropdown height (340) - header. Widget-local. */
  max-height: 280px;
  overflow-y: auto;
  padding: var(--space-1) 0;
}
.hero-dropdown-list::-webkit-scrollbar {
  width: var(--space-1);
}
.hero-dropdown-list::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 2px;
}
.hero-dropdown-row {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  /* 9 / 16 px row padding — vertical between --space-2 and --space-3
     to keep rows compact. */
  padding: 9px var(--space-4);
  transition: var(--transition-bg);
}
.hero-dropdown-row:hover {
  background: var(--surface-1);
}
.hero-dropdown-dot {
  /* 7 px status dot — too small for --icon-* tokens. */
  width: 7px;
  height: 7px;
  border-radius: var(--radius-circle);
  flex-shrink: 0;
}
.hero-dropdown .dot-green {
  background: var(--color-success);
}
.hero-dropdown .dot-gray {
  background: var(--border-ghost);
}
.hero-dropdown-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.hero-dropdown-name {
  color: var(--text-primary);
  font-weight: var(--font-medium);
  /* 13 px between --text-xs (~12) and --text-sm (~13.1). */
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hero-dropdown-device {
  color: var(--text-very-faint);
  /* 11 px between --text-3xs (~9.9) and --text-2xs (~11.2). */
  font-size: 11px;
}
.hero-dropdown-status {
  /* 10 px chip label — below the scale, dropdown-local. */
  font-size: 10px;
  flex-shrink: 0;
  padding: var(--space-half) 7px;
  border-radius: 5px;
  font-weight: var(--font-medium);
}
.hero-dropdown .status-active {
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}
.hero-dropdown .status-idle {
  background: var(--surface-2);
  color: var(--text-very-faint);
}
</style>
