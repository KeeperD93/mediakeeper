import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { pathToFileURL } from 'node:url'

const PLACEHOLDER_RE = /\{[a-zA-Z_][a-zA-Z0-9_]*\}/g

function flatten(value, prefix, out) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    if (prefix) out.set(prefix, value)
    return
  }
  for (const [key, nested] of Object.entries(value)) {
    flatten(nested, prefix ? `${prefix}.${key}` : key, out)
  }
}

export function flattenLocale(obj) {
  const map = new Map()
  flatten(obj, '', map)
  return map
}

export function extractPlaceholders(value) {
  if (typeof value !== 'string') return new Set()
  return new Set(value.match(PLACEHOLDER_RE) ?? [])
}

export function diffSets(a, b) {
  const only = []
  for (const item of a) if (!b.has(item)) only.push(item)
  return only.sort()
}

export function validateLocales({ locales, routeKeys = [], referenceLocale = 'fr' }) {
  const failures = []
  const localeNames = Object.keys(locales)
  if (!localeNames.includes(referenceLocale)) {
    failures.push(`Reference locale "${referenceLocale}" not found among: ${localeNames.join(', ')}`)
    return failures
  }

  const flat = {}
  for (const name of localeNames) {
    flat[name] = flattenLocale(locales[name])
  }

  const refKeys = new Set(flat[referenceLocale].keys())

  for (const name of localeNames) {
    if (name === referenceLocale) continue
    const otherKeys = new Set(flat[name].keys())
    const missing = diffSets(refKeys, otherKeys)
    const extra = diffSets(otherKeys, refKeys)
    if (missing.length) failures.push(`[${name}] missing keys vs ${referenceLocale}: ${missing.join(', ')}`)
    if (extra.length) failures.push(`[${name}] extra keys vs ${referenceLocale}: ${extra.join(', ')}`)
  }

  for (const name of localeNames) {
    for (const [key, value] of flat[name]) {
      if (typeof value !== 'string') {
        failures.push(`[${name}] non-string value at "${key}" (got ${typeof value})`)
        continue
      }
      if (value.trim() === '') {
        failures.push(`[${name}] empty value at "${key}"`)
      }
    }
  }

  for (const name of localeNames) {
    if (name === referenceLocale) continue
    for (const [key, refValue] of flat[referenceLocale]) {
      const otherValue = flat[name].get(key)
      if (otherValue === undefined) continue
      const refPh = extractPlaceholders(refValue)
      const otherPh = extractPlaceholders(otherValue)
      const missing = diffSets(refPh, otherPh)
      const extra = diffSets(otherPh, refPh)
      if (missing.length || extra.length) {
        const parts = []
        if (missing.length) parts.push(`missing ${missing.join(', ')}`)
        if (extra.length) parts.push(`extra ${extra.join(', ')}`)
        failures.push(`[${name}] placeholder mismatch at "${key}" (${parts.join('; ')})`)
      }
    }
  }

  for (const routeKey of routeKeys) {
    for (const name of localeNames) {
      if (!flat[name].has(routeKey)) {
        failures.push(`[${name}] route key missing: ${routeKey}`)
      }
    }
  }

  return failures
}

export function extractRouteI18nKeys(routerSource) {
  return [...new Set([...routerSource.matchAll(/\b(?:titleKey|subtitleKey):\s*['"]([^'"]+)['"]/g)].map((m) => m[1]))].sort()
}

async function readJson(filePath) {
  const source = await readFile(filePath, 'utf8')
  try {
    return JSON.parse(source)
  } catch (err) {
    throw new Error(`Invalid JSON at ${filePath}: ${err instanceof Error ? err.message : String(err)}`)
  }
}

async function listJavaScriptFiles(dirPath) {
  const entries = await readdir(dirPath, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const entryPath = path.join(dirPath, entry.name)
    if (entry.isDirectory()) {
      files.push(...await listJavaScriptFiles(entryPath))
    } else if (entry.isFile() && entry.name.endsWith('.js')) {
      files.push(entryPath)
    }
  }
  return files.sort()
}

async function readRouterSource(routerDir) {
  const files = await listJavaScriptFiles(routerDir)
  const sources = await Promise.all(files.map((filePath) => readFile(filePath, 'utf8')))
  return sources.join('\n')
}

async function main() {
  const root = process.cwd()
  const localesDir = path.join(root, 'src', 'locales')
  const routerDir = path.join(root, 'src', 'router')

  const [fr, en, routerSource] = await Promise.all([
    readJson(path.join(localesDir, 'fr.json')),
    readJson(path.join(localesDir, 'en.json')),
    readRouterSource(routerDir),
  ])

  const failures = validateLocales({
    locales: { fr, en },
    routeKeys: extractRouteI18nKeys(routerSource),
    referenceLocale: 'fr',
  })

  if (failures.length) {
    console.error(`i18n check failed (${failures.length} issue${failures.length > 1 ? 's' : ''}):`)
    for (const failure of failures) console.error(`  - ${failure}`)
    process.exit(1)
  }
  console.log('i18n check passed.')
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error))
    process.exit(1)
  })
}
