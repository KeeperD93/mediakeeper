/**
 * Recent attempts in Settings > Security: "Block IP" is never offered for the
 * marker of unreadable addresses (it would lock out every one of them), stays
 * disabled while an action runs, a neutralised failure says it no longer counts,
 * and a list that never loaded says so.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

import SecurityAttemptsSection from '@/components/settings/security/SecurityAttemptsSection.vue'

const ATTEMPTS = [
  { id: 1, ip: '203.0.113.5', scope: 'portal', success: false },
  { id: 2, ip: 'unknown', scope: 'portal', success: false },
]

function buildSection(props = {}) {
  return mount(SecurityAttemptsSection, {
    props: {
      onlyFailures: true,
      attempts: ATTEMPTS,
      loaded: true,
      failed: false,
      busy: false,
      displayIp: ip => ip,
      formatDate: () => '',
      scopeLabel: scope => scope,
      ...props,
    },
  })
}

const blockButtons = w => w.findAll('tbody tr').map(row => row.find('button').exists())

describe('SecurityAttemptsSection', () => {
  it('offers "Block IP" for a real address only', () => {
    expect(blockButtons(buildSection())).toEqual([true, false])
  })

  it('disables "Block IP" while an action runs', () => {
    const w = buildSection({ busy: true })
    expect(w.get('tbody button').attributes('disabled')).toBeDefined()
  })

  it('keeps a neutralised failure listed and says it no longer counts', () => {
    const w = buildSection({
      attempts: [
        { ...ATTEMPTS[0], cleared_at: '2026-11-01T10:00:00+00:00' },
        { ...ATTEMPTS[0], id: 3, cleared_at: null },
      ],
    })
    const [neutralised, counting] = w.findAll('tbody tr')

    expect(neutralised.text()).toContain('settings.security.failure')
    expect(neutralised.find('.is-cleared').text()).toBe('settings.security.cleared')
    expect(counting.find('.is-cleared').exists()).toBe(false)
  })

  it('says the list is unavailable when its first load failed', () => {
    const w = buildSection({ loaded: false, failed: true })
    expect(w.text()).toContain('settings.security.listUnavailable')
    expect(w.find('table').exists()).toBe(false)
  })
})
