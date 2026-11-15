/**
 * What the first-login wizard writes, all at the end: the choices in one request,
 * then the picked image. The wizard stays open until the choices are saved; a name
 * refused meanwhile sends the person back to it, any other failure can be retried.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { refusedNameReason } from '@/constants/displayName'
import { TOAST_TYPE } from '@/constants/toast'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'

const NO_ANSWER = 'no_answer'

/**
 * @param {object} options
 * @param {() => object} options.payload body of the onboarding save
 * @param {() => File|null} options.avatarFile image to send after it, if any
 * @param {(reason: string) => void} options.onNameRefused the save refused the name
 * @param {() => void} options.onDone everything that had to be saved is
 */
export function useOnboardingSave({ payload, avatarFile, onNameRefused, onDone }) {
  const { t } = useI18n()
  const { apiPost, apiPut, apiFetch } = useApi()
  const { replaceProfile } = usePortalAuth()
  const { showToast } = useToast()
  const saving = ref(false)
  const failed = ref(false)

  // `task` resolves to the saved profile. The page hears « done » before the profile
  // changes: the new profile closes the wizard, which can no longer speak once gone.
  async function run(task) {
    if (saving.value) return
    saving.value = true
    failed.value = false
    try {
      const saved = await task()
      onDone()
      replaceProfile(saved)
    } catch (err) {
      const reason = refusedNameReason(err?.message)
      if (reason) onNameRefused(reason)
      else failed.value = true
    } finally {
      saving.value = false
    }
  }

  async function withAvatar(saved) {
    const file = avatarFile()
    if (!file) return saved
    try {
      const data = new FormData()
      data.append('file', file)
      const res = await apiFetch('/api/portal/profiles/me/avatar', { method: 'POST', body: data })
      const body = res ? await res.json() : null
      if (!body) throw new Error(NO_ANSWER)
      return { ...saved, avatar_url: body.avatar_url, avatar_is_custom: true }
    } catch {
      // The choices are saved: the wizard ends, the image is for Settings.
      showToast(t('portal.wizard.avatar.uploadFailed'), TOAST_TYPE.WARN)
      return saved
    }
  }

  /** The whole tour: choices, then the image; the profile is replaced once both are done. */
  const saveAll = () =>
    run(async () => {
      const saved = await apiPost('/api/portal/profiles/me/onboarding', payload())
      if (!saved) throw new Error(NO_ANSWER)
      return withAvatar(saved)
    })

  /** The name alone, as the reset asks: the same save as the settings page. */
  const saveName = () =>
    run(async () => {
      const saved = await apiPut('/api/portal/profiles/me', {
        display_name: payload().display_name,
      })
      if (!saved) throw new Error(NO_ANSWER)
      return saved
    })

  return { saving, failed, saveAll, saveName }
}
