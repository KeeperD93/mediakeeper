import { afterEach, describe, expect, it } from 'vitest'
import { rootZoom } from '@/utils/zoom'

// rootZoom() is consumed by ~18 JS-positioned admin sites; these pin its two
// branches (Element.currentCSSZoom vs the width-ratio fallback) and, above all,
// the no-op-when-unzoomed contract every consumer silently relies on.

const root = document.documentElement
const realInnerWidth = window.innerWidth

function stub(target, prop, value) {
  Object.defineProperty(target, prop, { value, configurable: true })
}

describe('rootZoom', () => {
  afterEach(() => {
    delete root.currentCSSZoom
    delete root.clientWidth // restores the prototype getter
    stub(window, 'innerWidth', realInnerWidth)
  })

  it('uses Element.currentCSSZoom when present and > 0', () => {
    stub(root, 'currentCSSZoom', 0.9)
    expect(rootZoom()).toBe(0.9)
  })

  it('treats currentCSSZoom === 1 as no zoom', () => {
    stub(root, 'currentCSSZoom', 1)
    expect(rootZoom()).toBe(1)
  })

  it('falls back to the innerWidth/clientWidth ratio when currentCSSZoom is absent', () => {
    stub(root, 'clientWidth', 1000)
    stub(window, 'innerWidth', 900)
    expect(rootZoom()).toBeCloseTo(0.9, 5)
  })

  it('reads 1 from the fallback when document width equals the viewport (no zoom)', () => {
    stub(root, 'clientWidth', 1024)
    stub(window, 'innerWidth', 1024)
    expect(rootZoom()).toBe(1)
  })

  it('ignores a non-positive currentCSSZoom and falls back', () => {
    stub(root, 'currentCSSZoom', 0)
    stub(root, 'clientWidth', 1024)
    stub(window, 'innerWidth', 1024)
    expect(rootZoom()).toBe(1)
  })

  it('returns 1 (no-op) when clientWidth is 0 — the jsdom default that keeps every /z identity in unit tests', () => {
    stub(root, 'clientWidth', 0)
    expect(rootZoom()).toBe(1)
  })
})
