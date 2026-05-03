<template>
  <div ref="pageRef" class="login-page">
    <canvas ref="canvasRef" class="login-particles" />
    <div class="login-grain" aria-hidden="true" />
    <div class="login-scanlines" aria-hidden="true" />
    <div class="login-orbs" aria-hidden="true">
      <div class="login-orb login-orb-1" />
      <div class="login-orb login-orb-2" />
      <div class="login-orb login-orb-3" />
      <div class="login-orb login-orb-4" />
    </div>
    <div class="login-grid" aria-hidden="true" />

    <div v-if="!backendReady" class="login-waiting">
      <img :src="logoUrl" alt="MediaKeeper" class="login-waiting-logo" />
      <div class="login-waiting-ring">
        <svg viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" stroke="rgba(255,255,255,.06)" stroke-width="2" fill="none" />
          <circle cx="24" cy="24" r="20" stroke="url(#wait-grad)" stroke-width="2" fill="none"
            stroke-linecap="round" stroke-dasharray="100 26" class="login-waiting-arc" />
          <defs>
            <linearGradient id="wait-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#818cf8" />
              <stop offset="100%" stop-color="#6366f1" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <p class="login-waiting-text">{{ t('login.starting') }}</p>
    </div>

    <transition name="login-appear">
      <div v-if="backendReady" class="login-card">
        <div class="login-hero">
          <div class="login-hero-glow" aria-hidden="true" />
          <div class="login-hero-content">
            <img :src="bannerUrl" alt="MediaKeeper" class="login-hero-banner" />
            <h1 class="sr-only">{{ t('login.title') }}</h1>
            <p class="login-hero-sub">{{ t('login.title') }}</p>
          </div>
          <div class="login-hero-line" />
        </div>

        <div class="login-form-wrap">
          <div v-if="errorMsg" class="login-error">
            <TriangleAlert :size="14" />
            {{ errorMsg }}
          </div>

          <div class="login-fields">
            <div class="login-field">
              <label class="login-label">{{ t('login.username') }}</label>
              <div class="login-input-wrap">
                <User class="login-input-icon" :size="15" :stroke-width="1.8" />
                <input v-model="username" type="text" :placeholder="t('login.username')" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" class="login-input" @keydown.enter="doLogin" />
              </div>
            </div>

            <div class="login-field">
              <label class="login-label">{{ t('login.password') }}</label>
              <div class="login-input-wrap">
                <LockKeyhole class="login-input-icon" :size="15" :stroke-width="1.8" />
                <input v-model="password" type="password" :placeholder="t('login.password')" autocomplete="new-password" class="login-input" @keydown.enter="doLogin" />
              </div>
            </div>

            <label class="login-remember">
              <input v-model="remember" type="checkbox" class="login-checkbox" />
              <span>{{ $t('login.remember') }}</span>
            </label>

            <button class="login-submit" :disabled="submitting" @click="doLogin">
              <MkSpinner v-if="submitting" size="sm" inline />
              <template v-else>
                <LogIn :size="15" />
              </template>
              {{ submitting ? t('common.loading') : t('login.submit') }}
            </button>
          </div>

          <div class="login-links">
            <a href="https://discord.gg/mediakeeper" target="_blank" rel="noopener" title="Discord">
              <IconDiscord :size="18" />
            </a>
            <a href="https://github.com/mediakeeper" target="_blank" rel="noopener" title="GitHub">
              <Github :size="18" />
            </a>
            <a href="https://wiki.mediakeeper.app" target="_blank" rel="noopener" title="Wiki">
              <BookOpen :size="18" :stroke-width="1.8" />
            </a>
            <a href="https://mediakeeper.app" target="_blank" rel="noopener" :title="$t('login.officialSite')">
              <Globe :size="18" :stroke-width="1.8" />
            </a>
          </div>

          <p v-if="appVersion" class="login-version" data-test="login-version">
            MediaKeeper v{{ appVersion }} —
            <a :href="repoUrl" target="_blank" rel="noopener noreferrer" data-test="login-github-link">
              {{ t('attribution.githubLink') }}
            </a>
          </p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { fetchApiResponse, resolveApiError } from '@/composables/useApi'
