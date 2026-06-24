import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

/**
 * Health-check rule configuration: the reactive form state, the static
 * rule catalogue and the load / save round-trip. Extracted from
 * HealthCheckConfig.vue so the component stays a presentation layer.
 */
export function useHealthCheckConfig() {
  const { t } = useI18n()
  const { apiGet, apiPut } = useApi()
  const { showToast } = useToast()

  const config = reactive({
    obsolete_codecs_enabled: true,
    obsolete_containers_enabled: true,
    low_resolution_enabled: true,
    min_resolution_height: 720,
    low_bitrate_enabled: true,
    min_video_bitrate_kbps: 1000,
    no_audio_enabled: true,
    large_file_enabled: true,
    max_file_size_gb: 50,
    hdr_no_sdr_enabled: true,
  })
  const configDirty = ref(false)
  const configSaving = ref(false)

  const configRules = [
    { key: 'no_audio', issueType: 'no_audio', severity: 'critical', threshold: null },
    { key: 'obsolete_codecs', issueType: 'obsolete_codec', severity: 'warning', threshold: null },
    {
      key: 'obsolete_containers',
      issueType: 'obsolete_container',
      severity: 'warning',
      threshold: null,
    },
    {
      key: 'low_bitrate',
      issueType: 'low_bitrate',
      severity: 'warning',
      threshold: {
        key: 'min_video_bitrate_kbps',
        label: 'minBitrate',
        options: [
          { value: 500, label: '500 kbps' },
          { value: 750, label: '750 kbps' },
          { value: 1000, label: '1 000 kbps' },
          { value: 1500, label: '1 500 kbps' },
          { value: 2000, label: '2 000 kbps' },
          { value: 3000, label: '3 000 kbps' },
        ],
      },
    },
    {
      key: 'low_resolution',
      issueType: 'low_resolution',
      severity: 'info',
      threshold: {
        key: 'min_resolution_height',
        label: 'minResolution',
        options: [
          { value: 480, label: '480p (SD)' },
          { value: 720, label: '720p (HD)' },
          { value: 1080, label: '1080p (Full HD)' },
          { value: 2160, label: '2160p (4K)' },
        ],
      },
    },
    {
      key: 'large_file',
      issueType: 'large_file',
      severity: 'info',
      threshold: {
        key: 'max_file_size_gb',
        label: 'maxFileSize',
        freeInput: true,
        unit: 'Go',
        min: 1,
        max: 500,
      },
    },
    { key: 'hdr_no_sdr', issueType: 'hdr_no_sdr', severity: 'info', threshold: null },
  ]

  async function loadConfig() {
    try {
      const d = await apiGet('/api/healthcheck/config')
      if (d) Object.assign(config, d)
    } catch {
      /* silent: config load, defaults apply */
    }
  }

  async function saveConfig() {
    configSaving.value = true
    // Send only the schema-known keys to satisfy `extra="forbid"` (a legacy DB
    // row could surface unknown keys via `Object.assign(config, d)` in loadConfig),
    // and coerce numerics so a cleared free-input doesn't ship NaN/null.
    const payload = {
      obsolete_codecs_enabled: !!config.obsolete_codecs_enabled,
      obsolete_containers_enabled: !!config.obsolete_containers_enabled,
      low_resolution_enabled: !!config.low_resolution_enabled,
      min_resolution_height: Number(config.min_resolution_height) || 720,
      low_bitrate_enabled: !!config.low_bitrate_enabled,
      min_video_bitrate_kbps: Number(config.min_video_bitrate_kbps) || 1000,
      no_audio_enabled: !!config.no_audio_enabled,
      large_file_enabled: !!config.large_file_enabled,
      max_file_size_gb: Number(config.max_file_size_gb) || 50,
      hdr_no_sdr_enabled: !!config.hdr_no_sdr_enabled,
    }
    try {
      await apiPut('/api/healthcheck/config', payload)
      configDirty.value = false
      showToast(t('healthCheck.config.saved'), TOAST_TYPE.OK)
    } catch (e) {
      console.error('[HealthCheckConfig.saveConfig] failed to save config', e)
      showToast(t('common.apiError.saveFailed'), TOAST_TYPE.ERR)
    }
    configSaving.value = false
  }

  onMounted(loadConfig)

  return { config, configDirty, configSaving, configRules, saveConfig }
}
