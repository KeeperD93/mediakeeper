import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const cssPath = resolve(
  __dirname,
  '../assets/styles/app-topbar-dropdowns.css',
)
const css = readFileSync(cssPath, 'utf8')

function ruleBody(selector) {
  const re = new RegExp(`${selector.replace(/\./g, '\\.')}\\s*\\{([^}]+)\\}`)
  const m = css.match(re)
  return m ? m[1] : null
}

describe('notification dropdown text wraps long messages', () => {
  it('drops the ellipsis truncation that hid long messages', () => {
    const body = ruleBody('.tb-notif-text')
    expect(body).not.toBeNull()
    expect(body).not.toMatch(/text-overflow:\s*ellipsis/)
    expect(body).not.toMatch(/white-space:\s*nowrap/)
  })

  it('enables word-break so unbreakable strings still wrap', () => {
    const body = ruleBody('.tb-notif-text')
    expect(body).toMatch(/(overflow-wrap:\s*anywhere|word-break:\s*break-word)/)
  })
})
