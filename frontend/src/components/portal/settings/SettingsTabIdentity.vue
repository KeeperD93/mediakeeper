<template>
  <div class="pt-settings-card">
    <h3 class="pt-settings-section-title">{{ $t('portal.settings.identity.section') }}</h3>

    <!-- Avatar — reuses SideRankCard structure for tier ring + FX. -->
    <div class="pt-settings-avatar-block">
      <div class="pt-settings-avatar-preview gc-avatar-zone" :class="avatarFxClass">
        <template v-if="avatarFxKey === 'dedication'">
          <div class="gc-fx-comet-core" />
          <div class="gc-fx-comet-trail" />
          <div class="gc-fx-comet-head" />
        </template>
        <template v-else-if="avatarFxKey === 'special'">
          <div class="gc-fx-holy-rays" />
          <div class="gc-fx-holy-glow" />
          <div class="gc-fx-holy-ring" />
          <div class="gc-fx-rune" /><div class="gc-fx-rune" />
          <div class="gc-fx-rune" /><div class="gc-fx-rune" />
        </template>
        <template v-else-if="avatarFxKey === 'community'">
          <div class="gc-fx-nebula" />
          <span v-for="i in 8" :key="'cstar'+i" class="gc-fx-star" />
        </template>
        <template v-else-if="avatarFxKey === 'ranking'">
          <div v-for="i in 5" :key="'rhalo'+i" class="gc-fx-rhalo" :class="`gc-fx-rhalo--${i}`" />
        </template>
        <template v-else-if="avatarFxKey === 'meta'">
          <div class="gc-fx-mandala gc-fx-mandala--dots" />
          <div class="gc-fx-mandala gc-fx-mandala--outer" />
          <div class="gc-fx-mandala gc-fx-mandala--mid" />
          <div class="gc-fx-mandala gc-fx-mandala--inner" />
        </template>

        <div class="gc-avatar-ring">
          <div class="gc-avatar-inner">
            <img
              v-if="avatarPreviewUrl"
              :src="avatarPreviewUrl"
              :alt="form.display_name"
              class="gc-avatar-img"
            />
            <span v-else class="gc-avatar-letter">
              {{ (form.display_name || '?').charAt(0).toUpperCase() }}
            </span>
          </div>
        </div>

        <template v-if="avatarFxKey === 'ranking'">
          <div v-for="i in 5" :key="'rstar'+i" class="gc-fx-rstar" :class="`gc-fx-rstar--${i}`" />
        </template>
      </div>
      <div class="pt-settings-avatar-actions">
        <span class="pt-settings-hint">
          {{ profileData?.avatar_is_custom
              ? $t('portal.settings.identity.avatarOverride')
              : $t('portal.settings.identity.avatarEmby') }}
        </span>
        <div class="pt-settings-avatar-buttons">
          <button
            type="button"
            class="pt-settings-btn"
            :disabled="uploading"
            @click="triggerFile"
          >
            <Upload :size="14" />
            {{ profileData?.avatar_is_custom
                ? $t('portal.settings.identity.avatarReplace')
                : $t('portal.settings.identity.avatarUpload') }}
          </button>
          <button
            v-if="profileData?.avatar_is_custom"
            type="button"
            class="pt-settings-btn pt-settings-btn--danger"
            :disabled="uploading"
            @click="onDelete"
          >
            <Trash2 :size="14" />
            {{ $t('portal.settings.identity.avatarRemove') }}
          </button>
        </div>
        <p class="pt-settings-hint">{{ $t('portal.settings.identity.avatarHint') }}</p>
        <input
          ref="fileRef"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          class="pt-settings-file-input"
          @change="onFile"
        />
      </div>
    </div>

    <!-- ─── Username ──────────────────────────────────────────── -->
    <div class="pt-settings-row">
      <label class="pt-settings-label" for="pt-set-username">
        {{ $t('portal.settings.identity.usernameLabel') }}
      </label>
      <div class="pt-settings-uname-row">
        <input
          id="pt-set-username"
          :value="form.display_name"
          class="pt-settings-input"
          maxlength="50"
          autocomplete="off"
          :disabled="usernameLockedHard"
          @input="onUsernameInput($event.target.value)"
        />
        <span v-if="unameFlag.show" class="pt-settings-uname-flag" :class="unameFlag.cls">
          {{ unameFlag.text }}
        </span>
      </div>

      <p v-if="usernameLockedHard" class="pt-settings-hint">
        {{ $t('portal.settings.identity.usernameLocked', { date: lockedUntilFormatted }) }}
      </p>
      <p v-else class="pt-settings-hint">
        {{ $t('portal.settings.identity.usernameHint') }}
      </p>

      <div
        v-if="usernameCheck.suggestions.length"
        class="pt-settings-uname-suggestions"
      >
        <span class="pt-settings-hint">
          {{ $t('portal.settings.identity.usernameTakenSuggestion') }}
        </span>
        <button
          v-for="s in usernameCheck.suggestions"
          :key="s"
          type="button"
          class="pt-settings-uname-chip"
          @click="pickSuggestion(s)"
        >{{ s }}</button>
      </div>
    </div>

    <!-- ─── Bio ───────────────────────────────────────────────── -->
    <div class="pt-settings-row">
      <label class="pt-settings-label" for="pt-set-bio">
        {{ $t('portal.settings.identity.bioLabel') }}
      </label>
      <textarea
        id="pt-set-bio"
        :value="form.bio"
        class="pt-settings-textarea"
        :placeholder="$t('portal.settings.identity.bioPlaceholder')"
        maxlength="500"
        rows="4"
        @input="updateField('bio', $event.target.value)"
      />
      <span class="pt-settings-counter">
        {{ $t('portal.settings.identity.bioCounter', {
          used: (form.bio || '').length, max: 500
        }) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2, Upload } from 'lucide-vue-next'

import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const props = defineProps({
  form: { type: Object, required: true },
  profileData: { type: Object, default: null },
  usernameState: { type: Object, default: () => ({}) },
  usernameCheck: { type: Object, default: () => ({}) },
  uploadAvatar: { type: Function, required: true },
  deleteCustomAvatar: { type: Function, required: true },
  checkUsername: { type: Function, required: true },
})
const emit = defineEmits(['avatar-changed', 'update-field'])

const { t, locale } = useI18n()
const { showToast } = useToast()

const fileRef = ref(null)
const uploading = ref(false)
const lastUploadedUrl = ref(null)

const VALID_AVATAR_FX = new Set(['watching', 'dedication', 'diversity', 'special', 'community', 'ranking', 'meta'])
const avatarFxKey = computed(() => {
  const raw = props.form?.avatar_effect ?? props.profileData?.avatar_effect
  return VALID_AVATAR_FX.has(raw) ? raw : null
})
const avatarFxClass = computed(() => avatarFxKey.value ? `gc-avatar-fx--${avatarFxKey.value}` : '')

const usernameLockedHard = computed(() => {
  return !!props.usernameState?.locked && !props.usernameState?.must_set
})

const lockedUntilFormatted = computed(() => {
  const iso = props.usernameState?.locked_until
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(locale.value, {
      year: 'numeric', month: 'long', day: 'numeric',
    })
  } catch {
    return ''
  }
})

