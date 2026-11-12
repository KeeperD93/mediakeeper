import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsTabAppearance from '@/components/portal/settings/SettingsTabAppearance.vue'

const TEXTS = {
  'test.title.night': 'Night Shift',
  'test.title.snow': 'Snow Keeper',
  'test.title.film': 'Film Lover',
  'test.ach.moon': 'Moonlight Watcher',
  'test.ach.snow': 'First Snow',
  'test.ach.snow_desc': 'Watch a film on a snowy day',
  'test.ach.film': 'Film Buff',
  'test.ach.film_desc': 'Watch ten films',
}
const translate = key => TEXTS[key] ?? key

// Shapes sent by the server: no description for a secret not yet unlocked.
const CATALOGUE = [
  {
    title_key: 'test.title.night',
    achievement_name_key: 'test.ach.moon',
    achievement_description_key: null,
    secret: true,
    unlocked: false,
  },
  {
    title_key: 'test.title.snow',
    achievement_name_key: 'test.ach.snow',
    achievement_description_key: 'test.ach.snow_desc',
    secret: true,
    unlocked: true,
  },
  {
    title_key: 'test.title.film',
    achievement_name_key: 'test.ach.film',
    achievement_description_key: 'test.ach.film_desc',
    secret: false,
    unlocked: false,
  },
]

async function openRows() {
  const w = mount(SettingsTabAppearance, {
    props: { form: {}, titleCatalogue: CATALOGUE },
    global: { mocks: { $t: translate } },
  })
  await w.find('.pt-settings-btn').trigger('click')
  return w.findAll('.pt-settings-howto-row')
}

describe('SettingsTabAppearance — how to unlock each title', () => {
  it('names the trophy of a secret not yet unlocked, without any description', async () => {
    const row = (await openRows())[0]
    expect(row.text()).toContain('Moonlight Watcher')
    expect(row.text()).not.toContain('???')
    expect(row.find('em').exists()).toBe(false)
  })

  it('names and describes the trophy of an unlocked secret', async () => {
    const row = (await openRows())[1]
    expect(row.text()).toContain('First Snow')
    expect(row.find('em').text()).toContain('Watch a film on a snowy day')
  })

  it('keeps the name and description of an ordinary trophy', async () => {
    const row = (await openRows())[2]
    expect(row.text()).toContain('Film Buff')
    expect(row.find('em').text()).toContain('Watch ten films')
  })
})
