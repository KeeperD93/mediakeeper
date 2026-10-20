import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return { ...actual, useI18n: () => ({ t: key => key, locale: ref('fr') }) }
})

import DetailHero from '@/components/portal/detail/DetailHero.vue'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'
import { REQUEST_STATUS } from '@/constants/requests'

function mountHero(props) {
  return mount(DetailHero, {
    props: { media: { title: 'Show', media_type: 'tv' }, ...props },
    global: { stubs: { PremiumRibbon: true } },
  })
}

const REQUEST_LABELS = ['portal.detail.request', 'portal.detail.reRequest']

function requestButton(w) {
  return w.findAll('button').find(b => REQUEST_LABELS.includes(b.text()))
}

describe('DetailHero request button', () => {
  it('is hidden when the page says the title cannot be requested', () => {
    expect(
      requestButton(mountHero({ showRequestBtn: false, reqStatus: 'pending' })),
    ).toBeUndefined()
  })

  it('shows Request for a served series that still misses episodes', () => {
    const btn = requestButton(mountHero({ showRequestBtn: true, reqStatus: 'available' }))
    expect(btn.text()).toBe('portal.detail.request')
  })

  it('reads Request again after a rejection', () => {
    const btn = requestButton(mountHero({ showRequestBtn: true, reqStatus: 'rejected' }))
    expect(btn.text()).toBe('portal.detail.reRequest')
  })

  it('emits request on click', async () => {
    const w = mountHero({ showRequestBtn: true })
    await requestButton(w).trigger('click')
    expect(w.emitted('request')).toHaveLength(1)
  })

  it('disables the button and shows why when the request is blocked, whatever the status', () => {
    const w = mountHero({
      showRequestBtn: true,
      reqStatus: 'rejected',
      requestBlockedReason: 'Blocked',
    })

    expect(requestButton(w).attributes('disabled')).toBeDefined()
    expect(w.find('.dh-request-blocked').text()).toBe('Blocked')
  })
})

describe('DetailHero status ribbon', () => {
  // The ribbon sits on the poster: give the title one.
  const withPoster = props =>
    mountHero({ media: { title: 'Show', media_type: 'tv', poster: '/poster.jpg' }, ...props })
  const ribbon = w => w.findComponent(PremiumRibbon)

  it("shows a refused request with the poster cards' colour and label", () => {
    const w = withPoster({
      reqStatus: REQUEST_STATUS.REJECTED,
      reqStatusTooltip: 'Refused on day one',
    })

    expect(ribbon(w).props()).toMatchObject({
      label: 'PORTAL.POSTERCARD.STATUSREJECTED',
      bg: 'var(--portal-color-error)',
      title: 'Refused on day one',
    })
  })

  it('shows no ribbon once the title is available, nor without a request', () => {
    expect(ribbon(withPoster({ reqStatus: REQUEST_STATUS.AVAILABLE })).exists()).toBe(false)
    expect(ribbon(withPoster({})).exists()).toBe(false)
  })
})
