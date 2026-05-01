/// <reference types="vite/client" />

/**
 * Typed import.meta.env — document every VITE_* the app reads.
 * Adding a new one here makes it autocomplete-able and type-checked.
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_APP_NAME?: string
  readonly VITE_APP_VERSION?: string
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/**
 * Shim for `.vue` files — lets TypeScript understand Vue single-file
 * components imported from .ts code. Matches the default
 * DefineComponent signature of Vue 3.
 */
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}
