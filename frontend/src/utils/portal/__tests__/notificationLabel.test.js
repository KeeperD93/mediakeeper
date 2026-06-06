import { describe, it, expect } from 'vitest'
import {
  Bell,
  Film,
  Flag,
  ListPlus,
  Megaphone,
  MessageSquare,
  Target,
  TicketCheck,
} from 'lucide-vue-next'
import {
  iconComponentForNotification,
  labelForNotification,
} from '@/utils/portal/notificationLabel'

describe('iconComponentForNotification', () => {
  it('returns Bell for an empty or unknown type', () => {
    expect(iconComponentForNotification(null)).toBe(Bell)
    expect(iconComponentForNotification(undefined)).toBe(Bell)
    expect(iconComponentForNotification('')).toBe(Bell)
    expect(iconComponentForNotification('unknown_topic')).toBe(Bell)
  })

  it('maps each prefixed family to its dedicated Lucide glyph', () => {
    expect(iconComponentForNotification('event_invitation')).toBe(Film)
    expect(iconComponentForNotification('event_room_open')).toBe(Film)
    expect(iconComponentForNotification('request_approved')).toBe(Target)
    expect(iconComponentForNotification('ticket_created')).toBe(TicketCheck)
    expect(iconComponentForNotification('list_copied')).toBe(ListPlus)
    expect(iconComponentForNotification('chat_dm')).toBe(MessageSquare)
  })

  it('flags reported chat messages with the Flag glyph', () => {
    expect(iconComponentForNotification('chat_message_reported')).toBe(Flag)
  })

  it('uses Megaphone for admin broadcasts', () => {
    expect(iconComponentForNotification('admin_message')).toBe(Megaphone)
  })
})

describe('labelForNotification', () => {
  const t = (key, params) => (params ? `${key}|${Object.values(params).join(',')}` : key)

  it('renders admin messages through i18n with the payload title', () => {
    const label = labelForNotification(
      { type: 'admin_message', payload: { title: 'Maintenance' } },
      t,
    )
    expect(label).toBe('portal.notifications.tpl.adminMessage|Maintenance')
  })

  it('renders list notifications through i18n, not the raw type code', () => {
    expect(labelForNotification({ type: 'list_copied' }, t)).toBe(
      'portal.notifications.tpl.listCopied',
    )
    expect(labelForNotification({ type: 'list_contributor_added' }, t)).toBe(
      'portal.notifications.tpl.listContributorAdded',
    )
  })

  it('still falls back to the raw type for a genuinely unknown event', () => {
    expect(labelForNotification({ type: 'totally_unknown' }, t)).toBe('totally_unknown')
  })
})
