import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'

function flattenKeys(value, prefix = '', out = new Set()) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    if (prefix) out.add(prefix)
    return out
  }

  const entries = Object.entries(value)
  if (!entries.length && prefix) out.add(prefix)

  for (const [key, nested] of entries) {
    const nextPrefix = prefix ? `${prefix}.${key}` : key
    flattenKeys(nested, nextPrefix, out)
  }

  return out
}

async function main() {
  const root = process.cwd()
  const routerPath = path.join(root, 'src', 'router', 'index.js')
  const localesPath = path.join(root, 'src', 'locales')
  const frPath = path.join(localesPath, 'fr.json')

  const localeFiles = (await readdir(localesPath))
    .filter((file) => file.endsWith('.json'))
    .sort()

  const [routerSource, frSource] = await Promise.all([
    readFile(routerPath, 'utf8'),
    readFile(frPath, 'utf8'),
  ])

  const routeNames = routerSource
    .split(/\r?\n/)
    .flatMap((line, index, lines) => {
      const match = line.match(/name:\s*['"]([^'"]+)['"]/)
      if (!match) return []
      const recentLines = lines.slice(Math.max(0, index - 6), index).join('\n')
      if (!/path:\s*['"]/.test(recentLines)) return []
      if (/redirect:/.test(recentLines)) return []
      return [match[1]]
    })
  const duplicateNames = [...new Set(routeNames.filter((name, index) => routeNames.indexOf(name) !== index))]
  const routeI18nKeys = [...routerSource.matchAll(/\b(?:titleKey|subtitleKey):\s*['"]([^'"]+)['"]/g)]
    .map((match) => match[1])

  const frKeys = flattenKeys(JSON.parse(frSource))
  const missingRouteKeysInFr = routeI18nKeys.filter((key) => !frKeys.has(key))

  const failures = []

  for (const localeFile of localeFiles.filter((file) => file !== 'fr.json')) {
    const source = await readFile(path.join(localesPath, localeFile), 'utf8')
    const keys = flattenKeys(JSON.parse(source))
    const missing = [...frKeys].filter((key) => !keys.has(key))
    const extra = [...keys].filter((key) => !frKeys.has(key))
    const missingRouteKeys = routeI18nKeys.filter((key) => !keys.has(key))

    if (missing.length) {
      failures.push(`Missing ${localeFile} keys: ${missing.join(', ')}`)
    }
    if (extra.length) {
      failures.push(`Extra ${localeFile} keys: ${extra.join(', ')}`)
    }
    if (missingRouteKeys.length) {
      failures.push(`Route i18n keys missing in ${localeFile}: ${missingRouteKeys.join(', ')}`)
    }
  }

  if (duplicateNames.length) {
    failures.push(`Duplicate route names: ${duplicateNames.join(', ')}`)
  }
  if (missingRouteKeysInFr.length) {
    failures.push(`Route i18n keys missing in FR: ${missingRouteKeysInFr.join(', ')}`)
  }

  if (failures.length) {
    for (const failure of failures) {
      console.error(failure)
    }
    process.exit(1)
  }

  console.log('Integrity checks passed.')
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
