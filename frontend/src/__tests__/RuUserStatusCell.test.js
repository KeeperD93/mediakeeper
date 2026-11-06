/**
 * The status of an account in the users list: active, never activated (it still earns
 * XP and trophies) or deactivated (it no longer does).
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import RuUserStatusCell from '@/components/portal/admin/users/RuUserStatusCell.vue'

function statusOf(user) {
  return mount(RuUserStatusCell, { props: { user } }).get('.ru-status-text').text()
}

describe('RuUserStatusCell', () => {
  it('shows an active account', () => {
    expect(statusOf({ account_active: true, deactivated: false })).toBe(
      'requestsAdmin.users.labels.active',
    )
  })

  it('tells an account never activated from a deactivated one', () => {
    expect(statusOf({ account_active: false, deactivated: false })).toBe(
      'requestsAdmin.users.labels.neverActivated',
    )
    expect(statusOf({ account_active: false, deactivated: true })).toBe(
      'requestsAdmin.users.labels.deactivated',
    )
  })
})
