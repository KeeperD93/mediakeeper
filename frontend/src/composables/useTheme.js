import { ref, readonly, watchEffect, computed } from 'vue'
import { fetchApiResponse } from '@/composables/useApi'
import { applyLocaleEphemeral, getLocale, isSupportedLocale } from '@/i18n'

// ---- Theme system ----
// Single theme for v0.x. Alternate themes return in v1.0, rebuilt on top
// of the design-token foundation. The exported API (themeName, themeList,
// setThemeName, toggleTheme, setTheme, isDark) is kept stable so existing
// consumers compile unchanged; the theme setters are no-ops for now.
export const THEMES = {
  dark: { label: 'Default', isDark: true, bodyClass: '' },
}

const themeName = ref('dark')
const isDark = computed(() => true)

// ---- Radius ----
const borderRadius = ref(parseInt(localStorage.getItem('mediakeeper_radius') || '12'))

function applyRadius(r) {
  const root = document.documentElement
  root.style.setProperty('--radius-card', r + 'px')
  root.style.setProperty('--radius-btn', Math.max(4, r - 4) + 'px')
  // Form fields stay crisp rectangles: a big negative offset + low floor keeps
  // inputs/selects markedly squarer than cards/buttons (4px at the default r=12).
  root.style.setProperty('--radius-input', Math.max(2, r - 8) + 'px')
  root.style.setProperty('--radius-sm', Math.max(4, r - 6) + 'px')
}
applyRadius(borderRadius.value)

// ---- Custom background ----
const customBg = ref(localStorage.getItem('mediakeeper_bg') || '')
const customBgOpacity = ref(parseFloat(localStorage.getItem('mediakeeper_bg_opacity') || '0.15'))
const customBgBlur = ref(parseInt(localStorage.getItem('mediakeeper_bg_blur') || '20'))

function applyCustomBg(url, opacity, blur) {
  const root = document.documentElement
  let el = document.getElementById('mk-custom-bg')
  if (url) {
    if (!el) {
      el = document.createElement('div')
      el.id = 'mk-custom-bg'
      document.body.insertBefore(el, document.body.firstChild)
    }
    root.style.setProperty('--custom-bg-url', `url("${url}")`)
    root.style.setProperty('--custom-bg-opacity', String(opacity))
    root.style.setProperty('--custom-bg-blur', blur + 'px')
    document.body.classList.add('has-custom-bg')
  } else {
    if (el) el.remove()
    root.style.removeProperty('--custom-bg-url')
    document.body.classList.remove('has-custom-bg')
  }
}
applyCustomBg(customBg.value, customBgOpacity.value, customBgBlur.value)

// ---- Particles ----
const particlesEnabled = ref(localStorage.getItem('mediakeeper_particles') !== 'false')

// ---- Pill glow intensity (0 = off, 1 = default, 2 = max) ----
const glowIntensity = ref(parseFloat(localStorage.getItem('mediakeeper_glow') ?? '1'))
if (!Number.isFinite(glowIntensity.value) || glowIntensity.value < 0 || glowIntensity.value > 2)
  glowIntensity.value = 1
function applyGlow(v) {
  const root = document.documentElement
  const s = Math.max(0, Math.min(2, Number(v) || 0))
  root.style.setProperty('--mk-glow', String(s))
}
applyGlow(glowIntensity.value)

// ---- Accent ----
const ACCENT_PRESETS = {
  mediakeeper: {
    500: '#5c5792',
    400: '#7972a8',
    300: '#9690bf',
    600: '#4d4878',
    700: '#3d395f',
    rgb: '92,87,146',
  },
  indigo: {
    500: '#6366f1',
    400: '#818cf8',
    300: '#a5b4fc',
    600: '#4f46e5',
    700: '#4338ca',
    rgb: '99,102,241',
  },
  blue: {
    500: '#3b82f6',
    400: '#60a5fa',
    300: '#93c5fd',
    600: '#2563eb',
    700: '#1d4ed8',
    rgb: '59,130,246',
  },
  violet: {
    500: '#8b5cf6',
    400: '#a78bfa',
    300: '#c4b5fd',
    600: '#7c3aed',
    700: '#6d28d9',
    rgb: '139,92,246',
  },
  emerald: {
    500: '#10b981',
    400: '#34d399',
    300: '#6ee7b7',
    600: '#059669',
    700: '#047857',
    rgb: '16,185,129',
  },
  rose: {
    500: '#f43f5e',
    400: '#fb7185',
    300: '#fda4af',
    600: '#e11d48',
    700: '#be123c',
    rgb: '244,63,94',
  },
  amber: {
    500: '#f59e0b',
    400: '#fbbf24',
    300: '#fcd34d',
    600: '#d97706',
    700: '#b45309',
    rgb: '245,158,11',
  },
  cyan: {
    500: '#06b6d4',
    400: '#22d3ee',
    300: '#67e8f9',
    600: '#0891b2',
    700: '#0e7490',
    rgb: '6,182,212',
  },
}

// Single locked accent for now — the MediaKeeper signature violet. The
// picker is dormant (ParamsAppearanceTab.vue) and the server accent
// preference is intentionally ignored in syncFromServer below, so the whole
// app uses one accent until alternate accents return. To re-enable: restore
// the picker UI + the accent block in syncFromServer, and seed from
// ``ref(localStorage.getItem('mediakeeper_accent') || 'mediakeeper')``.
const accentName = ref('mediakeeper')

