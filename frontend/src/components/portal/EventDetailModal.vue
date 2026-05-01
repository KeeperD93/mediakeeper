<template>
  <Teleport to="body">
    <div class="pt-evd-overlay" @click.self="$emit('close')">
      <div v-if="event" class="pt-evd">
        <header class="pt-evd-head">
          <div>
            <span class="pt-evd-kind" :class="`pt-evd-kind--${event.kind}`">
              {{ $t(`portal.mkCalendar.kind.${event.kind}`) }}
            </span>
            <h2 class="pt-evd-title">{{ event.title }}</h2>
          </div>
          <button class="pt-evd-x" :aria-label="$t('common.close')" @click="$emit('close')">
            <X :size="20" :stroke-width="2.5" />
          </button>
        </header>

        <div class="pt-evd-body">
          <div class="pt-evd-meta">
            <div class="pt-evd-meta-item">
              <span class="pt-evd-meta-label">{{ $t('portal.mkEvents.detail.scheduled') }}</span>
              <span>{{ formatFull(event.scheduled_at) }}</span>
            </div>
            <div class="pt-evd-meta-item">
              <span class="pt-evd-meta-label">{{ $t('portal.mkEvents.detail.creator') }}</span>
              <span>{{ event.creator_label }}</span>
            </div>
          </div>

          <h3 class="pt-evd-section-title">
            {{ event.tmdb_ids.length > 1 ? $t('portal.mkEvents.detail.marathonList') : $t('portal.mkEvents.detail.media') }}
          </h3>
          <div class="pt-evd-medias">
            <div v-for="(m, i) in event.tmdb_ids" :key="i" class="pt-evd-media">
              <img v-if="m.poster_url" :src="m.poster_url" :alt="m.title" />
              <div class="pt-evd-media-info">
                <div class="pt-evd-media-title">{{ m.title }}</div>
                <div class="pt-evd-media-type">
                  {{ isTv(m) ? $t('portal.card.series') : $t('portal.card.movie') }}
                </div>
              </div>
            </div>
          </div>

          <p v-if="event.comment" class="pt-evd-comment">{{ event.comment }}</p>

          <h3 class="pt-evd-section-title">{{ $t('portal.mkEvents.detail.invitees') }}</h3>
          <div class="pt-evd-invitees">
            <div
              v-for="inv in event.invitations"
              :key="inv.id"
              class="pt-evd-invitee"
              :class="`pt-evd-invitee--${inv.status}`"
            >
              <span class="pt-evd-invitee-name">{{ inv.username }}</span>
              <span class="pt-evd-invitee-status">{{ $t(`portal.mkEvents.detail.status.${inv.status}`) }}</span>
              <button
                v-if="canManage && inv.user_id !== event.creator_user_id && inv.status === INVITATION_STATUS.ACCEPTED"
                class="pt-evd-invitee-x"
                :title="$t('portal.mkEvents.detail.removeMember')"
                @click="removeMember(inv.user_id)"
              >×</button>
            </div>
          </div>

          <div v-if="conflictWarning" class="pt-evd-warn">
            ⚠️ {{ $t('portal.mkEvents.detail.conflictWarning') }}
          </div>
        </div>

        <footer class="pt-evd-footer">
          <button class="pt-evd-btn pt-evd-btn--ghost" @click="$emit('close')">{{ $t('common.close') }}</button>

          <!-- Enter the cinema room: shown to accepted members from
               T-15 minutes onward, regardless of creator/invitee role. -->
          <button
            v-if="roomOpen && (myStatus === INVITATION_STATUS.ACCEPTED || canManage)"
            class="pt-evd-btn pt-evd-btn--cinema"
            @click="enterRoom"
          >
            🎬 {{ $t('portal.mkEvents.detail.enterRoom') }}
          </button>

          <template v-if="canManage">
            <button class="pt-evd-btn pt-evd-btn--danger" @click="cancelEvent">
              {{ $t('portal.mkEvents.detail.cancel') }}
            </button>
          </template>
          <template v-else>
            <template v-if="myStatus !== INVITATION_STATUS.ACCEPTED">
              <button class="pt-evd-btn pt-evd-btn--ghost" @click="respond('decline')">
                {{ $t('portal.mkEvents.detail.decline') }}
              </button>
              <button class="pt-evd-btn pt-evd-btn--primary" @click="respond('accept')">
                {{ $t('portal.mkEvents.detail.accept') }}
              </button>
            </template>
            <template v-else>
              <button class="pt-evd-btn pt-evd-btn--ghost" @click="respond('decline')">
                {{ $t('portal.mkEvents.detail.unsubscribe') }}
              </button>
            </template>
          </template>
        </footer>
      </div>

      <div v-else class="pt-evd-loading">{{ $t('common.loading') }}</div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from '@/composables/useConfirm'
import { useRouter } from 'vue-router'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useNotifications } from '@/composables/portal/useNotifications'
import { EVENT_STATUS, INVITATION_STATUS } from '@/constants/events'
import { isTv } from '@/constants/media'
import { X } from 'lucide-vue-next'

import '@/assets/styles/portal/event-detail-modal.css'

const router = useRouter()
const { t } = useI18n()
const mkConfirm = useConfirm()

const props = defineProps({
  eventId: { type: Number, required: true },
})
const emit = defineEmits(['close'])

const { getOne, respond: respondSvc, cancel, removeMember: removeMemberSvc } = useRooms()
const { profile } = usePortalAuth()
const { fetchCount } = useNotifications()

const event = ref(null)
const conflictWarning = ref(false)

const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)
const canManage = computed(() => event.value?.creator_user_id === myUserId.value)
const myStatus = computed(() => {
  const inv = event.value?.invitations?.find((i) => i.user_id === myUserId.value)
  return inv?.status || null
})

// Tick every second so the room button appears the moment T-15 hits.
const nowTs = ref(Date.now())
let tickTimer = null
onMounted(() => { tickTimer = setInterval(() => { nowTs.value = Date.now() }, 1000) })
onBeforeUnmount(() => { if (tickTimer) clearInterval(tickTimer) })

// Room is open from 15 minutes BEFORE scheduled time (matches the
// backend ROOM_OPEN_BEFORE_MIN constant in mk_events.py).
const roomOpen = computed(() => {
  if (!event.value || event.value.status !== EVENT_STATUS.SCHEDULED) return false
  const start = new Date(event.value.scheduled_at).getTime()
  const open = start - 15 * 60 * 1000
  return nowTs.value >= open
})

function enterRoom() {
  emit('close')
  // Open the cinema room in a NEW tab so the user can keep their
  // current portal page running in the background.
  const url = router.resolve({ name: 'portal-rooms', params: { id: event.value.id } }).href
  window.open(url, '_blank', 'noopener')
}

async function load() {
  event.value = await getOne(props.eventId)
}

async function respond(decision) {
  const res = await respondSvc(props.eventId, decision)
  if (res?.conflict) conflictWarning.value = true
  await load()
  fetchCount()
}

async function cancelEvent() {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.cancel'),
    message: t('portal.mkEvents.detail.cancelConfirm'),
    variant: 'warn',
  })
  if (!ok) return
  await cancel(props.eventId)
  emit('close')
}

async function removeMember(userId) {
  await removeMemberSvc(props.eventId, userId)
  await load()
}

function formatFull(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

onMounted(load)
</script>
