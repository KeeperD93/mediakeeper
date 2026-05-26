/**
 * Whitelist of lucide-vue-next icons used by MkButton.
 *
 * Why a whitelist (Rules.md §3, perf):
 *   `import * as lucide from 'lucide-vue-next'` cannot be tree-shaken by Vite
 *   and pulls ~500 kb of icons into the prod bundle. A static named import
 *   per icon yields a tree-shakable ~5-10 kb footprint.
 *
 * To add a new icon: import it below, then add the kebab-case → component
 * mapping in MK_BUTTON_ICONS. Keep alphabetical by kebab-case key.
 */
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  EyeOff,
  Info,
  LayoutGrid,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Settings,
  Shuffle,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'

import type { Component } from 'vue'

export const MK_BUTTON_ICONS: Readonly<Record<string, Component>> = Object.freeze({
  check: Check,
  'chevron-left': ChevronLeft,
  'chevron-right': ChevronRight,
  download: Download,
  eye: Eye,
  'eye-off': EyeOff,
  info: Info,
  'layout-grid': LayoutGrid,
  pencil: Pencil,
  plus: Plus,
  'refresh-cw': RefreshCw,
  save: Save,
  settings: Settings,
  shuffle: Shuffle,
  'trash-2': Trash2,
  upload: Upload,
  x: X,
})

export type MkButtonIconName = keyof typeof MK_BUTTON_ICONS

export function getMkButtonIcon(name: string | null | undefined): Component | null {
  if (!name) return null
  return MK_BUTTON_ICONS[name as MkButtonIconName] ?? null
}

export { Loader2 as MkButtonSpinner }
