import { onBeforeUnmount, watch } from 'vue'

// Slow membership re-pull cadence — well under the 60/min room limit.
const MEMBERSHIP_REFRESH_MS = 15_000

/**
 * Cinema room — seat presence & per-user step sync. Keeps
 * ``event.value.invitations`` in step with peers without a full reload:
 *   - a 15 s membership re-pull that adopts newcomers (the 3 s presence
 *     poll only toggles rows we already know — it cannot introduce a peer
 *     who joined after our initial load),
 *   - a watch merging the marathon-progress poll's presence + per-user
 *     step back into the seat rows.
 *
 * Call ``start()`` once the event is loaded to arm the 15 s timer; the
 * progress watch is live from setup. The timer is cleared on unmount.
 */
export function useCinemaRoomMembership({ event, eventId, getOne, marathonProgress }) {
  let membershipTimer = null

  async function refreshMembership() {
    const fresh = await getOne(eventId).catch(() => null)
    if (!fresh?.invitations || !event.value) return
    const localByUser = new Map(event.value.invitations.map(i => [i.user_id, i]))
    event.value.invitations = fresh.invitations.map(inv => {
      const local = localByUser.get(inv.user_id)
      return local
        ? { ...inv, is_currently_in_room: local.is_currently_in_room, user_step: local.user_step }
        : inv
    })
  }

  // Merge fresh per-user marathon steps + presence flags from the
  // progress poll back into ``event.value.invitations`` so the seats
  // (filtered on ``is_currently_in_room``) and the per-user CTA stay in
  // sync with peers without a full ``getOne`` round trip every 3 s.
  watch(
    () => marathonProgress.progress.value,
    payload => {
      if (!payload || !event.value?.invitations) return
      const stepByUser = new Map(
        (payload.participants || [])
          .filter(p => typeof p.user_id === 'number')
          .map(p => [p.user_id, p.user_step]),
      )
      const presenceByUser = new Map(
        (payload.presence || [])
          .filter(p => typeof p.user_id === 'number')
          .map(p => [p.user_id, Boolean(p.is_currently_in_room)]),
      )
      event.value.invitations = event.value.invitations.map(inv => {
        const next = { ...inv }
        const step = stepByUser.get(inv.user_id)
        if (typeof step === 'number') next.user_step = step
        const presence = presenceByUser.get(inv.user_id)
        if (presence != null) next.is_currently_in_room = presence
        return next
      })
    },
    { deep: true },
  )

  function start() {
    if (!membershipTimer) membershipTimer = setInterval(refreshMembership, MEMBERSHIP_REFRESH_MS)
  }

  onBeforeUnmount(() => {
    if (membershipTimer) {
      clearInterval(membershipTimer)
      membershipTimer = null
    }
  })

  return { start }
}
