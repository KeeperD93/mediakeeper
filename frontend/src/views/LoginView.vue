<template>
  <a href="#main-content" class="mk-skip-link">{{ t('common.skipToMain') }}</a>
  <main id="main-content" ref="pageRef" tabindex="-1" class="login-page">
    <canvas ref="canvasRef" class="login-particles" aria-hidden="true" />
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
          <circle
            cx="24"
            cy="24"
            r="20"
            stroke="rgba(255,255,255,.06)"
            stroke-width="2"
            fill="none"
          />
          <circle
            cx="24"
            cy="24"
            r="20"
            stroke="url(#wait-grad)"
            stroke-width="2"
            fill="none"
            stroke-linecap="round"
            stroke-dasharray="100 26"
            class="login-waiting-arc"
          />
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
            <h1 class="sr-only">{{ t(headingKey) }}</h1>
            <p class="login-hero-sub">{{ t(subtitleKey) }}</p>
          </div>
          <div class="login-hero-line" />
        </div>

        <div class="login-form-wrap">
          <div v-if="loggedOutMsg" class="login-info" data-test="login-logged-out" role="status">
            <CircleCheck :size="14" />
            {{ loggedOutMsg }}
          </div>

          <div v-if="errorMsg" class="login-error" role="alert">
            <TriangleAlert :size="14" />
            {{ errorMsg }}
          </div>

          <div class="login-fields">
            <div class="login-field">
              <label class="login-label">{{ t(usernameKey) }}</label>
              <div class="login-input-wrap">
                <User class="login-input-icon" :size="15" :stroke-width="1.8" />
                <input
                  v-model="username"
                  type="text"
                  :placeholder="t(usernameKey)"
                  autocomplete="off"
                  autocorrect="off"
                  autocapitalize="off"
                  spellcheck="false"
                  class="login-input"
                  @keydown.enter="doLogin"
                />
              </div>
            </div>

            <div class="login-field">
              <label class="login-label">{{ t(passwordKey) }}</label>
              <div class="login-input-wrap">
                <LockKeyhole class="login-input-icon" :size="15" :stroke-width="1.8" />
                <input
                  v-model="password"
                  type="password"
                  :placeholder="t(passwordKey)"
                  autocomplete="new-password"
                  class="login-input"
                  @keydown.enter="doLogin"
                />
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
              {{ submitting ? t('common.loading') : t(submitKey) }}
            </button>
          </div>

          <div class="login-links">
            <a href="https://discord.gg/A2hyNUUn6a" target="_blank" rel="noopener" title="Discord">
              <IconDiscord :size="18" />
            </a>
            <a
              :href="repoUrl"
              target="_blank"
              rel="noopener noreferrer"
              title="GitHub"
              data-test="login-github-link"
            >
              <Github :size="18" />
            </a>
            <a href="https://wiki.mediakeeper.app" target="_blank" rel="noopener" title="Wiki">
              <BookOpen :size="18" :stroke-width="1.8" />
            </a>
            <a
              href="https://mediakeeper.app"
              target="_blank"
              rel="noopener"
              :title="$t('login.officialSite')"
            >
              <Globe :size="18" :stroke-width="1.8" />
            </a>
          </div>

          <span v-if="appVersion" class="login-version" data-test="login-version">
            v{{ appVersion }}
          </span>
        </div>
      </div>
    </transition>
  </main>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { resolveApiError } from '@/composables/useApi'
import { STORAGE_KEYS } from '@/constants/storage'
import { useTheme } from '@/composables/useTheme'
import { initLoginParticles } from '@/composables/useLoginParticles'
import { useLoginRedirect } from '@/composables/useLoginRedirect'
import {
  BookOpen,
  CircleCheck,
  Github,
  Globe,
  LockKeyhole,
  LogIn,
  TriangleAlert,
  User,
} from 'lucide-vue-next'
import IconDiscord from '@/components/icons/IconDiscord.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import '@/assets/styles/login-view.css'

const { t } = useI18n()
const router = useRouter()
const { login } = useAuth()
const { particlesEnabled } = useTheme()

const username = ref('')
const password = ref('')
const remember = ref(false)
const errorMsg = ref('')
const loggedOutMsg = ref('')
const submitting = ref(false)
const pageRef = ref(null)
const canvasRef = ref(null)
let cleanupParticles = null

const { backendReady, appVersion, getRedirectTarget, start, dispose } = useLoginRedirect({
  username,
  remember,
  errorMsg,
  loggedOutMsg,
})

const repoUrl = 'https://github.com/KeeperD93/mediakeeper'
const logoUrl = '/assets/icons/mediakeeper.png'
const bannerUrl = '/assets/icons/mediakeeper_banner.png'

const isPortalLogin = computed(() => getRedirectTarget().startsWith('/portal'))
const headingKey = computed(() => (isPortalLogin.value ? 'portalLogin.title' : 'login.title'))
const subtitleKey = computed(() => (isPortalLogin.value ? 'portalLogin.subtitle' : 'login.title'))
const usernameKey = computed(() =>
  isPortalLogin.value ? 'portalLogin.username' : 'login.username',
)
const passwordKey = computed(() =>
  isPortalLogin.value ? 'portalLogin.password' : 'login.password',
)
const submitKey = computed(() => (isPortalLogin.value ? 'portalLogin.submit' : 'login.submit'))

onMounted(async () => {
  if (particlesEnabled.value) cleanupParticles = initLoginParticles(canvasRef.value, pageRef.value)
  await start()
})

onUnmounted(() => {
  if (cleanupParticles) cleanupParticles()
  dispose()
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
      localStorage.setItem(STORAGE_KEYS.SAVED_USERNAME, username.value.trim())
    } else {
      localStorage.removeItem(STORAGE_KEYS.SAVED_USERNAME)
    }

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
