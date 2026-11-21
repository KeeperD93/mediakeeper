/**
 * First-login wizard, its texts: one typography in the whole window. French keeps
 * « ? ! : ; » and guillemets with their words (no-break space); English writes straight
 * quotes and apostrophes, as the rest of the portal.
 */
import { describe, expect, it } from 'vitest'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'

const BLOCKS = ['wizard', 'wizardHelp']
const ch = String.fromCharCode
const PLAIN_SPACE_IN_FRENCH = new RegExp(` [?!:;${ch(0xbb)}]|${ch(0xab)} `)
const CURLY = new RegExp(`[${ch(0x2018)}${ch(0x2019)}${ch(0x201c)}${ch(0x201d)}]`)

/** Every text of a block, with its path. */
function* texts(node, path) {
  if (typeof node === 'string') yield [path, node]
  else for (const [key, value] of Object.entries(node)) yield* texts(value, `${path}.${key}`)
}

const offending = (messages, pattern) =>
  BLOCKS.flatMap(block => [...texts(messages.portal[block], block)])
    .filter(([, text]) => pattern.test(text))
    .map(([path]) => path)

describe('PortalOnboardingWizard, typography', () => {
  it('keeps French punctuation and guillemets with their words', () => {
    expect(offending(fr, PLAIN_SPACE_IN_FRENCH)).toEqual([])
  })

  it('writes straight quotes and apostrophes in English', () => {
    expect(offending(en, CURLY)).toEqual([])
  })
})
