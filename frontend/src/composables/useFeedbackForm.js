import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi, resolveApiError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { SIDEBAR_SUB_TABS } from '@/constants/sidebarSubTabs'
import {
  FEEDBACK_MAX_CHARS,
  FEEDBACK_PAGES,
  FEEDBACK_RES_CUSTOM,
  FEEDBACK_RES_PRESETS,
} from '@/constants/feedback'
import { locationFromRoute } from '@/utils/feedbackLocation'

// Roughly the fixed block overhead (delimiters + labels + meta line) so the
// counter stays conservative vs the backend's 2000-char truncation.
const OVERHEAD = 170

function detectResolution() {
  const dpr = window.devicePixelRatio || 1
  const w = Math.round((window.screen?.width || 0) * dpr)
  const h = Math.round((window.screen?.height || 0) * dpr)
  if (!w || !h) return { choice: '', custom: '' }
  const value = `${w}x${h}`
  return FEEDBACK_RES_PRESETS.some(r => r.value === value)
    ? { choice: value, custom: '' }
    : { choice: FEEDBACK_RES_CUSTOM, custom: value }
}

/**
 * Bug / suggestion report form behind FeedbackModal: fields, location and
 * resolution pre-fill, character budget and submit. `endpoint` and
 * `showLocation` are getters so the modal's props stay live.
 */
export function useFeedbackForm({ endpoint, showLocation }) {
  const route = useRoute()
  const { t } = useI18n()
  const { apiPost } = useApi()
  const { showToast } = useToast()

  const type = ref('bug')
  const title = ref('')
  const description = ref('')
  const reproduction = ref('')
  const pageRoute = ref('')
  const tabId = ref('')
  const platforms = reactive({ desktop: false, mobile: false })
  const resolutionChoice = ref('')
  const resolutionCustom = ref('')
  const selectedTags = ref(new Set())
  const anonymous = ref(false)
  const busy = ref(false)
  let initialized = false
  let locationPicked = false // page or tab chosen by hand

  const selectedPage = computed(() => FEEDBACK_PAGES.find(p => p.route === pageRoute.value) || null)
  const tabOptions = computed(() => {
    const tp = selectedPage.value?.tabsPath
    return tp ? SIDEBAR_SUB_TABS[tp] || [] : []
  })
  const tabLabel = computed(() => {
    const tab = tabOptions.value.find(tb => tb.id === tabId.value)
    return tab ? t(tab.labelKey) : ''
  })
  const resolution = computed(() =>
    resolutionChoice.value === FEEDBACK_RES_CUSTOM
      ? resolutionCustom.value.trim()
      : resolutionChoice.value,
  )
  const platform = computed(() => {
    if (platforms.desktop && platforms.mobile) return 'both'
    if (platforms.desktop) return 'desktop'
    if (platforms.mobile) return 'mobile'
    return 'both'
  })
  const used = computed(
    () =>
      OVERHEAD +
      title.value.length +
      description.value.length +
      reproduction.value.length +
      resolution.value.length +
      (selectedPage.value?.zone.length || 0) +
      (selectedPage.value?.module.length || 0) +
      tabLabel.value.length +
      [...selectedTags.value].join(', ').length,
  )
  const canSubmit = computed(
    () => !!title.value.trim() && !!description.value.trim() && used.value <= FEEDBACK_MAX_CHARS,
  )
  // Where the admin is now; the portal form has no location.
  const currentLocation = computed(() =>
    showLocation() ? locationFromRoute(route.name, route.query.tab) : null,
  )
  // Offered when the form points away from a page the list knows.
  const canUseCurrentPage = computed(() => {
    const here = currentLocation.value
    return !!here?.pageRoute && (here.pageRoute !== pageRoute.value || here.tabId !== tabId.value)
  })

  // A report in progress keeps its location: typed text or a hand-picked page.
  const hasDraft = () =>
    locationPicked || [title, description, reproduction].some(field => field.value.trim())

  function toggleTag(tag) {
    const next = new Set(selectedTags.value)
    if (next.has(tag)) next.delete(tag)
    else next.add(tag)
    selectedTags.value = next
  }

  function onPageChange() {
    tabId.value = '' // the previous page's active tab no longer applies
    locationPicked = true
  }

  function onTabChange() {
    locationPicked = true
  }

  function refreshLocation() {
    const here = currentLocation.value
    pageRoute.value = here?.pageRoute ?? ''
    tabId.value = here?.tabId ?? ''
    locationPicked = false
  }

  function reset() {
    type.value = 'bug'
    title.value = ''
    description.value = ''
    reproduction.value = ''
    platforms.desktop = false
    platforms.mobile = false
    selectedTags.value = new Set()
    anonymous.value = false
    refreshLocation()
    const r = detectResolution()
    resolutionChoice.value = r.choice
    resolutionCustom.value = r.custom
  }

  // The first open fills everything in; later ones move the location to the
  // current page unless a report is in progress (the rest of the form stays).
  function onOpen() {
    if (!initialized) {
      reset()
      initialized = true
    } else if (!hasDraft()) {
      refreshLocation()
    }
  }

  // `onSent` runs while still busy, so the window can close looking as it was sent.
  async function submit(onSent) {
    if (!canSubmit.value) return
    busy.value = true
    try {
      await apiPost(endpoint(), {
        type: type.value,
        title: title.value.trim(),
        description: description.value.trim(),
        reproduction: reproduction.value.trim(),
        zone: selectedPage.value?.zone || '',
        module: selectedPage.value?.module || '',
        tab: tabLabel.value,
        platform: platform.value,
        resolution: resolution.value,
        tags: [...selectedTags.value],
        anonymous: anonymous.value,
      })
      showToast(t('feedback.modal.sent'), TOAST_TYPE.OK)
      onSent()
    } catch (e) {
      console.error('[useFeedbackForm.submit]', e)
      showToast(resolveApiError(e.message, 'common.apiError.submitFailed'), TOAST_TYPE.ERR)
    } finally {
      busy.value = false
    }
  }

  return {
    type,
    title,
    description,
    reproduction,
    pageRoute,
    tabId,
    platforms,
    resolutionChoice,
    resolutionCustom,
    selectedTags,
    anonymous,
    busy,
    tabOptions,
    used,
    canSubmit,
    canUseCurrentPage,
    toggleTag,
    onPageChange,
    onTabChange,
    refreshLocation,
    reset,
    onOpen,
    submit,
  }
}
