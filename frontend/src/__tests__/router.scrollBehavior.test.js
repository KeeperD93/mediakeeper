/**
 * Router scroll: a link to an anchor of the page glides to it, or jumps there when
 * the device asks for reduced motion; any other page opens at its top at once.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({}) }))
vi.mock('@/composables/useApi', () => ({ fetchApiResponse: vi.fn() }))

import router from '@/router'

const scrollFor = (to, saved = null) => router.options.scrollBehavior(to, {}, saved)

function stubReducedMotion(matches) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches })),
  )
}

describe('router — scrollBehavior', () => {
  beforeEach(() => {
    const anchor = document.createElement('section')
    anchor.id = 'faq'
    document.body.append(anchor)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.replaceChildren()
  })

  it('glides to an anchor of the page', () => {
    stubReducedMotion(false)
    expect(scrollFor({ hash: '#faq' })).toEqual({ el: '#faq', behavior: 'smooth' })
  })

  it('jumps to it under reduced motion', () => {
    stubReducedMotion(true)
    expect(scrollFor({ hash: '#faq' })).toEqual({ el: '#faq', behavior: 'auto' })
  })

  it('leaves the other cases as they were', () => {
    stubReducedMotion(false)
    expect(scrollFor({ hash: '#identity' })).toBe(false)
    expect(scrollFor({ hash: '' })).toEqual({ top: 0, behavior: 'instant' })
    expect(scrollFor({ hash: '#faq' }, { left: 0, top: 120 })).toEqual({ left: 0, top: 120 })
  })
})
