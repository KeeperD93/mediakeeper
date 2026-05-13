/**
 * Cinema room — marathon progress panel rendering.
 *
 * Stubs lucide icons so we don't pull SVG noise into the assertions.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MarathonProgressPanel from '@/components/portal/cinema/MarathonProgressPanel.vue'

const STUBS = {
  Film: { template: '<span />' },
  Check: { template: '<span class="stub-check" />' },
}

function build(progress) {
  return mount(MarathonProgressPanel, {
    props: { progress },
    global: { stubs: STUBS },
  })
}

describe('MarathonProgressPanel', () => {
  it('renders nothing when is_marathon is false', () => {
    const w = build({ is_marathon: false, ready: false, participants: [] })
    expect(w.find('.pt-cr-marathon').exists()).toBe(false)
  })

  it('renders nothing when progress is null', () => {
    const w = build(null)
    expect(w.find('.pt-cr-marathon').exists()).toBe(false)
  })

  it('shows a row per participant with the right width on the bar', () => {
    const w = build({
      is_marathon: true,
      current_step: 1,
      total_steps: 3,
      participants: [
        { user_id: 1, display_name: 'Alice', ratio: 0.5, seconds_remaining: 1800, meets_threshold: false },
        { user_id: 2, display_name: 'Bob', ratio: 0.9, seconds_remaining: 360, meets_threshold: true },
      ],
      ineligible_count: 0,
      ready: false,
    })
    expect(w.find('.pt-cr-marathon').exists()).toBe(true)
    const rows = w.findAll('.pt-cr-marathon-row')
    expect(rows).toHaveLength(2)
    const widths = w.findAll('.pt-cr-marathon-bar-fill').map(d => d.attributes('style'))
    expect(widths[0]).toContain('width: 50%')
    expect(widths[1]).toContain('width: 90%')
  })

  it('renders a "done" badge only on participants meeting the threshold', () => {
    const w = build({
      is_marathon: true,
      current_step: 0,
      total_steps: 2,
      participants: [
        { user_id: 1, display_name: 'Watching', ratio: 0.4, seconds_remaining: 1200, meets_threshold: false },
        { user_id: 2, display_name: 'Done', ratio: 0.92, seconds_remaining: 60, meets_threshold: true },
      ],
      ineligible_count: 0,
      ready: false,
    })
    const dones = w.findAll('.pt-cr-marathon-bar-done')
    expect(dones).toHaveLength(1)
  })

  it('renders the ineligible-count notice when ineligible_count > 0', () => {
    const w = build({
      is_marathon: true,
      current_step: 0,
      total_steps: 2,
      participants: [],
      ineligible_count: 2,
      ready: false,
    })
    expect(w.find('.pt-cr-marathon-ineligible').exists()).toBe(true)
  })

  it('hides the ineligible-count notice when ineligible_count is zero', () => {
    const w = build({
      is_marathon: true,
      current_step: 0,
      total_steps: 2,
      participants: [],
      ineligible_count: 0,
      ready: false,
    })
    expect(w.find('.pt-cr-marathon-ineligible').exists()).toBe(false)
  })

  it('formats the remaining time helper: minutes, hours, dash', () => {
    const w = build({
      is_marathon: true,
      current_step: 0,
      total_steps: 2,
      participants: [
        { user_id: 1, display_name: 'M', ratio: 0, seconds_remaining: null, meets_threshold: false },
      ],
      ineligible_count: 0,
      ready: false,
    })
    const exposed = w.vm
    expect(exposed.formatRemaining(null)).toBe('—')
    expect(exposed.formatRemaining(0)).toBe('0 min')
    expect(exposed.formatRemaining(120)).toBe('2 min')
    expect(exposed.formatRemaining(3900)).toBe('1h 05')
    expect(exposed.pct(0.337)).toBe(34)
    expect(exposed.pct(2)).toBe(100)
    expect(exposed.pct(-1)).toBe(0)
  })
})
