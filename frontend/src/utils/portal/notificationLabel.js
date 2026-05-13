import { Bell, Film, Flag, MessageSquare, Target, TicketCheck } from 'lucide-vue-next'
import { NOTIF_TYPE } from '@/constants/notifications'

/**
 * Lucide component used to prefix a notification row in the bell popup.
 * Falls back to the generic Bell glyph when the type is unknown so the
 * UI never renders an empty slot.
 */
export function iconComponentForNotification(type) {
  if (!type) return Bell
  if (type === NOTIF_TYPE.CHAT_MESSAGE_REPORTED) return Flag
  if (type.startsWith('event_')) return Film
  if (type.startsWith('request_')) return Target
  if (type.startsWith('ticket_')) return TicketCheck
  if (type.startsWith('chat_')) return MessageSquare
  return Bell
}

/**
 * Translate a notification into the short human-readable label shown
 * in the bell popup. Uses the caller's `t` function so we keep full
 * control of the i18n locale and avoid re-instantiating a composable
 * in a pure helper. Falls back to the raw `type` string for unknown
 * events — that way a new server-side type never renders blank while
 * we wait for the matching translation key to ship.
 */
export function labelForNotification(n, t) {
  const p = n.payload || {}
  switch (n.type) {
    case 'event_invitation':
      return t('portal.notifications.tpl.invitation', { from: p.from || '?', title: p.title || '' })
    case 'event_accepted':
      return t('portal.notifications.tpl.accepted', { from: p.from || '?', title: p.title || '' })
    case 'event_declined':
      return t('portal.notifications.tpl.declined', { from: p.from || '?', title: p.title || '' })
    case 'event_modified':
      return t('portal.notifications.tpl.modified', { title: p.title || '' })
    case 'event_cancelled':
      return t('portal.notifications.tpl.cancelled', { title: p.title || '' })
    case 'event_removed':
      return t('portal.notifications.tpl.removed', { title: p.title || '' })
    case NOTIF_TYPE.EVENT_ROOM_OPEN:
      return t('portal.notifications.tpl.roomOpen', { title: p.title || '' })
    case 'event_reminder':
      return t('portal.notifications.tpl.reminder', { title: p.title || '' })
    case NOTIF_TYPE.REQUEST_APPROVED:
      return t('portal.notifications.tpl.requestApproved', { title: p.title || '' })
    case NOTIF_TYPE.REQUEST_AVAILABLE:
      return t('portal.notifications.tpl.requestAvailable', { title: p.title || '' })
    case NOTIF_TYPE.TICKET_CREATED:
      return t('portal.notifications.tpl.ticketCreated', { title: p.title || '' })
    case NOTIF_TYPE.TICKET_REPLIED:
      return t('portal.notifications.tpl.ticketReplied', { title: p.title || '' })
    case NOTIF_TYPE.TICKET_RESOLVED:
      return t('portal.notifications.tpl.ticketResolved', { title: p.title || '' })
    case NOTIF_TYPE.CHAT_MESSAGE_REPORTED:
      return t('portal.notifications.tpl.chatMessageReported', {
        from: p.reporter_name || '?',
        excerpt: p.excerpt || '',
      })
    default:
      return n.type
  }
}

/**
 * Relative time helper — "now", "5 min", "2 h", then the localised date.
 * Receives `t` the same way as `labelForNotification` so both callers
 * share one i18n pipeline.
 */
export function timeAgoForNotification(iso, t) {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return t('portal.notifications.now')
  if (diff < 3600) return `${Math.floor(diff / 60)} min`
  if (diff < 86400) return `${Math.floor(diff / 3600)} h`
  return d.toLocaleDateString()
}
