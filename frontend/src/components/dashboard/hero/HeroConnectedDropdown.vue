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
          <span
            class="hero-dropdown-status"
            :class="u.isActive ? 'status-active' : 'status-idle'"
          >
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
    const rect = connectedRef.value.getBoundingClientRect()
    ddPos.value = {
      position: 'fixed',
      top: rect.bottom + 8 + 'px',
      right: window.innerWidth - rect.right + 'px',
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
  top: 14px;
  right: 20px;
  z-index: 20;
}
.hero-connected {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.5);
  background: rgb(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
  padding: 5px 12px;
  border-radius: var(--radius-card);
}
.hero-connected-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
}
.hero-connected-clickable {
  cursor: pointer;
}
</style>
<!-- Non-scoped block intentional: dropdown content uses <Teleport to="body">,
     so scoped-CSS data-v attributes never reach it. All selectors are prefixed
     with .hero-dropdown* to keep the namespace unique. -->
<style>
.hero-dropdown {
  position: fixed;
  width: 300px;
  max-height: 340px;
  background: rgb(15, 20, 35, 0.97);
  backdrop-filter: blur(16px);
  border: 1px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: 0 12px 40px rgb(0, 0, 0, 0.5);
  animation: dd-in 0.12s ease-out;
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
  padding: 12px 16px;
  border-bottom: 1px solid rgb(255, 255, 255, 0.06);
  font-size: 12px;
  font-weight: 500;
  color: rgb(255, 255, 255, 0.6);
}
.hero-dropdown-list {
  max-height: 280px;
  overflow-y: auto;
  padding: 4px 0;
}
.hero-dropdown-list::-webkit-scrollbar {
  width: 4px;
}
.hero-dropdown-list::-webkit-scrollbar-thumb {
  background: rgb(255, 255, 255, 0.1);
  border-radius: 2px;
}
.hero-dropdown-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  transition: background 0.1s;
}
.hero-dropdown-row:hover {
  background: rgb(255, 255, 255, 0.03);
}
.hero-dropdown-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.hero-dropdown .dot-green {
  background: var(--color-success);
}
.hero-dropdown .dot-gray {
  background: rgb(255, 255, 255, 0.15);
}
.hero-dropdown-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.hero-dropdown-name {
  color: rgb(255, 255, 255, 0.85);
  font-weight: 500;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hero-dropdown-device {
  color: rgb(255, 255, 255, 0.25);
  font-size: 11px;
}
.hero-dropdown-status {
  font-size: 10px;
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 5px;
  font-weight: 500;
}
.hero-dropdown .status-active {
  background: rgb(var(--color-success-rgb), 0.12);
  color: var(--color-success);
}
.hero-dropdown .status-idle {
  background: rgb(255, 255, 255, 0.04);
  color: rgb(255, 255, 255, 0.3);
}
</style>