const avatarPreviewUrl = computed(() => {
  return lastUploadedUrl.value || props.profileData?.avatar_url || null
})

const unameFlag = computed(() => {
  const c = props.usernameCheck
  if (!c.reason) return { show: false }
  if (c.pending) {
    return { show: true, cls: 'pt-settings-uname-flag--warn',
      text: t('portal.settings.forceUsername.checking') }
  }
  if (c.reason === 'current') {
    return { show: true, cls: 'pt-settings-uname-flag--warn',
      text: t('portal.settings.identity.usernameCurrent') }
  }
  if (c.reason === 'free') {
    return { show: true, cls: 'pt-settings-uname-flag--ok',
      text: t('portal.settings.identity.usernameAvailable') }
  }
  if (c.reason === 'taken') {
    return { show: true, cls: 'pt-settings-uname-flag--err',
      text: t('portal.settings.identity.usernameTaken') }
  }
  if (c.reason === 'reserved') {
    return { show: true, cls: 'pt-settings-uname-flag--err',
      text: t('portal.settings.identity.usernameReserved') }
  }
  if (c.reason === 'locked') {
    return { show: true, cls: 'pt-settings-uname-flag--err',
      text: t('portal.settings.identity.usernameLockedShort', {
        days: props.usernameState?.lock_days || 180,
      }) }
  }
  return { show: false }
})

function updateField(key, value) {
  emit('update-field', key, value)
}

function onUsernameInput(value) {
  updateField('display_name', value)
  props.checkUsername(value)
}

function pickSuggestion(s) {
  updateField('display_name', s)
  props.checkUsername(s)
}

function triggerFile() { fileRef.value?.click() }

async function onFile(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await props.uploadAvatar(file)
    if (res?.avatar_url) {
      lastUploadedUrl.value = res.avatar_url
      emit('avatar-changed', res)
      showToast(t('portal.settings.save.saved'), TOAST_TYPE.OK)
    }
  } catch (err) {
    const detail = err?.data?.detail
    if (detail === 'avatar_too_large') showToast(t('portal.settings.identity.avatarTooLarge'), TOAST_TYPE.ERR)
    else if (detail?.startsWith('avatar_')) showToast(t('portal.settings.identity.avatarBadFormat'), TOAST_TYPE.ERR)
    else showToast(t('portal.settings.save.error'), TOAST_TYPE.ERR)
  } finally {
    uploading.value = false
    if (fileRef.value) fileRef.value.value = ''
  }
}

async function onDelete() {
  uploading.value = true
  try {
    const res = await props.deleteCustomAvatar()
    lastUploadedUrl.value = null
    emit('avatar-changed', res)
    showToast(t('portal.settings.save.saved'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.settings.save.error'), TOAST_TYPE.ERR)
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.pt-settings-file-input { display: none; }
</style>
