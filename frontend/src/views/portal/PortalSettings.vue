<template>
  <div :class="['pt-settings', 'mk-page-root', rankTier ? `gc--${rankTier}` : '']">
    <!-- Until the profile-full payload resolves the rank tier is unknown, so
         the whole-page accent (tabs, save button, title gradient, hero card)
         would paint in the default premium hue then snap to the real tier — a
         visible colour flash. Mirror the profile dashboard: hold a neutral
         loader until `loading` clears (rankTier is set by then) so the page
         renders once, straight into the correct tier. -->
    <div v-if="loading" class="dp-loading pt-settings-loading">
      <MkSpinner size="sm" inline />
      {{ $t('common.loading') }}
    </div>

    <div v-else class="dp-reveal-item dp-reveal-item--d0">
      <SettingsHero
        :profile-data="profileData"
        :live-preview="livePreview"
        :rank-tier="rankTier"
        :title-key="titleKey"
        :title-tier-name="titleTierName"
        :ranking="ranking"
        :member-since="memberSince"
        :xp-percent="xpPercent"
        :next-level-xp="nextLevelXp"
        :trophies="displayTrophies"
        :icon-map="ICON_MAP"
        :streak-days="streakDays"
      />
    </div>

    <section v-if="!loading" class="pt-settings-body">
      <header class="pt-settings-header dp-reveal-item dp-reveal-item--d1">
        <h1 class="pt-settings-h1">{{ $t('portal.settings.title') }}</h1>
        <p class="pt-settings-sub">{{ $t('portal.settings.subtitle') }}</p>
      </header>

      <nav class="pt-settings-tabs dp-reveal-item dp-reveal-item--d2" role="tablist">
        <button
          v-for="tab in TABS"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.id"
          class="pt-settings-tab"
          :class="{ 'pt-settings-tab--active': activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ $t(tab.labelKey) }}
        </button>
      </nav>

      <div :key="activeTab" class="dp-reveal-item dp-reveal-item--d3">
        <SettingsTabIdentity
          v-if="activeTab === 'identity'"
          :form="form"
          :profile-data="profileData"
          :username-state="usernameState"
          :username-check="usernameCheck"
          :upload-avatar="uploadAvatar"
          :delete-custom-avatar="deleteCustomAvatar"
          :check-username="checkUsername"
          @update-field="updateField"
          @avatar-changed="onAvatarChanged"
        />
        <SettingsTabAppearance
          v-else-if="activeTab === 'appearance'"
          :form="form"
          :available-titles="availableTitles"
          :available-avatar-effects="availableAvatarEffects"
          :title-catalogue="titleCatalogue"
          @update-field="updateField"
        />
        <SettingsTabPreferences
          v-else-if="activeTab === 'preferences'"
          :form="form"
          @update-field="updateField"
        />
        <SettingsTabVisibility
          v-else-if="activeTab === 'visibility'"
          :form="form"
          :profile-data="profileData"
          @update-field="updateField"
        />
        <SettingsTabAccount
          v-else-if="activeTab === 'account'"
          :profile-data="profileData"
          :emby-url="embyUrl"
        />
        <PrivacyTab v-else-if="activeTab === 'privacy'" />
      </div>

      <footer
        class="pt-settings-savebar dp-reveal-item dp-reveal-item--d4"
        :class="{ 'pt-settings-savebar--dirty': dirty }"
      >
        <span class="pt-settings-savebar-status" :class="statusClass">
          {{ statusLabel }}
        </span>
        <div class="pt-settings-savebar-actions">
          <button
            type="button"
            class="pt-settings-btn"
            :disabled="!dirty || saving"
            @click="discard"
          >
            {{ $t('portal.settings.save.discardBtn') }}
          </button>
          <button
            type="button"
            class="pt-settings-btn pt-settings-btn--primary"
            :disabled="!dirty || saving"
            @click="onSave"
          >
            {{ saving ? $t('portal.settings.save.saving') : $t('portal.settings.save.saveBtn') }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { usePortalSettings } from '@/composables/portal/usePortalSettings'
import { useSettingsTabHash } from '@/composables/portal/useSettingsTabHash'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useProfileData } from '@/composables/portal/useProfileData'
import { useProfileXp } from '@/composables/portal/useProfileXp'
import { useTrophyDisplay } from '@/composables/portal/useTrophyDisplay'
import { ICON_MAP } from '@/utils/portal/iconMap'

import SettingsHero from '@/components/portal/settings/SettingsHero.vue'
import SettingsTabIdentity from '@/components/portal/settings/SettingsTabIdentity.vue'
import SettingsTabAppearance from '@/components/portal/settings/SettingsTabAppearance.vue'
import SettingsTabPreferences from '@/components/portal/settings/SettingsTabPreferences.vue'
import SettingsTabVisibility from '@/components/portal/settings/SettingsTabVisibility.vue'
import SettingsTabAccount from '@/components/portal/settings/SettingsTabAccount.vue'
import PrivacyTab from '@/components/portal/settings/PrivacyTab.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'

import '@/assets/styles/portal/settings-premium.css'

