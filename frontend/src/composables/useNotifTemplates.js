import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { buildTplGroups, buildTestTypes } from './notif-templates/groups'
import { getActiveTplVars as getActiveTplVarsRaw } from './notif-templates/vars'
import {
  defaultTpl as defaultTplRaw,
  defaultColor as defaultColorRaw,
} from './notif-templates/defaults'
import { renderPreview as renderPreviewRaw } from './notif-templates/preview-renderer'

export function useNotifTemplates() {
  const { t, locale } = useI18n()
  const { apiGet } = useApi()
  const tplMeta = ref({})

  const TPL_GROUPS = buildTplGroups(t)
  const testTypes = buildTestTypes(TPL_GROUPS)

  const getActiveTplVars = key => getActiveTplVarsRaw(tplMeta.value, key)
  const defaultTpl = key => defaultTplRaw(tplMeta.value, locale.value, key)
  const defaultColor = key => defaultColorRaw(tplMeta.value, key)
  const renderPreview = (tpl, key, imageStyle) =>
    renderPreviewRaw(tpl, key, imageStyle, tplMeta.value, locale.value)

  async function loadMeta() {
    try {
      const d = await apiGet(`/api/notifications/discord/meta?lang=${locale.value}`)
      if (d) tplMeta.value = d
    } catch {
      /* silent: meta fetch, defaults apply */
    }
  }
  watch(locale, () => {
    loadMeta()
  })

  return {
    tplMeta,
    TPL_GROUPS,
    testTypes,
    getActiveTplVars,
    defaultTpl,
    defaultColor,
    renderPreview,
    loadMeta,
  }
}
