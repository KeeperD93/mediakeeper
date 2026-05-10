/**
 * Vitest coverage for episode audio-language tags in the watchlist card.
 *
 * The Suivi/Manquants UI surfaces 2-letter codes (``EN``, ``FR``…) next
 * to every episode marked ``present`` so the user can tell at a glance
 * which dubs Emby has on disk. Missing/upcoming episodes never show
 * tags; an absent or empty ``audio_languages`` field renders nothing.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('lucide-vue-next', () => ({
  Ban: { name: 'BanStub', template: '<i />' },
  Check: { name: 'CheckStub', template: '<i />' },
  ChevronDown: { name: 'ChevronDownStub', template: '<i />' },
  Copy: { name: 'CopyStub', template: '<i />' },
}))

import WlSeriesCard from '@/components/watchlist/WlSeriesCard.vue'

function buildSeries(audioLanguages, status = 'present') {
  return {
    tmdb_id: 42,
    name: 'Test Show',
    year: '2024',
    total_seasons: 1,
    seasons: [
      {
        season: 1,
        episode_count_emby: 1,
        episode_count_tmdb: 1,
        all_present: status === 'present',
        episodes: [
          {
            episode: 1,
            name: 'Pilot',
            air_date: '2024-01-01',
            status,
            ...(audioLanguages !== undefined && { audio_languages: audioLanguages }),
          },
        ],
      },
    ],
    _fm: status === 'missing' ? 1 : 0,
  }
}

function mountCard(series) {
  return mount(WlSeriesCard, {
    props: { series, ignoredSet: new Set() },
    global: {
      mocks: { $t: key => key },
    },
  })
}

async function expandFirstSeason(wrapper) {
  // Open the card and the season so the episode rows render.
  await wrapper.find('.wlsc-head').trigger('click')
  await wrapper.find('.wlsc-season-head').trigger('click')
}

describe('WlSeriesCard audio-language tags', () => {
  it('renders one tag per language for a present episode', async () => {
    const w = mountCard(buildSeries(['FR', 'EN']))
    await expandFirstSeason(w)

    const tags = w.findAll('.wlsc-ep-lang')
    expect(tags).toHaveLength(2)
    expect(tags.map(t => t.text())).toEqual(['FR', 'EN'])
  })

  it('renders no tag span when audio_languages is absent', async () => {
    const w = mountCard(buildSeries(undefined))
    await expandFirstSeason(w)

    expect(w.find('.wlsc-ep-langs').exists()).toBe(false)
    expect(w.findAll('.wlsc-ep-lang')).toHaveLength(0)
  })

  it('renders no tag span when audio_languages is an empty array', async () => {
    const w = mountCard(buildSeries([]))
    await expandFirstSeason(w)

    expect(w.find('.wlsc-ep-langs').exists()).toBe(false)
  })

  it('does not render tags on missing episodes even if audio_languages is present', async () => {
    // Defensive: backend should never set audio_languages on a missing
    // episode, but the component must not leak the data through.
    const w = mountCard(buildSeries(['FR'], 'missing'))
    await expandFirstSeason(w)

    expect(w.find('.wlsc-ep-langs').exists()).toBe(false)
  })

  it('exposes the language_available i18n key as the tag tooltip', async () => {
    const w = mountCard(buildSeries(['JP']))
    await expandFirstSeason(w)

    const tag = w.find('.wlsc-ep-lang')
    expect(tag.attributes('title')).toBe('watchlist.language_available')
  })
})
