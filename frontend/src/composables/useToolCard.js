import { ref, reactive, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const ATTRIBUTION_TOOLS = ['tmdb', 'opensubtitles']

/**
 * Field / secret-mask handling, the save payload and the connection ping
 * for a settings ToolCard. Extracted from ToolCard.vue so the component
 * stays a presentation layer; takes the component's props + emit.
 */
export function useToolCard(props, emit) {
  const { t } = useI18n()
  const { apiGet } = useApi()

  const open = ref(false)
  const saving = ref(false)
  const pinging = ref(false)
  const pingResult = ref(null)

  const hasAttributionNote = computed(() => ATTRIBUTION_TOOLS.includes(props.toolKey))
  const attributionNoteText = computed(() =>
    props.toolKey === 'tmdb'
      ? t('attribution.settings.tmdb')
      : t('attribution.settings.opensubtitles'),
  )

  const fieldValues = reactive({})
  const secretEditing = reactive({})

  function isSecretField(field) {
    return field?.type === 'password' || field?.key === 'api_key' || field?.key === 'password'
  }

  function secretMask(field) {
    const configured = props.cfg?.[`${field.key}_configured`]
    const length = Number(props.cfg?.[`${field.key}_length`]) || 0
    if (!configured) return ''
    return '*'.repeat(Math.max(1, length))
  }

  function fieldPlaceholder(field) {
    return field.placeholder || ''
  }

  function displayValue(field) {
    if (!isSecretField(field)) return fieldValues[field.key] || ''
    if (secretEditing[field.key] || !props.cfg?.[`${field.key}_configured`])
      return fieldValues[field.key] || ''
    return secretMask(field)
  }

  function inputType(field) {
    if (!isSecretField(field)) return 'text'
    return props.cfg?.[`${field.key}_configured`] && !secretEditing[field.key] ? 'text' : 'password'
  }

  function onFieldFocus(field) {
    if (!isSecretField(field)) return
    if (props.cfg?.[`${field.key}_configured`] && !secretEditing[field.key]) {
      secretEditing[field.key] = true
      fieldValues[field.key] = ''
    }
  }

  function onFieldInput(field, value) {
    if (isSecretField(field)) secretEditing[field.key] = true
    fieldValues[field.key] = value
  }

  // Init field values from config
  function syncFields() {
    for (const f of props.def.fields || []) {
      fieldValues[f.key] = props.cfg[f.key] || ''
      if (isSecretField(f)) secretEditing[f.key] = false
    }
  }
  syncFields()
  watch(() => props.cfg, syncFields, { deep: true })

  function save() {
    saving.value = true
    const payload = {}
    for (const f of props.def.fields || []) {
      const value = (fieldValues[f.key] || '').trim()
      if (
        isSecretField(f) &&
        props.cfg?.[`${f.key}_configured`] &&
        (!secretEditing[f.key] || !value)
      )
        continue
      payload[f.key] = value
    }
    emit('save', payload)
    setTimeout(() => {
      saving.value = false
      open.value = false
    }, 600)
  }

  async function ping() {
    pinging.value = true
    pingResult.value = null
    try {
      const data = await apiGet(`/api/settings/tools/${props.toolKey}/ping`)
      if (data?.ok) pingResult.value = t('settings.connected')
      else pingResult.value = t('settings.connectionFailed')
    } catch {
      pingResult.value = '✗ ' + t('common.error')
    }
    pinging.value = false
    setTimeout(() => {
      pingResult.value = null
    }, 4000)
  }

  return {
    open,
    saving,
    pinging,
    pingResult,
    hasAttributionNote,
    attributionNoteText,
    fieldPlaceholder,
    displayValue,
    inputType,
    onFieldFocus,
    onFieldInput,
    save,
    ping,
  }
}
