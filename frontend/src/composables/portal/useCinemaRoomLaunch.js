import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { isTv as isTvMedia } from '@/constants/media'
import { TOAST_TYPE } from '@/constants/toast'
import { safeHref } from '@/utils/safeUrl'

// 2 s leaves Emby long enough to register a PlaybackSession before we
// re-poll, so the launching viewer sees their own bar grow without
// waiting for the next 3 s tick.
const LAUNCH_POLL_KICK_MS = 2_000

/**
 * Cinema room — launch CTA. Owns the floating "Launch / next film"
 * button: its label, enabled state, the click that opens the viewer's
 * current film in Emby, the per-user "advance-self" step, and the
 * centring of the CTA over the virtual screen.
 *
 * Per-user marathon state lives on the viewer's invitation row, so this
 * composable derives myUserId / myUserStep / currentMedia from the
 * shared event ref and exposes them for the template too.
 *
 * Inputs (reactive, owned by the view): event (mutated on advance-self),
 * profile, flow (resetAcademy), marathonProgress (bump), advanceSelf
 * (useRooms), checkAvailability/getAvailability (useAvailability),
 * t/showToast.
 */
export function useCinemaRoomLaunch({
  event,
  profile,
  flow,
  marathonProgress,
  advanceSelf,
  checkAvailability,
  getAvailability,
  t,
  showToast,
}) {
  const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)

  // Per-user marathon step lives on ``MKEventInvitation`` so latecomers
  // and viewers who fall behind keep watching their own film while peers
  // advance. Falls back to 0 until the current viewer has been seated.
  const myUserStep = computed(() => {
    const me = event.value?.invitations?.find(i => i.user_id === myUserId.value)
    return typeof me?.user_step === 'number' ? me.user_step : 0
  })

  const currentMedia = computed(() => event.value?.tmdb_ids?.[myUserStep.value] || null)

  const canAdvanceSelf = computed(() => {
    if (!event.value) return false
    const total = event.value.tmdb_ids?.length || 0
    return total > 1 && myUserStep.value < total - 1
  })

  const launchLabel = computed(() => {
    if (!currentMedia.value) return ''
    return isTvMedia(currentMedia.value)
      ? t('portal.cinema.launchSeries')
      : t('portal.cinema.launchMovie')
  })

  // The launch CTA centres on the *virtual screen*, which is not the viewport
  // centre (seats sit below it) and must stay above the side chat — so it lives
  // at the root layer, positioned from the screen frame's measured box.
  const screenFrameEl = ref(null)
  const launchPos = ref({ top: '50%', left: '50%' })
  function syncLaunchPos() {
    const r = screenFrameEl.value?.getBoundingClientRect()
    if (r) launchPos.value = { top: `${r.top + r.height / 2}px`, left: `${r.left + r.width / 2}px` }
  }

  function resolveLaunchUrl(media) {
    if (!media?.tmdb_id) return null
    const info = getAvailability(media.tmdb_id)
    return info?.emby_url || null
  }

  async function onLaunchClick() {
    // The launch button opens the *viewer's* current film (per-user
    // marathon step). The marathon-wide ``/advance`` POST is gone from
    // this path; ``/advance-self`` now bumps just our own step so peers
    // can stay where they are while we move forward.
    if (!event.value || !currentMedia.value) return
    let url = resolveLaunchUrl(currentMedia.value)
    if (!url) {
      // Cold cache, or the 60 s availability TTL lapsed while the viewer
      // waited for showtime: resolve on demand so the click reliably opens
      // Emby. The sub-second resolve keeps window.open inside the click's
      // transient activation, so it is not popup-blocked.
      await Promise.resolve(checkAvailability([currentMedia.value])).catch(() => {})
      url = resolveLaunchUrl(currentMedia.value)
    }
    url = safeHref(url)
    if (url) {
      window.open(url, '_blank', 'noopener')
      // Force a fresh progress fetch so the playback panel surfaces the
      // viewer's session as soon as Emby reports it instead of waiting
      // for the next regular tick.
      setTimeout(() => marathonProgress.bump(), LAUNCH_POLL_KICK_MS)
      return
    }
    // The film is always in Emby (only Emby-available titles can be picked
    // at event creation), so an unresolved url means the availability index
    // is momentarily behind — ask the viewer to retry instead of routing
    // them away to the portal detail page.
    showToast(t('portal.cinema.errors.launch_unavailable'), TOAST_TYPE.WARN)
  }

  async function onAdvanceSelfClick() {
    // Per-user advance: bumps ``user_step`` on the viewer's invitation
    // and re-syncs the event-wide ``current_step`` to ``max(user_step)``.
    // The seat row's "En retard" tag flips off for this viewer; peers
    // unaffected. Used for the next-film CTA that follows the launch.
    if (!event.value) return
    const res = await advanceSelf(event.value.id).catch(() => null)
    if (!res || res.error) return
    if (event.value?.invitations) {
      event.value.invitations = event.value.invitations.map(inv =>
        inv.user_id === myUserId.value ? { ...inv, user_step: res.user_step } : inv,
      )
      event.value = { ...event.value, current_step: res.current_step }
    }
    flow.resetAcademy()
  }

  // Re-centre the launch CTA once the room + seats have rendered, and on
  // every viewport resize.
  watch(event, async v => {
    if (!v) return
    await nextTick()
    syncLaunchPos()
  })

  onMounted(() => window.addEventListener('resize', syncLaunchPos))
  onBeforeUnmount(() => window.removeEventListener('resize', syncLaunchPos))

  return {
    screenFrameEl,
    launchPos,
    currentMedia,
    myUserStep,
    launchLabel,
    canAdvanceSelf,
    onLaunchClick,
    onAdvanceSelfClick,
  }
}
