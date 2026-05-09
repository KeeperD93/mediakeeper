<template>
  <Teleport to="body">
    <transition name="pt-force-fade">
      <div v-if="open" class="pt-force-uname-overlay" role="dialog" aria-modal="true">
        <div ref="panelRef" class="pt-force-uname-panel" tabindex="-1">
          <h2 class="pt-force-uname-title">{{ $t('portal.settings.forceUsername.title') }}</h2>
          <p class="pt-force-uname-sub">{{ $t('portal.settings.forceUsername.subtitle') }}</p>

          <label class="pt-settings-label" for="pt-force-uname-input">
            {{ $t('portal.settings.forceUsername.fieldLabel') }}
          </label>

          <div class="pt-settings-uname-row">
            <input
              id="pt-force-uname-input"
              ref="inputRef"
              v-model="candidate"
              class="pt-settings-input"
              maxlength="50"
              autocomplete="off"
              @input="onInput"
            />
            <span v-if="state.flag" class="pt-settings-uname-flag" :class="state.flagClass">
              {{ state.flagText }}
            </span>
          </div>

          <p v-if="errorKey" class="pt-settings-hint pt-force-uname-error">
            {{ $t(errorKey) }}
          </p>

          <div v-if="usernameCheck.suggestions.length" class="pt-settings-uname-suggestions">
            <button
              v-for="s in usernameCheck.suggestions"
              :key="s"
              type="button"
              class="pt-settings-uname-chip"
              @click="pickSuggestion(s)"
            >
              {{ s }}
            </button>
          </div>

          <div class="pt-settings-savebar-actions pt-settings-uname-actions">
            <button
              type="button"
              class="pt-settings-btn pt-settings-btn--primary"
              :disabled="!canSave"
              @click="confirm"
            >
              {{
                saving
                  ? $t('portal.settings.forceUsername.saving')
                  : $t('portal.settings.forceUsername.save')
              }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { useApi } from '@/composables/useApi'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['done'])

const { t } = useI18n()
const { profile, updateProfile } = usePortalAuth()
const { apiGet } = useApi()
const { showToast } = useToast()

const candidate = ref('')
const inputRef = ref(null)
const panelRef = ref(null)
const saving = ref(false)
const errorKey = ref(null)
const usernameCheck = reactive({
  pending: false,
  available: null,
  reason: null,
  suggestions: [],
})

let timer = null

watch(
  () => props.open,
  async open => {
    if (!open) return
    candidate.value = profile.value?.display_name || ''
    errorKey.value = null
    usernameCheck.available = null
    usernameCheck.reason = null
    usernameCheck.suggestions = []
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select()
  },
)

const state = computed(() => {
  const trimmed = candidate.value.trim()
  if (!trimmed) return { flag: false }
  if (usernameCheck.pending) {
    return {
      flag: true,
      flagClass: 'pt-settings-uname-flag--warn',
      flagText: t('portal.settings.forceUsername.checking'),
    }
  }
  if (usernameCheck.reason === 'taken') {
    return {
      flag: true,
      flagClass: 'pt-settings-uname-flag--err',
      flagText: t('portal.settings.forceUsername.taken'),
    }
  }
  if (usernameCheck.available) {
    return {
      flag: true,
      flagClass: 'pt-settings-uname-flag--ok',
      flagText: t('portal.settings.forceUsername.available'),
    }
  }
  return { flag: false }
})

const canSave = computed(() => {
  const trimmed = candidate.value.trim()
  if (saving.value) return false
  if (trimmed.length < 3) return false
  if (usernameCheck.pending) return false
  return usernameCheck.available === true || usernameCheck.reason === 'current'
})

function onInput() {
  errorKey.value = null
  if (timer) clearTimeout(timer)
  const trimmed = candidate.value.trim()
  if (!trimmed) {
    usernameCheck.available = null
    usernameCheck.reason = null
    usernameCheck.suggestions = []
    return
  }
  if (trimmed.length < 3) {
    errorKey.value = 'portal.settings.forceUsername.tooShort'
    usernameCheck.available = false
    usernameCheck.reason = 'invalid'
    usernameCheck.suggestions = []
    return
  }
  usernameCheck.pending = true
  timer = setTimeout(async () => {
    try {
      const res = await apiGet(
        `/api/portal/profiles/me/check-username?name=${encodeURIComponent(trimmed)}`,
      )
      usernameCheck.available = !!res?.available
      usernameCheck.reason = res?.reason || null
      usernameCheck.suggestions = res?.suggestions || []
    } catch {
      usernameCheck.available = null
      usernameCheck.reason = 'error'
    } finally {
      usernameCheck.pending = false
    }
  }, 300)
}

function pickSuggestion(s) {
  candidate.value = s
  onInput()
}

async function confirm() {
  if (!canSave.value) return
  saving.value = true
  errorKey.value = null
  try {
    await updateProfile({ display_name: candidate.value.trim() })
    showToast(t('portal.settings.save.saved'), TOAST_TYPE.OK)
    emit('done')
  } catch (err) {
    const detail = err?.data?.detail || err?.message
    if (detail === 'display_name_taken') {
      usernameCheck.available = false
      usernameCheck.reason = 'taken'
      onInput()
    } else {
      errorKey.value = 'portal.settings.save.error'
    }
  } finally {
    saving.value = false
  }
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: inputRef,
})
</script>

<style scoped>
.pt-force-uname-error {
  color: var(--portal-color-error);
}

.pt-settings-uname-actions {
  margin-top: 0.75rem;
}

.pt-force-fade-enter-active,
.pt-force-fade-leave-active {
  transition: opacity var(--portal-dur-base) var(--portal-ease-default);
}
.pt-force-fade-enter-from,
.pt-force-fade-leave-to {
  opacity: 0;
}
</style>