function applyAccent(name) {
  const preset = ACCENT_PRESETS[name] || ACCENT_PRESETS.indigo
  const root = document.documentElement
  root.style.setProperty('--accent-500', preset[500])
  root.style.setProperty('--accent-400', preset[400])
  root.style.setProperty('--accent-300', preset[300])
  root.style.setProperty('--accent-600', preset[600])
  root.style.setProperty('--accent-700', preset[700])
  root.style.setProperty('--accent-rgb', preset.rgb)
  root.style.setProperty('--accent', preset[700])
  root.style.setProperty('--accent-light', preset[700] + '33')
}
applyAccent(accentName.value)
watchEffect(() => {
  applyAccent(accentName.value)
})

// ---- Sync BDD — never overwrite localStorage with an invalid server value ----
let _syncDone = false

async function syncFromServer() {
  if (_syncDone) return
  try {
    const res = await fetchApiResponse('/api/auth/preferences', { redirectOn401: false })
    if (!res.ok) return
    const prefs = await res.json()
    // Accent intentionally NOT synced: locked to the single MediaKeeper
    // accent (see accentName above). Restore this block with multi-accent.
    // Radius
    if (prefs.radius != null && !isNaN(prefs.radius)) {
      borderRadius.value = prefs.radius
      localStorage.setItem('mediakeeper_radius', prefs.radius)
      applyRadius(prefs.radius)
    }
    // Particles
    if (prefs.particles != null) {
      particlesEnabled.value = prefs.particles !== false
      localStorage.setItem('mediakeeper_particles', particlesEnabled.value)
    }
    // Glow intensity
    if (prefs.glow != null && Number.isFinite(Number(prefs.glow))) {
      const g = Math.max(0, Math.min(2, Number(prefs.glow)))
      glowIntensity.value = g
      localStorage.setItem('mediakeeper_glow', String(g))
      applyGlow(g)
    }
    // Locale — server is the source of truth; drives Discord notification language
    if (prefs.locale && isSupportedLocale(prefs.locale) && prefs.locale !== getLocale()) {
      await applyLocaleEphemeral(prefs.locale)
      localStorage.setItem('mediakeeper_locale', prefs.locale)
    }
    _syncDone = true
  } catch {
    /* silent: preferences sync, UI keeps local values */
  }
}

async function _savePrefsToServer() {
  const body = JSON.stringify({
    theme: 'dark',
    sidebar_collapsed: localStorage.getItem('mk_sidebar_collapsed') === 'true',
    accent: accentName.value,
    radius: borderRadius.value,
    particles: particlesEnabled.value,
    glow: glowIntensity.value,
  })
  try {
    await fetchApiResponse('/api/auth/preferences', {
      method: 'POST',
      body,
      redirectOn401: false,
    })
  } catch {
    /* silent: preferences save is best-effort, retried on next change */
  }
}

export function useTheme() {
  // No-op stubs kept so existing call sites compile; the full theme
  // system is reintroduced in v1.0 on top of the design tokens.
  function setThemeName() {}
  function toggleTheme() {}
  function setTheme() {}

  function setAccent(name) {
    if (!ACCENT_PRESETS[name]) return
    accentName.value = name
    localStorage.setItem('mediakeeper_accent', name)
    applyAccent(name)
    _savePrefsToServer()
  }

  function setRadius(r) {
    borderRadius.value = r
    localStorage.setItem('mediakeeper_radius', r)
    applyRadius(r)
  }

  function setCustomBg(url, opacity, blur) {
    customBg.value = url
    customBgOpacity.value = opacity
    customBgBlur.value = blur
    try {
      localStorage.setItem('mediakeeper_bg', url)
      localStorage.setItem('mediakeeper_bg_opacity', opacity)
      localStorage.setItem('mediakeeper_bg_blur', blur)
    } catch {
      console.warn(
        '[useTheme.setCustomBg] failed to persist custom background (localStorage quota)',
      )
    }
    applyCustomBg(url, opacity, blur)
  }

  function clearCustomBg() {
    setCustomBg('', 0.15, 20)
  }

  function setParticles(enabled) {
    particlesEnabled.value = enabled
    localStorage.setItem('mediakeeper_particles', enabled)
    _savePrefsToServer()
  }

  function setGlowIntensity(v) {
    const s = Math.max(0, Math.min(2, Number(v) || 0))
    glowIntensity.value = s
    localStorage.setItem('mediakeeper_glow', String(s))
    applyGlow(s)
    _savePrefsToServer()
  }

  function saveAll() {
    _savePrefsToServer()
  }

  const accentPresets = computed(() =>
    Object.entries(ACCENT_PRESETS).map(([name, colors]) => ({ name, color: colors[500] })),
  )

  const themeList = computed(() =>
    Object.entries(THEMES).map(([name, def]) => ({
      name,
      label: def.label,
      isDark: def.isDark,
    })),
  )

  return {
    isDark: readonly(isDark),
    themeName: readonly(themeName),
    themeList,
    setThemeName,
    toggleTheme,
    setTheme,
    accentName: readonly(accentName),
    accentPresets,
    setAccent,
    borderRadius: readonly(borderRadius),
    setRadius,
    customBg: readonly(customBg),
    customBgOpacity: readonly(customBgOpacity),
    customBgBlur: readonly(customBgBlur),
    setCustomBg,
    clearCustomBg,
    particlesEnabled: readonly(particlesEnabled),
    setParticles,
    glowIntensity: readonly(glowIntensity),
    setGlowIntensity,
    saveAll,
    syncFromServer,
    THEMES,
  }
}
