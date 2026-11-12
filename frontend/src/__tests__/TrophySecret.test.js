import { describe, it, expect, vi } from 'vitest'
import { markRaw } from 'vue'
import { mount } from '@vue/test-utils'

const TEXTS = {
  'test.ach.moon': 'Moonlight Watcher',
  'test.ach.moon_desc': 'Watch fifty films after midnight',
  'test.title.night': 'Night Shift',
  'test.ach.film': 'Film Buff',
  'test.ach.film_desc': 'Watch ten films',
  'portal.profile.secretDescription': 'Secret trophy',
}
const translate = key => TEXTS[key] ?? key

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: translate, te: key => key in TEXTS }),
}))

// The real module boots the app-wide i18n instance.
vi.mock('@/utils/datetime', () => ({ localizedDate: date => date.toISOString() }))

vi.mock('lucide-vue-next', () => {
  const icon = name => ({ template: `<i data-icon="${name}" />` })
  return {
    HelpCircle: icon('help-circle'),
    Gift: icon('gift'),
    Pin: icon('pin'),
    Crown: icon('crown'),
    Search: icon('search'),
    Sparkles: icon('sparkles'),
  }
})

import TrophyGrid from '@/components/portal/profile/TrophyGrid.vue'
import TrophyOverlay from '@/components/portal/profile/TrophyOverlay.vue'

const ICON_MAP = {
  Moon: markRaw({ template: '<i data-icon="moon" />' }),
  Film: markRaw({ template: '<i data-icon="film" />' }),
}

// Worst case: the row still carries its description, reward and progress.
// The unearned-secret status alone must keep them off screen.
const SECRET = {
  id: 'secret_moon',
  name_key: 'test.ach.moon',
  description_key: 'test.ach.moon_desc',
  icon: 'Moon',
  tier: 4,
  tier_name: 'platinum',
  category: 'secret',
  status: 'secret',
  secret: true,
  rarity: 'epic',
  progress: 30,
  threshold: 50,
  title_reward: 'test.title.night',
  xp_reward: 200,
  stars: 4,
  sort_order: 1,
}

const LOCKED = {
  ...SECRET,
  id: 'film_1',
  name_key: 'test.ach.film',
  description_key: 'test.ach.film_desc',
  icon: 'Film',
  category: 'watching',
  status: 'locked',
  secret: false,
  progress: 0,
  threshold: 10,
  title_reward: null,
  sort_order: 2,
}

const mocks = { $t: translate }

function mountGrid() {
  return mount(TrophyGrid, {
    props: { displayTrophies: [SECRET], iconMap: ICON_MAP },
    global: { mocks },
  })
}

function mountOverlay(trophies = [SECRET]) {
  return mount(TrophyOverlay, {
    props: {
      modelValue: true,
      categoriesWithStats: [],
      filteredTrophies: trophies,
      iconMap: ICON_MAP,
    },
    global: { mocks },
  })
}

describe('TrophyGrid — unearned secret', () => {
  it('shows the real name and a dimmed real icon', () => {
    const card = mountGrid().find('.gc-trophy--secret')
    expect(card.find('.gc-trophy-label').text()).toBe('Moonlight Watcher')
    expect(card.find('[data-icon="moon"]').exists()).toBe(true)
    expect(card.find('[data-icon="help-circle"]').exists()).toBe(false)
    expect(card.find('.gc-trophy-icon-wrap').classes()).toContain('gc-trophy-icon--dim')
  })

  it('shows no progress', () => {
    const card = mountGrid().find('.gc-trophy--secret')
    expect(card.find('.gc-trophy-pbar').exists()).toBe(false)
    expect(card.find('.gc-trophy-ptxt').exists()).toBe(false)
    expect(card.text()).not.toContain('30')
  })
})

describe('TrophyOverlay — unearned secret', () => {
  it('shows the name, the real icon and "Secret trophy" instead of the description', () => {
    const row = mountOverlay().find('.ta-row--secret')
    expect(row.find('.ta-row-name').text()).toBe('Moonlight Watcher')
    expect(row.find('[data-icon="moon"]').exists()).toBe(true)
    expect(row.find('[data-icon="help-circle"]').exists()).toBe(false)
    expect(row.find('.ta-row-icon').classes()).toContain('gc-trophy-icon--dim')
    expect(row.find('.ta-row-desc').text()).toBe('Secret trophy')
    expect(row.text()).not.toContain('midnight')
  })

  it('shows no progress bar nor figures', () => {
    const row = mountOverlay().find('.ta-row--secret')
    expect(row.find('.ta-row-prog').exists()).toBe(false)
    expect(row.text()).not.toContain('30')
  })

  it('finds the secret by its name', async () => {
    const w = mountOverlay([SECRET, LOCKED])
    await w.find('.ta-search-input').setValue('moonlight')
    expect(w.findAll('.ta-row').map(r => r.attributes('data-trophy-id'))).toEqual(['secret_moon'])
  })

  it('does not find the secret by its description, its reward or the placeholder text', async () => {
    const w = mountOverlay([SECRET, LOCKED])
    for (const query of ['midnight', 'night shift', 'secret trophy']) {
      await w.find('.ta-search-input').setValue(query)
      expect(w.find('[data-trophy-id="secret_moon"]').exists()).toBe(false)
    }
  })

  it('still searches the description of an ordinary trophy', async () => {
    const w = mountOverlay([SECRET, LOCKED])
    await w.find('.ta-search-input').setValue('ten films')
    expect(w.findAll('.ta-row').map(r => r.attributes('data-trophy-id'))).toEqual(['film_1'])
  })
})
