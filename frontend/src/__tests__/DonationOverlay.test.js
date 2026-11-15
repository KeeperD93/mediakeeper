/**
 * DonationOverlay conditional rendering:
 * - admin sees the MediaKeeper section (Ko-fi + star), sponsor hidden while blank
 * - the operator section shows for anyone when enabled with a safe link
 * - an unsafe operator URL drops the operator section (safeHref guard)
 * - the operator message is scrubbed before rendering; scrubbed to nothing, the intro shows
 * - close button emits close
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import DonationOverlay from '@/components/common/DonationOverlay.vue'

const iconStub = { template: '<i />' }
const STUBS = { Coffee: iconStub, Github: iconStub, Heart: iconStub, Star: iconStub, X: iconStub }

function build(props = {}) {
  return mount(DonationOverlay, {
    props: { open: true, isAdmin: false, donation: null, ...props },
    global: { stubs: STUBS },
    attachTo: document.body,
  })
}

describe('DonationOverlay', () => {
  it('shows the MediaKeeper section for admins and hides the blank sponsor row', () => {
    const w = build({ isAdmin: true })
    expect(w.html()).toContain('ko-fi.com/keeperd93')
    expect(w.html()).toContain('github.com/keeperd93/mediakeeper')
    // Sponsor URL is empty by default -> its row must not render.
    expect(w.text()).not.toContain('donation.sponsor')
    expect(w.find('.dn-section--instance').exists()).toBe(false)
    w.unmount()
  })

  it('shows both the MediaKeeper and server sections for an admin when configured', () => {
    const w = build({
      isAdmin: true,
      donation: { enabled: true, url: 'https://example.org/give', message: '' },
    })
    expect(w.html()).toContain('ko-fi.com/keeperd93')
    expect(w.find('.dn-section--instance').exists()).toBe(true)
    w.unmount()
  })

  it('shows only the operator section for a non-admin when enabled', () => {
    const w = build({
      isAdmin: false,
      donation: { enabled: true, url: 'https://example.org/give', message: 'Help me' },
    })
    expect(w.html()).not.toContain('ko-fi.com')
    const cta = w.get('.dn-section--instance a.dn-cta--primary')
    expect(cta.attributes('href')).toBe('https://example.org/give')
    expect(w.text()).toContain('Help me')
    w.unmount()
  })

  it('scrubs the operator message before rendering it', () => {
    const w = build({
      donation: {
        enabled: true,
        url: 'https://example.org/give',
        message:
          '<p>Help <strong>me</strong></p><img src="x" onerror="alert(1)"><script>alert(1)</script>',
      },
    })
    const quote = w.get('.dn-quote').html()
    expect(quote).toContain('<p>Help <strong>me</strong></p>')
    expect(quote).not.toContain('onerror')
    expect(quote).not.toContain('<script')
    w.unmount()
  })

  it('shows the default intro when the message scrubs to nothing', () => {
    const w = build({
      donation: {
        enabled: true,
        url: 'https://example.org/give',
        message: '<script>alert(1)</script>',
      },
    })
    expect(w.get('.dn-quote').text()).toBe('donation.instanceIntro')
    w.unmount()
  })

  it('drops the operator section when the link is unsafe', () => {
    const w = build({ donation: { enabled: true, url: 'javascript:alert(1)', message: '' } })
    expect(w.find('.dn-section--instance').exists()).toBe(false)
    w.unmount()
  })

  it('emits close when the close button is clicked', async () => {
    const w = build({ isAdmin: true })
    await w.get('.dn-close').trigger('click')
    expect(w.emitted('close')).toBeTruthy()
    w.unmount()
  })
})
