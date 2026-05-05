<template>
  <div class="pt-bell-wrap">
    <button
      ref="btnRef"
      class="pt-nav-icon pt-bell"
      :title="$t('portal.notifications.title')"
      @click="toggle"
    >
      <Bell :size="20" />
      <span v-if="unread > 0" class="pt-bell-badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>

    <Teleport to="body">
      <transition name="pt-bell-pop">
        <div v-if="open" class="pt-bell-popup" :style="popupStyle" @click.stop>
          <header class="pt-bell-head">
            <h3>{{ $t('portal.notifications.title') }}</h3>
          </header>
          <div class="pt-bell-list">
            <div v-if="loading" class="pt-bell-empty">{{ $t('common.loading') }}</div>
            <div v-else-if="!items.length" class="pt-bell-empty">
              {{ $t('portal.notifications.empty') }}
            </div>
            <button
              v-for="n in items"
              :key="n.id"
              class="pt-bell-item"
              :class="{ 'pt-bell-item--unread': !n.read }"
              @click="onClick(n)"
            >
              <span class="pt-bell-icon">{{ iconForNotification(n.type) }}</span>
              <div class="pt-bell-body">
                <div class="pt-bell-text">{{ labelForNotification(n, t) }}</div>
                <div class="pt-bell-time">{{ timeAgoForNotification(n.created_at, t) }}</div>
              </div>
            </button>
          </div>
        </div>
      </transition>

      <div v-if="open" class="pt-bell-shade" @click="close" />
    </Teleport>

    <EventDetailModal
      v-if="detailEventId"
      :event-id="detailEventId"
      @close="detailEventId = null"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useNotifications } from '@/composables/portal/useNotifications'
import EventDetailModal from './EventDetailModal.vue'
import { NOTIF_TYPE } from '@/constants/notifications'
import { PORTAL_TAB } from '@/constants/portal'
import {
  iconForNotification,
  labelForNotification,
  timeAgoForNotification,
} from '@/utils/portal/notificationLabel'
import { Bell } from 'lucide-vue-next'

const router = useRouter()

const { t } = useI18n()
const { items, unread, loading, fetchList, markRead, markAllRead, startPolling, stopPolling } =
  useNotifications()

const open = ref(false)
const detailEventId = ref(null)
const btnRef = ref(null)
const popupStyle = ref({})

// Anchor the popup to the trigger button's rect. The nav has a
// max-width so on wide viewports the bell sits far from the viewport's
// right edge — a static `right: 2rem` drifts the popup away from it.
function computePopupStyle() {
  const el = btnRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const rightOffset = Math.max(8, window.innerWidth - rect.right)
  popupStyle.value = {
    top: `${Math.round(rect.bottom + 8)}px`,
    right: `${Math.round(rightOffset)}px`,
  }
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    computePopupStyle()
    await fetchList(false)
    // Opening the popup is the read action — clears the badge and
    // flags every listed item on the server.
    if (unread.value > 0) await markAllRead()
  }
}
function close() {
  open.value = false
}
function onResize() {
  if (open.value) computePopupStyle()
}

async function onClick(n) {
  if (!n.read) await markRead(n.id)
  const p = n.payload || {}
  // Request status notifs open the media detail page.
  if (n.type === NOTIF_TYPE.REQUEST_APPROVED || n.type === NOTIF_TYPE.REQUEST_AVAILABLE) {
    if (p.tmdb_id && p.media_type) {
      close()
      router.push({
        name: 'portal-media-detail',
        params: { type: p.media_type, id: p.tmdb_id },
      })
    }
    return
  }
  // Ticket notifs deep-link to the ticket detail page so the user
  // sees the new reply / status without hunting for it.
  if (
    n.type === NOTIF_TYPE.TICKET_CREATED ||
    n.type === NOTIF_TYPE.TICKET_REPLIED ||
    n.type === NOTIF_TYPE.TICKET_RESOLVED
  ) {
    if (p.ticket_id) {
      close()
      router.push({ name: PORTAL_TAB.TICKET_DETAIL, params: { id: p.ticket_id } })
    }
    return
  }
  const eid = p.event_id
  if (!eid) return
  // Room-open notif jumps directly to the cinema room. Everything
  // else opens the detail modal.
  if (n.type === NOTIF_TYPE.EVENT_ROOM_OPEN) {
    close()
    router.push({ name: 'portal-rooms', params: { id: eid } })
    return
  }
  detailEventId.value = eid
  close()
}

onMounted(() => {
  startPolling(30000)
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onResize, { passive: true })
})
onBeforeUnmount(() => {
  stopPolling()
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize)
})
</script>

<style scoped>
.pt-bell-wrap {
  position: relative;
  display: inline-block;
}

/* The button carries class="pt-nav-icon pt-bell"; the shell (size,
   radius, border, background, hover) comes from .pt-nav-icon. This
   file only declares bell-specific extras (badge, popup, shade). */
.pt-bell {
  position: relative;
}

.pt-bell-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--portal-color-error);
  color: #fff;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-extrabold);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgb(20, 20, 30, 0.95);
}

.pt-bell-shade {
  position: fixed;
  inset: 0;
  z-index: 8800;
}

.pt-bell-popup {
  position: fixed;
  top: 70px;
  right: clamp(0.5rem, 4%, 2rem);
  width: clamp(280px, 90vw, 380px);
  max-height: 70vh;
  background: rgb(20, 20, 30, 0.97);
  border: 1px solid var(--portal-border-strong);
  border-radius: var(--radius-card);
  box-shadow: 0 24px 60px rgb(0, 0, 0, 0.6);
  color: #fff;
  z-index: 8900;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: var(--portal-blur-lg);
  -webkit-backdrop-filter: var(--portal-blur-lg);
}
.pt-bell-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--portal-border-default);
}
.pt-bell-head h3 {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-extrabold);
}
.pt-bell-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.4rem;
}
.pt-bell-empty {
  padding: 1.5rem 1rem;
  text-align: center;
  color: rgb(255, 255, 255, 0.45);
  font-size: var(--portal-text-sm);
}
.pt-bell-item {
  display: flex;
  width: 100%;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.7rem 0.75rem;
  border: none;
  background: transparent;
  color: #fff;
  cursor: pointer;
  text-align: left;
  border-radius: var(--radius-btn);
  transition: background var(--portal-dur-fast);
}
.pt-bell-item:hover {
  background: var(--portal-surface-3);
}
.pt-bell-item--unread {
  background: rgb(67, 56, 202, 0.12);
}
.pt-bell-item--unread:hover {
  background: rgb(67, 56, 202, 0.2);
}
.pt-bell-icon {
  font-size: var(--portal-text-lg);
  flex-shrink: 0;
}
.pt-bell-body {
  flex: 1;
  min-width: 0;
}
.pt-bell-text {
  font-size: var(--portal-text-sm);
  line-height: 1.35;
  color: var(--portal-text-primary);
  /* stylelint-disable-next-line declaration-property-value-keyword-no-deprecated -- non-standard but widely supported; behaviour differs from overflow-wrap: break-word on CJK */
  word-break: break-word;
}
.pt-bell-time {
  font-size: var(--portal-text-2xs);
  color: rgb(255, 255, 255, 0.45);
  margin-top: 0.2rem;
}

.pt-bell-pop-enter-active,
.pt-bell-pop-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.pt-bell-pop-enter-from,
.pt-bell-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
