<template>
  <!--
    Expandable Floating Action Button for the Portal home.

    Collapsed: a single "+" button in the bottom-right corner.
    Expanded:  sub-buttons fan upward with a staggered transition.
    The main button rotates 45° (becomes "×") when the menu is open.
    Clicking outside the FAB cluster closes it automatically.
  -->
  <Teleport to="body">
    <div ref="fabRef" class="pt-fab">
      <!-- Sub-buttons (expand upward when open) -->
      <transition-group name="pt-fab-pop" tag="div" class="pt-fab-sub">
        <!-- Promotion (disabled placeholder) -->
        <button
          v-if="open"
          key="promo"
          class="pt-fab-btn pt-fab-btn--disabled"
          disabled
          :title="$t('portal.promotion.soon')"
          :style="{ transitionDelay: '0.06s' }"
        >
          <Star :size="20" />
        </button>

        <!-- Event creation -->
        <button
          v-if="open"
          key="event"
          class="pt-fab-btn"
          :title="$t('portal.mkEvents.create.title')"
          :style="{ transitionDelay: '0.04s' }"
          @click="((eventModalOpen = true), (open = false))"
        >
          <CalendarPlus :size="20" />
        </button>

        <!-- Surprise -->
        <button
          v-if="open"
          key="surprise"
          class="pt-fab-btn"
          :title="$t('portal.surprise.title')"
          :style="{ transitionDelay: '0.02s' }"
          @click="($emit('open-surprise'), (open = false))"
        >
          <Dices :size="20" />
        </button>

        <!-- Chat -->
        <button
          v-if="open && chatAllowed"
          key="chat"
          class="pt-fab-btn"
          :title="$t('portal.chat')"
          :style="{ transitionDelay: '0s' }"
          @click="onChat"
        >
          <MessageSquare :size="20" />
          <span v-if="unreadCount > 0" class="pt-fab-badge">
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </span>
        </button>
      </transition-group>

      <!-- Main toggle button -->
      <button class="pt-fab-main" :class="{ 'pt-fab-main--open': open }" @click.stop="open = !open">
        <Plus :size="24" :stroke-width="2.5" />
        <!-- Unread chat badge — shown on the collapsed FAB only; the
             expanded sub-button below carries its own badge. -->
        <span
          v-if="!open && chatAllowed && unreadCount > 0"
          class="pt-fab-badge pt-fab-badge--main"
        >
          {{ unreadCount > 99 ? '99+' : unreadCount }}
        </span>
      </button>
    </div>

    <ChatPanel v-if="chatOpen" @close="closeChat" />
    <EventCreateModal v-if="eventModalOpen" @close="eventModalOpen = false" />
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import ChatPanel from './ChatPanel.vue'
import EventCreateModal from './EventCreateModal.vue'
import { usePortalChat } from '@/composables/portal/usePortalChat'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { CalendarPlus, Dices, MessageSquare, Plus, Star } from 'lucide-vue-next'

defineEmits(['open-surprise'])

const { unreadCount, markRead } = usePortalChat()
const { profile } = usePortalAuth()

const open = ref(false)
const chatOpen = ref(false)
const eventModalOpen = ref(false)
const fabRef = ref(null)
const chatAllowed = computed(() => profile.value?.chat_enabled !== false)

function onChat() {
  if (!chatAllowed.value) return
  chatOpen.value = !chatOpen.value
  if (chatOpen.value) markRead()
  open.value = false
}
function closeChat() {
  chatOpen.value = false
}

// Close the FAB menu when clicking anywhere outside the cluster.
function onClickOutside(e) {
  if (open.value && fabRef.value && !fabRef.value.contains(e.target)) {
    open.value = false
  }
}
onMounted(() => document.addEventListener('click', onClickOutside, true))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside, true))
</script>

<style scoped>
.pt-fab {
  position: fixed;
  right: 14px;
  bottom: calc(14px + 72px + env(safe-area-inset-bottom, 0px));
  z-index: 9997;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
@media (min-width: 768px) {
  .pt-fab {
    right: 24px;
    bottom: 24px;
  }
}

/* Sub-buttons column (above the main button) */
.pt-fab-sub {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* ─── Main toggle button ─── */
.pt-fab-main {
  width: 52px;
  height: 52px;
  border-radius: var(--portal-radius-circle);
  border: 1px solid var(--portal-border-intense);
  background: rgb(67, 56, 202, 0.9);
  backdrop-filter: var(--portal-blur-md);
  -webkit-backdrop-filter: var(--portal-blur-md);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow:
    0 8px 28px rgb(67, 56, 202, 0.45),
    0 4px 12px rgb(0, 0, 0, 0.3);
  transition:
    transform var(--portal-dur-med) ease,
    background var(--portal-dur-med) ease,
    box-shadow var(--portal-dur-med) ease;
  flex-shrink: 0;
}
.pt-fab-main svg {
  transition: transform var(--portal-dur-med) ease;
}
.pt-fab-main--open svg {
  transform: rotate(45deg);
}
.pt-fab-main:hover {
  background: rgb(79, 70, 229, 0.95);
  transform: scale(1.06);
}
@media (min-width: 640px) {
  .pt-fab-main {
    width: 56px;
    height: 56px;
  }
}

/* ─── Sub-buttons ─── */
.pt-fab-btn {
  width: 44px;
  height: 44px;
  border-radius: var(--portal-radius-circle);
  border: 1px solid var(--portal-border-strong);
  background: rgb(20, 20, 30, 0.82);
  backdrop-filter: var(--portal-blur-md);
  -webkit-backdrop-filter: var(--portal-blur-md);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 6px 20px rgb(0, 0, 0, 0.45);
  transition:
    transform var(--portal-dur-fast),
    background var(--portal-dur-fast),
    opacity var(--portal-dur-base);
  position: relative;
}
.pt-fab-btn:hover:not(:disabled) {
  background: rgb(67, 56, 202, 0.85);
  transform: translateY(-2px);
}
.pt-fab-btn--disabled {
  opacity: 0.35;
  cursor: not-allowed;
  color: rgb(255, 255, 255, 0.45);
}
@media (min-width: 640px) {
  .pt-fab-btn {
    width: 48px;
    height: 48px;
  }
}

/* Badge (unread chat count) */
.pt-fab-main {
  position: relative;
}
.pt-fab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: var(--portal-color-error);
  color: #fff;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgb(20, 20, 30, 0.9);
  box-shadow: 0 0 10px rgb(var(--portal-color-error-rgb), 0.5);
}
/* Slightly bigger ring on the main "+" so the badge stays legible
   against the indigo background. */
.pt-fab-badge--main {
  top: -6px;
  right: -6px;
  border-color: var(--bg-primary, rgb(20, 20, 30, 0.9));
}

/* ─── Pop transition: sub-buttons scale + fade in from below ─── */
.pt-fab-pop-enter-active {
  transition:
    opacity var(--portal-dur-base) ease,
    transform var(--portal-dur-med) cubic-bezier(0.34, 1.56, 0.64, 1);
}
.pt-fab-pop-leave-active {
  transition:
    opacity var(--portal-dur-fast) ease,
    transform var(--portal-dur-fast) ease;
}
.pt-fab-pop-enter-from {
  opacity: 0;
  transform: scale(0.3) translateY(20px);
}
.pt-fab-pop-leave-to {
  opacity: 0;
  transform: scale(0.5) translateY(10px);
}
</style>