import { useTheme } from '@/composables/useTheme'
import { initLoginParticles } from '@/composables/useLoginParticles'
import { BookOpen, Github, Globe, LockKeyhole, LogIn, TriangleAlert, User } from 'lucide-vue-next'
import IconDiscord from '@/components/icons/IconDiscord.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import '@/assets/styles/login-view.css'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const { login, checkAuth } = useAuth()
const { particlesEnabled } = useTheme()

const username = ref('')
const password = ref('')
const remember = ref(false)
const errorMsg = ref('')
const submitting = ref(false)
const backendReady = ref(false)
const appVersion = ref('')
const pageRef = ref(null)
const canvasRef = ref(null)
let cleanupParticles = null

const repoUrl = 'https://github.com/KeeperD93/mediakeeper'
const logoUrl = '/assets/icons/mediakeeper.png'
const bannerUrl = '/assets/icons/mediakeeper_banner.png'

function getRedirectTarget() {
  return typeof route.query.redirect === 'string' ? route.query.redirect : ''
}

async function waitForAuth() {
  while (true) {
    try {
      const res = await fetchApiResponse('/api/health', {
        retryOn401: false,
        redirectOn401: false,
      })
      if (res.status < 500) { backendReady.value = true; return }
    } catch { /* silent: health poll retries by design */ }
    await new Promise(r => setTimeout(r, 1500))
  }
}

async function fetchVersion() {
  try {
    const res = await fetchApiResponse('/api/changelog/current', {
      retryOn401: false,
      redirectOn401: false,
    })
    if (res.ok) {
      const data = await res.json()
      appVersion.value = data.version || ''
    }
  } catch { /* silent: version display is cosmetic */ }
}

onMounted(async () => {
  if (particlesEnabled.value) cleanupParticles = initLoginParticles(canvasRef.value, pageRef.value)
  await waitForAuth()
  const justLoggedOut = route.query.logged_out === '1' || sessionStorage.getItem('mk_just_logged_out') === '1'
  const redirect = getRedirectTarget()
      const isPortalRedirect = redirect.startsWith('/portal')

  if (justLoggedOut) {
    try {
      sessionStorage.removeItem('mk_just_logged_out')
    } catch { /* ignore */ }
    fetchVersion()
    const saved = localStorage.getItem('mediakeeper_saved_username')
    if (saved) {
      username.value = saved
      remember.value = true
    }
    return
  }

  if (await checkAuth()) {
    router.replace(redirect || '/')
    return
  }

  try {
    const { usePortalAuth } = await import('@/composables/portal/usePortalAuth')
    const ok = await usePortalAuth().checkPortalAuth()
    if (ok) {
        router.replace(isPortalRedirect ? redirect : '/portal')
      return
    }
  } catch {
    // Stay on the login page if the portal check fails.
  }

  fetchVersion()
  const saved = localStorage.getItem('mediakeeper_saved_username')
  if (saved) {
    username.value = saved
    remember.value = true
  }
})

onUnmounted(() => {
  if (cleanupParticles) cleanupParticles()
})

async function doLogin() {
  errorMsg.value = ''

  if (!username.value.trim() || !password.value) {
    errorMsg.value = t('login.allRequired')
    return
  }

  submitting.value = true
  try {
    const data = await login(username.value.trim(), password.value)
    const redirect = getRedirectTarget()
      const isPortalRedirect = redirect.startsWith('/portal')

    if (remember.value) {
      localStorage.setItem('mediakeeper_saved_username', username.value.trim())
    } else {
      localStorage.removeItem('mediakeeper_saved_username')
    }

    localStorage.setItem('mediakeeper_username', data.username)

    if (data.scope === 'portal') {
        router.push(isPortalRedirect ? redirect : '/portal')
    } else if (data.must_change_password) {
      router.push('/?force_change_password=1')
    } else {
      router.push(redirect || '/')
    }
  } catch (e) {
    errorMsg.value = resolveApiError(e.message)
  } finally {
    submitting.value = false
  }
}
</script>
