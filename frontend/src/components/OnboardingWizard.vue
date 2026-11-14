<template>
  <Teleport to="body">
    <transition name="ob-fade">
      <div v-if="visible" class="ob-overlay">
        <div class="ob-shell">
          <!-- ═══ Sidebar ═══ -->
          <div class="ob-sidebar">
            <div class="ob-brand">
              <img
                src="/assets/icons/mk-logo-128.png"
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
                <div v-if="currentStepId === STEP.WELCOME" key="welcome" class="ob-panel">
                  <div class="ob-welcome-hero">
                    <div class="ob-welcome-orbs" aria-hidden="true">
                      <div class="ob-orb ob-orb-1" />
                      <div class="ob-orb ob-orb-2" />
                      <div class="ob-orb ob-orb-3" />
                    </div>
                    <div class="ob-welcome-center">
                      <img
                        src="/assets/icons/mk-logo-128.png"
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

                <ObLocaleStep
                  v-else-if="currentStepId === STEP.LOCALE"
                  key="locale"
                  v-model:zone-key="zoneKey"
                  :zone-rows="zoneRows"
                  :zone-row="zoneRow"
                />

                <ObToolStep
                  v-else-if="currentStepId === STEP.EMBY"
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

                <ObToolStep
                  v-else-if="currentStepId === STEP.TMDB"
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

                <ObToolStep
                  v-else-if="currentStepId === STEP.OPENSUBTITLES"
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

                <ObFoldersStep
                  v-else-if="currentStepId === STEP.FOLDERS"
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

                <ObTourStep
                  v-else-if="currentStepId === STEP.TOUR"
                  key="tour"
                  v-model:active="tourActive"
                  :modules="modules"
                />

                <ObDoneStep
                  v-else-if="currentStepId === STEP.DONE"
                  key="done"
                  :zone-saved="zoneSaved"
                  :emby="emby"
                  :tmdb="tmdb"
                  :open-subs="openSubs"
                  :folders="folders"
                  :has-folders="hasFolders"
                />
              </transition>
            </div>

            <!-- Footer -->
            <div class="ob-footer">
              <button v-if="isMiddleStep" class="ob-btn ob-btn-ghost" @click="prev">
                <ChevronLeft :size="14" />
                {{ $t('common.back') }}
              </button>
              <div class="ob-footer-spacer" />
              <button v-if="isMiddleStep" class="ob-btn ob-btn-skip" @click="skip">
                {{ $t('onboarding.skip') }}
              </button>
              <button
                v-if="currentStepId !== STEP.DONE"
                class="ob-btn ob-btn-primary"
                :disabled="saving"
                @click="next"
              >
                <span v-if="saving" class="ob-spin" />
                <span v-else>
                  {{
                    currentStepId === STEP.TOUR ? $t('onboarding.finish') : $t('onboarding.next')
                  }}
                </span>
                <ChevronRight v-if="!saving && currentStepId !== STEP.TOUR" :size="14" />
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
import { computed } from 'vue'
import { useOnboarding } from '@/composables/useOnboarding'
import { useOnboardingModules } from '@/composables/useOnboardingModules'
import { ONBOARDING_STEP as STEP } from '@/constants/onboarding'
import ObLocaleStep from './onboarding/ObLocaleStep.vue'
import ObToolStep from './onboarding/ObToolStep.vue'
import ObFoldersStep from './onboarding/ObFoldersStep.vue'
import ObTourStep from './onboarding/ObTourStep.vue'
import ObDoneStep from './onboarding/ObDoneStep.vue'
import { Check, ChevronLeft, ChevronRight, Zap } from 'lucide-vue-next'
import '@/assets/styles/onboarding-wizard.css'

const emit = defineEmits(['done'])

const {
  visible,
  currentStep,
  currentStepId,
  saving,
  tourActive,
  steps,
  zoneRows,
  zoneKey,
  zoneRow,
  zoneSaved,
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
} = useOnboarding(emit)
const { features, modules } = useOnboardingModules()
const isMiddleStep = computed(() => ![STEP.WELCOME, STEP.DONE].includes(currentStepId.value))

defineExpose({ checkAndShow })
</script>
