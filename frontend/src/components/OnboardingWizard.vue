<template>
  <Teleport to="body">
    <transition name="ob-fade">
      <div v-if="visible" class="ob-overlay">
        <div class="ob-shell">
          <!-- ═══ Sidebar ═══ -->
          <div class="ob-sidebar">
            <div class="ob-brand">
              <img
                src="/assets/icons/mediakeeper.png"
                class="ob-brand-logo"
                alt=""
                onerror="this.style.display = 'none'"
              />
              <span class="ob-brand-name">MediaKeeper</span>
            </div>

            <nav class="ob-nav">
              <button
                v-for="(step, i) in steps"
                :key="i"
                class="ob-nav-item"
                :class="{
                  'ob-nav-active': i === currentStep,
                  'ob-nav-done': i < currentStep,
                  'ob-nav-locked': i > currentStep,
                }"
                @click="i <= currentStep ? (currentStep = i) : null"
              >
                <span class="ob-nav-bullet">
                  <Check v-if="i < currentStep" :size="11" :stroke-width="3" />
                  <span v-else>{{ i + 1 }}</span>
                </span>
                <span class="ob-nav-label">{{ step.label }}</span>
              </button>
            </nav>

            <div class="ob-sidebar-footer">
              <div class="ob-progress-bar">
                <div
                  class="ob-progress-fill"
                  :style="{ width: (currentStep / (steps.length - 1)) * 100 + '%' }"
                />
              </div>
              <span class="ob-progress-text">
                {{ currentStep }} / {{ steps.length - 1 }} {{ $t('onboarding.stepsCompleted') }}
              </span>
            </div>
          </div>

          <!-- ═══ Main ═══ -->
          <div class="ob-main">
            <div class="ob-content">
              <transition name="ob-slide" mode="out-in">
                <!-- Step 0 — Welcome -->
                <div v-if="currentStep === 0" key="welcome" class="ob-panel">
                  <div class="ob-welcome-hero">
                    <div class="ob-welcome-orbs" aria-hidden="true">
                      <div class="ob-orb ob-orb-1" />
                      <div class="ob-orb ob-orb-2" />
                      <div class="ob-orb ob-orb-3" />
                    </div>
                    <div class="ob-welcome-center">
                      <img
                        src="/assets/icons/mediakeeper.png"
                        class="ob-welcome-logo"
                        alt=""
                        onerror="this.style.display = 'none'"
                      />
                      <h1 class="ob-welcome-title">{{ $t('onboarding.welcomeTitle') }}</h1>
                      <p class="ob-welcome-sub">{{ $t('onboarding.welcomeDesc') }}</p>
                    </div>
                  </div>
                  <div class="ob-feature-grid">
                    <div v-for="f in features" :key="f.id" class="ob-feature-card">
                      <div class="ob-feature-icon" :style="{ background: f.bg }">
                        <component :is="f.icon" :size="18" :stroke-width="1.8" />
                      </div>
                      <div>
                        <div class="ob-feature-name">{{ f.name }}</div>
                        <div class="ob-feature-desc">{{ f.desc }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Step 1 — Emby -->
                <ObToolStep
                  v-else-if="currentStep === 1"
                  key="emby"
                  v-model="emby"
                  icon-bg="rgba(82,181,182,.12)"
                  icon-src="/assets/icons/emby.svg"
                  :title="$t('onboarding.embyTitle')"
                  :desc="$t('onboarding.embyDesc')"
                  has-url-field
                  :url-label="$t('onboarding.embyUrl')"
                  url-placeholder="http://192.168.1.x:8096"
                  :key-label="$t('onboarding.embyKey')"
                  :key-placeholder="$t('onboarding.embyKeyPlaceholder')"
                  key-help-url="https://emby.media/community/index.php?/topic/16538-how-do-i-obtain-an-api-key/"
                  :key-help-text="$t('onboarding.embyKeyHelp')"
                  :guide-chips="[
                    $t('onboarding.embyDashboard'),
                    $t('onboarding.advanced'),
                    $t('onboarding.security'),
                    $t('onboarding.apiKeys'),
                  ]"
                  @test="testEmby"
                />

                <!-- Step 2 — TMDB -->
                <ObToolStep
                  v-else-if="currentStep === 2"
                  key="tmdb"
                  v-model="tmdb"
                  icon-bg="rgba(1,212,113,.08)"
                  icon-src="/assets/icons/tmdb.svg"
                  :title="$t('onboarding.tmdbTitle')"
                  :desc="$t('onboarding.tmdbDesc')"
                  :key-label="$t('onboarding.tmdbKey')"
                  :key-placeholder="$t('onboarding.tmdbKeyPlaceholder')"
                  key-help-url="https://www.themoviedb.org/settings/api"
                  :key-help-text="$t('onboarding.tmdbKeyHelp')"
                  :guide-chips="[
                    'themoviedb.org',
                    $t('onboarding.profile'),
                    $t('onboarding.settings'),
                    'API → Read Access Token',
                  ]"
                  @test="testTmdb"
                />

                <!-- Step 3 — OpenSubtitles -->
                <ObToolStep
                  v-else-if="currentStep === 3"
                  key="opensubs"
                  v-model="openSubs"
                  icon-bg="rgba(168,85,247,.1)"
                  :title="$t('onboarding.opensubsTitle')"
                  :desc="$t('onboarding.opensubsDesc')"
                  :key-label="$t('onboarding.opensubsKey')"
                  :key-placeholder="$t('onboarding.opensubsKeyPlaceholder')"
                  key-help-url="https://www.opensubtitles.com/fr/consumers"
                  :key-help-text="$t('onboarding.opensubsKeyHelp')"
                  @test="testOpenSubs"
                />

                <!-- Step 4 — Folders -->
                <ObFoldersStep
                  v-else-if="currentStep === 4"
                  key="folders"
                  :folders="folders"
                  :browse-path="browsePath"
                  :browse-dirs="browseDirs"
                  :browse-loading="browseLoading"
                  :browse-open="browseOpen"
                  @add-folder="addFolder"
                  @remove-folder="removeFolder"
                  @open-browser="openBrowser"
                  @browse-to="browseTo"
                  @select-browse-path="selectBrowsePath"
                />

                <!-- Step 5 — Tour -->
                <div v-else-if="currentStep === 5" key="tour" class="ob-panel">
                  <h2 class="ob-panel-title">{{ $t('onboarding.tourTitle') }}</h2>
                  <p class="ob-panel-desc ob-panel-desc-tight">{{ $t('onboarding.tourDesc') }}</p>

                  <div class="ob-tour-grid">
                    <div
                      v-for="(mod, i) in modules"
                      :key="mod.id"
                      class="ob-tour-card"
                      :class="{ 'ob-tour-active': tourActive === i }"
                      @click="tourActive = i"
                    >
                      <div class="ob-tour-card-inner">
                        <div class="ob-tour-icon" :style="{ background: mod.bg }">
                          <component :is="mod.icon" :size="16" :stroke-width="1.8" />
                        </div>
                        <span class="ob-tour-name">{{ mod.name }}</span>
                      </div>
                    </div>
                  </div>

                  <transition name="ob-fade">
                    <div v-if="modules[tourActive]" class="ob-tour-detail">
                      <div class="ob-tour-detail-header">
                        <div
                          class="ob-tour-icon-lg"
                          :style="{ background: modules[tourActive].bg }"
                        >
                          <component
                            :is="modules[tourActive].icon"
                            :size="22"
                            :stroke-width="1.8"
                          />
                        </div>
                        <div>
                          <div class="ob-tour-detail-name">{{ modules[tourActive].name }}</div>
                          <div class="ob-tour-detail-desc">{{ modules[tourActive].desc }}</div>
                        </div>
                      </div>
                      <div class="ob-tour-features">
                        <div
                          v-for="feat in modules[tourActive].features"
                          :key="feat"
                          class="ob-tour-feat"
                        >
                          <Check :size="11" :stroke-width="2.5" class="ob-feature-check" />
                          {{ feat }}
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>

                <!-- Step 6 — Done -->
                <div v-else-if="currentStep === 6" key="done" class="ob-panel ob-panel-done">
                  <div class="ob-done-visual">
                    <div class="ob-done-ring ob-done-ring-1" />
                    <div class="ob-done-ring ob-done-ring-2" />
                    <div class="ob-done-ring ob-done-ring-3" />
                    <img
                      src="/assets/icons/mediakeeper.png"
                      class="ob-done-logo"
                      alt=""
                      onerror="this.style.display = 'none'"
                    />
                  </div>
                  <h2 class="ob-done-title">{{ $t('onboarding.doneTitle') }}</h2>
                  <p class="ob-done-desc">{{ $t('onboarding.doneDesc') }}</p>
                  <div class="ob-done-summary">
                    <div
                      class="ob-done-item"
                      :class="{
                        ok: emby.url && (emby.api_key || emby._configured),
                        skip: !emby.url,
                      }"
                    >
                      <img src="/assets/icons/emby.svg" width="16" height="16" />
                      <span>Emby</span>
                      <span class="ob-done-badge">
                        {{
                          emby.url && (emby.api_key || emby._configured)
                            ? $t('onboarding.configured')
                            : $t('onboarding.skipped')
                        }}
                      </span>
                    </div>
                    <div
                      class="ob-done-item"
                      :class="{
                        ok: tmdb.api_key || tmdb._configured,
                        skip: !(tmdb.api_key || tmdb._configured),
                      }"
                    >
                      <img src="/assets/icons/tmdb.svg" width="16" height="16" />
                      <span>TMDB</span>
                      <span class="ob-done-badge">
                        {{
                          tmdb.api_key || tmdb._configured
                            ? $t('onboarding.configured')
                            : $t('onboarding.skipped')
                        }}
                      </span>
                    </div>
                    <div
                      class="ob-done-item"
                      :class="{
                        ok: openSubs.api_key || openSubs._configured,
                        skip: !(openSubs.api_key || openSubs._configured),
                      }"
                    >
                      <Captions :size="16" />
                      <span>OpenSubtitles</span>
                      <span class="ob-done-badge">
                        {{
                          openSubs.api_key || openSubs._configured
                            ? $t('onboarding.configured')
                            : $t('onboarding.skipped')
                        }}
                      </span>
                    </div>
                    <div class="ob-done-item" :class="{ ok: hasFolders, skip: !hasFolders }">
                      <Folder :size="16" />
                      <span>{{ $t('onboarding.foldersTitle') }}</span>
                      <span class="ob-done-badge">
                        {{
                          hasFolders
                            ? folders.filter(f => f.path).length +
                              ' ' +
                              $t('onboarding.foldersConfigured')
                            : $t('onboarding.skipped')
                        }}
                      </span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>

            <!-- Footer -->
            <div class="ob-footer">
              <button
                v-if="currentStep > 0 && currentStep < 6"
                class="ob-btn ob-btn-ghost"
                @click="prev"
              >
                <ChevronLeft :size="14" />
                {{ $t('common.back') }}
              </button>
              <div class="ob-footer-spacer" />
              <button
                v-if="currentStep > 0 && currentStep < 6"
                class="ob-btn ob-btn-skip"
                @click="skip"
              >
                {{ $t('onboarding.skip') }}
              </button>
              <button
                v-if="currentStep < 6"
                class="ob-btn ob-btn-primary"
                :disabled="saving"
                @click="next"
              >
                <span v-if="saving" class="ob-spin" />
                <span v-else>
                  {{ currentStep === 5 ? $t('onboarding.finish') : $t('onboarding.next') }}
                </span>
                <ChevronRight v-if="!saving && currentStep < 5" :size="14" />
              </button>
              <button v-else class="ob-btn ob-btn-launch" :disabled="saving" @click="complete">
                <span v-if="saving" class="ob-spin" />
                <Zap v-else :size="15" />
                {{ $t('onboarding.launch') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { useOnboarding } from '@/composables/useOnboarding'
import ObToolStep from './onboarding/ObToolStep.vue'
import ObFoldersStep from './onboarding/ObFoldersStep.vue'
import { Captions, Check, ChevronLeft, ChevronRight, Folder, Zap } from 'lucide-vue-next'
import '@/assets/styles/onboarding-wizard.css'

const props = defineProps({ forceShow: { type: Boolean, default: false } })
const emit = defineEmits(['done'])

const {
  visible,
  currentStep,
  saving,
  tourActive,
  steps,
  features,
  modules,
  emby,
  tmdb,
  openSubs,
  testEmby,
  testTmdb,
  testOpenSubs,
  folders,
  hasFolders,
  addFolder,
  removeFolder,
  browsePath,
  browseDirs,
  browseLoading,
  browseOpen,
  openBrowser,
  browseTo,
  selectBrowsePath,
  next,
  prev,
  skip,
  complete,
  checkAndShow,
} = useOnboarding(props, emit)

defineExpose({ checkAndShow })
</script>
