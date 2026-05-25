<template>
  <!-- Mobile substitute for ``CinemaRoomSeats``. The desktop 3D plan
       doesn't fit on a phone, so we surface the same data — every
       occupable slot, who's seated, the "En retard" tag — as a flat
       avatar grid. Chat, playback timer, screen + launch CTA keep
       working from the surrounding ``CinemaRoomView`` template. -->
  <section class="pt-crm" aria-label="participants">
    <h3 class="pt-crm-title">{{ $t('portal.cinema.mobile.participants', { count: accepted.length, total: capacity }) }}</h3>
    <ul class="pt-crm-grid">
      <li
        v-for="seatIdx in capacity"
        :key="`m-slot-${seatIdx}`"
        class="pt-crm-slot"
        :class="{
          'pt-crm-slot--occupied': !!seatOccupant(seatIdx - 1),
          'pt-crm-slot--mine': isMine(seatIdx - 1),
        }"
      >
        <template v-if="seatOccupant(seatIdx - 1)">
          <div class="pt-crm-avatar">
            <img
              v-if="seatOccupant(seatIdx - 1).avatar_url"
              :src="seatOccupant(seatIdx - 1).avatar_url"
              :alt="seatOccupant(seatIdx - 1).username || ''"
              class="pt-crm-avatar-img"
            />
            <span v-else class="pt-crm-avatar-initial">
              {{
                seatOccupant(seatIdx - 1)
                  .username?.charAt(0)
                  ?.toUpperCase()
              }}
            </span>
          </div>
          <span class="pt-crm-name">{{ seatOccupant(seatIdx - 1).username }}</span>
          <span
            v-if="isLate(seatOccupant(seatIdx - 1))"
            class="pt-crm-late"
          >
            {{ $t('portal.cinema.marathon.late') }}
          </span>
        </template>
        <span v-else class="pt-crm-empty" aria-hidden="true" />
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { INVITATION_STATUS } from '@/constants/events'

const props = defineProps({
  event: { type: Object, default: null },
})

const { profile } = usePortalAuth()
const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)

const terminated = computed(() => Boolean(props.event?.is_terminated))

const capacity = computed(() => {
  const raw = Number(props.event?.max_participants)
  if (Number.isFinite(raw) && raw > 0) return raw
  return 5
})

const accepted = computed(() =>
  (props.event?.invitations || []).filter(
    i => i.status === INVITATION_STATUS.ACCEPTED && i.seat_index != null,
  ),
)

const groupStep = computed(() => Number(props.event?.current_step ?? 0))

function seatOccupant(seatIdx) {
  if (!props.event || terminated.value) return null
  if (seatIdx < 0 || seatIdx >= capacity.value) return null
  const inv = accepted.value.find(i => i.seat_index === seatIdx)
  if (!inv) return null
  // Same presence gate as the desktop ``CinemaRoomSeats``: only paint
  // the avatar while the heartbeat is fresh; the seat stays reserved
  // in the back-end so a returning viewer reclaims their slot.
  if (!inv.is_currently_in_room) return null
  return inv
}

function isMine(seatIdx) {
  const occ = seatOccupant(seatIdx)
  return !!occ && occ.user_id === myUserId.value
}

function isLate(occ) {
  if (!occ) return false
  if (typeof occ.user_step !== 'number') return false
  return occ.user_step < groupStep.value
}
</script>

<style scoped>
.pt-crm {
  position: relative;
  z-index: 5;
  width: 100%;
  padding: 1rem 0.75rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.pt-crm-title {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  color: var(--portal-text-primary);
  text-align: center;
  margin: 0;
  letter-spacing: 0.02em;
}
.pt-crm-grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
}
.pt-crm-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  min-height: 84px;
  padding: 0.5rem 0.25rem;
  border-radius: var(--portal-radius-md);
  background: rgb(0, 0, 0, 0.32);
  border: 1px solid var(--portal-border-subtle);
}
.pt-crm-slot--occupied {
  background: rgb(0, 0, 0, 0.42);
  border-color: rgb(var(--accent-rgb), 0.35);
}
.pt-crm-slot--mine {
  border-color: var(--portal-color-warning);
  background: rgb(var(--portal-color-warning-rgb), 0.12);
}
.pt-crm-avatar {
  width: 44px;
  height: 44px;
  border-radius: var(--portal-radius-circle);
  background: linear-gradient(135deg, #6366f1 0%, #4338ca 100%);
  border: 2px solid rgb(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}
.pt-crm-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: var(--portal-radius-circle);
}
.pt-crm-avatar-initial {
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-extrabold);
  color: var(--portal-text-primary);
}
.pt-crm-name {
  max-width: 100%;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  color: var(--portal-text-primary);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.1;
}
.pt-crm-late {
  font-size: 9px;
  font-weight: var(--portal-font-bold);
  padding: 1px 5px;
  border-radius: var(--portal-radius-pill);
  background: rgb(var(--portal-color-warning-rgb), 0.22);
  color: var(--portal-color-warning);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pt-crm-empty {
  width: 44px;
  height: 44px;
  border-radius: var(--portal-radius-circle);
  background: var(--portal-surface-2);
  border: 1px dashed rgb(255, 255, 255, 0.15);
}
</style>
