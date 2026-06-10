import { describe, it, expect } from 'vitest'
import { watchedPct } from '@/components/stats/statsTableUtils'

describe('watchedPct', () => {
  it('computes the real watched percentage (no threshold snap)', () => {
    expect(watchedPct(740, 1000)).toBe(74)
    expect(watchedPct(250, 1000)).toBe(25)
    expect(watchedPct(960, 1000)).toBe(96)
  })

  it('clamps an overshoot (position past runtime) to 100%', () => {
    expect(watchedPct(1200, 1000)).toBe(100)
  })

  it('returns null when the runtime is unknown (legacy/imported rows)', () => {
    expect(watchedPct(300, 0)).toBeNull()
    expect(watchedPct(300, null)).toBeNull()
    expect(watchedPct(300, undefined)).toBeNull()
  })
})
