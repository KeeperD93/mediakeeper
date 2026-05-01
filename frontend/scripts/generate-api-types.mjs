#!/usr/bin/env node
/**
 * Generates TypeScript types from the FastAPI OpenAPI schema.
 *
 * Produces `src/types/api.d.ts` — a single .d.ts file containing one type
 * per endpoint and per schema model. Import and consume in useApi and the
 * per-domain composables for end-to-end type safety.
 *
 * Usage:
 *   # 1. Start the backend locally:
 *   #    docker compose up backend     (or uvicorn main:app --reload)
 *   # 2. Generate types:
 *   npm run types:api
 *
 * The fetched OpenAPI URL defaults to http://localhost:8000/openapi.json.
 * Override with: OPENAPI_URL=https://... npm run types:api
 */
import openapiTS, { astToString } from 'openapi-typescript'
import { writeFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')
const OUT = resolve(ROOT, 'src/types/api.d.ts')
const URL = process.env.OPENAPI_URL || 'http://localhost:8000/openapi.json'

const HEADER = `/**
 * AUTO-GENERATED — do not edit by hand.
 * Regenerate with: npm run types:api
 * Source: ${URL}
 */

`

async function main() {
  console.log(`[types:api] fetching ${URL}…`)
  const ast = await openapiTS(new URL(URL))
  const content = HEADER + astToString(ast)
  await mkdir(dirname(OUT), { recursive: true })
  await writeFile(OUT, content, 'utf8')
  console.log(`[types:api] wrote ${OUT} (${content.length} bytes)`)
}

main().catch(err => {
  console.error('[types:api] failed:', err.message || err)
  process.exit(1)
})