const ALL_TABS = [
  { id: 'identity', labelKey: 'portal.settings.tabs.identity' },
  { id: 'appearance', labelKey: 'portal.settings.tabs.appearance' },
  { id: 'preferences', labelKey: 'portal.settings.tabs.preferences' },
  { id: 'visibility', labelKey: 'portal.settings.tabs.visibility' },
  { id: 'account', labelKey: 'portal.settings.tabs.account' },
  // Privacy is opt-in: only surfaces when the admin has enabled the
  // GDPR mode. Filtered out of TABS below otherwise.
  { id: 'privacy', labelKey: 'portal.settings.tabs.privacy', gdprOnly: true },
]

const { t } = useI18n()
const { showToast } = useToast()
const { apiGet } = useApi()
const { profile: profileData, gdpr, setPortalAuth } = usePortalAuth()
const route = useRoute()
const router = useRouter()

const TABS = computed(() => ALL_TABS.filter(tab => !tab.gdprOnly || gdpr.value?.enabled))
const visibleTabIds = computed(() => TABS.value.map(tab => tab.id))
const {
  form,
  dirty,
  saving,
  lastSaveError,
  usernameState,
  usernameCheck,
  fetchUsernameState,
  checkUsername,
  save,
  discard,
  uploadAvatar,
  deleteCustomAvatar,
} = usePortalSettings()

const { loading, stats, ranking, titleKey, rankTier, trophies, load } = useProfileData()
const { titleTierName, memberSince, xpPercent, nextLevelXp } = useProfileXp(profileData, stats)
const { displayTrophies } = useTrophyDisplay(trophies, profileData)

const { activeTab } = useSettingsTabHash(route, router, visibleTabIds)
const availableTitles = ref([])
const availableAvatarEffects = ref([])
const titleCatalogue = ref([])
const embyUrl = ref('')

const livePreview = computed(() => ({
  display_name: form.display_name,
  selected_title: form.selected_title,
  avatar_effect: form.avatar_effect,
  selected_badges: form.selected_badges || profileData.value?.selected_badges,
}))

const streakDays = computed(() => stats.value?.streak || 0)

const statusClass = computed(() => {
  if (lastSaveError.value) return 'pt-settings-savebar-status--err'
  if (dirty.value) return 'pt-settings-savebar-status--dirty'
  return 'pt-settings-savebar-status--ok'
})

const statusLabel = computed(() => {
  if (lastSaveError.value) return t('portal.settings.save.error')
  if (saving.value) return t('portal.settings.save.saving')
  if (dirty.value) return t('portal.settings.save.dirty')
  return t('portal.settings.save.noChanges')
})

async function onSave() {
  const languageBefore = profileData.value?.language || null
  const res = await save()
  if (res.ok) {
    if (profileData.value?.language && profileData.value.language !== languageBefore) {
      // Portal hero overviews, trending descriptions and discover lists
      // are fetched from TMDB using profile.language. Pages that have
      // already loaded those rows still hold the previous-language
      // strings — reload so every cached row comes back in the new
      // locale at once.
      window.location.reload()
      return
    }
    showToast(t('portal.settings.save.saved'), TOAST_TYPE.OK)
  } else if (res.error === 'display_name_taken') {
    checkUsername(form.display_name)
    showToast(t('portal.settings.identity.usernameTaken'), TOAST_TYPE.ERR)
    activeTab.value = 'identity'
  } else if (res.error === 'display_name_reserved') {
    checkUsername(form.display_name)
    showToast(t('portal.settings.identity.usernameReserved'), TOAST_TYPE.ERR)
    activeTab.value = 'identity'
  } else if (res.error === 'display_name_locked') {
    showToast(
      t('portal.settings.identity.usernameLockedShort', {
        days: usernameState.lock_days || 180,
      }),
      TOAST_TYPE.ERR,
    )
    activeTab.value = 'identity'
  } else {
    showToast(t('portal.settings.save.error'), TOAST_TYPE.ERR)
  }
}

function onAvatarChanged(payload) {
  // The endpoint returns the updated avatar fields; we re-issue the
  // current portal-auth state so every consumer of `profile` rerenders.
  if (!profileData.value || !payload) return
  const merged = {
    ...profileData.value,
    avatar_url: payload.avatar_url,
    avatar_custom_path: payload.avatar_custom_path ?? null,
    avatar_is_custom: !!payload.avatar_custom_path,
  }
  setPortalAuth(merged)
}

function updateField(key, value) {
  form[key] = value
}

watch(
  () => form.display_name,
  (next, prev) => {
    if (next !== prev) checkUsername(next)
  },
)

onMounted(async () => {
  await Promise.all([
    fetchUsernameState(),
    load(),
    apiGet('/api/portal/profiles/me/titles')
      .then(res => {
        if (res?.titles) availableTitles.value = res.titles
        if (res?.catalogue) titleCatalogue.value = res.catalogue
      })
      .catch(() => {}),
    apiGet('/api/portal/profiles/me/avatar-effects')
      .then(res => {
        if (res?.effects) availableAvatarEffects.value = res.effects
      })
      .catch(() => {}),
  ])
})
</script>

<style scoped>
.pt-settings-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.pt-settings-h1 {
  margin: 0;
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-extrabold);
  color: var(--portal-text-primary);
  font-family: var(--portal-font-display, inherit);
}

.pt-settings-sub {
  margin: 0;
  font-size: var(--portal-text-sm);
  color: var(--portal-text-secondary);
}

.pt-settings-loading {
  /* Span both grid columns so the loader sits centred across the full page
     instead of being squeezed into the 320px hero column. */
  grid-column: 1 / -1;
}
</style>
