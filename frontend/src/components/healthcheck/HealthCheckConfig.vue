<template>
  <div class="hc-config">
    <p class="hc-config-intro">{{ $t('healthCheck.config.intro') }}</p>

    <div class="hc-rules-grid">
      <div v-for="rule in configRules" :key="rule.key" class="glass-card hc-rule-card">
        <div class="hc-rule-header">
          <label class="hc-rule-toggle">
            <input
              v-model="config[rule.key + '_enabled']"
              type="checkbox"
              @change="configDirty = true"
            />
            <span class="hc-toggle-track"><span class="hc-toggle-thumb" /></span>
          </label>
          <div class="hc-rule-title-wrap">
            <span class="hc-rule-title">{{ $t('healthCheck.issues.' + rule.issueType) }}</span>
            <span class="hc-rule-severity" :class="'hc-rs-' + rule.severity">
              {{ $t('healthCheck.' + rule.severity) }}
            </span>
          </div>
        </div>
        <p class="hc-rule-desc">{{ $t('healthCheck.explanations.' + rule.issueType) }}</p>
        <div v-if="rule.threshold" class="hc-rule-threshold">
          <label class="hc-threshold-label">
            {{ $t('healthCheck.config.' + rule.threshold.label) }}
          </label>
          <template v-if="rule.threshold.freeInput">
            <div class="hc-threshold-free">
              <input
                v-model.number="config[rule.threshold.key]"
                type="number"
                :min="rule.threshold.min || 1"
                :max="rule.threshold.max || 9999"
                class="hc-input-num"
                @change="configDirty = true"
              />
              <span class="hc-threshold-unit">{{ rule.threshold.unit }}</span>
            </div>
          </template>
          <select
            v-else
            v-model.number="config[rule.threshold.key]"
            class="hc-select mk-select-chevron hc-select-sm"
            @change="configDirty = true"
          >
            <option v-for="opt in rule.threshold.options" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div class="hc-config-actions">
      <button class="hc-save-btn" :disabled="!configDirty || configSaving" @click="saveConfig">
        <span v-if="configSaving" class="mk-spin hc-save-spin" />
        {{ $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

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
</script>

<style scoped>
.hc-config-intro {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 20px;
  line-height: var(--lh-normal);
}
.hc-rules-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 900px;
}
.hc-rule-card {
  padding: 16px 20px;
}
.hc-rule-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.hc-rule-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
}
.hc-rule-toggle input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.hc-toggle-track {
  width: 36px;
  height: 20px;
  border-radius: var(--radius-pill);
  background: var(--surface-3);
  transition: background var(--duration-base);
  position: relative;
}
.hc-toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all var(--duration-base);
}
.hc-rule-toggle input:checked + .hc-toggle-track {
  background: var(--accent-500);
}
.hc-rule-toggle input:checked + .hc-toggle-track .hc-toggle-thumb {
  transform: translateX(16px);
  background: #fff;
}

.hc-rule-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.hc-rule-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.hc-rule-severity {
  font-size: var(--text-3xs);
  padding: 2px 7px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-weight: var(--font-medium);
}
.hc-rs-critical {
  background: rgb(244, 63, 94, 0.12);
  color: #fb7185;
}
.hc-rs-warning {
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
}
.hc-rs-info {
  background: rgb(var(--color-info-rgb), 0.12);
  color: var(--color-info);
}

.hc-rule-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.45;
  margin: 0 0 8px;
}
.hc-rule-threshold {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.hc-threshold-label {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.hc-select {
  background: var(--mk-chrome-bg);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-input);
  padding: 6px 28px 6px 10px;
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--duration-fast);
}
.hc-select:hover {
  border-color: var(--border-hover);
}
.hc-select:focus {
  border-color: var(--accent-500);
}
.hc-select option {
  background: var(--mk-chrome-bg);
  color: var(--text-primary);
}
.hc-select-sm {
  padding: 5px 26px 5px 8px;
  font-size: var(--text-2xs);
}
.hc-input-num {
  width: 80px;
  padding: 5px 8px;
  font-size: var(--text-2xs);
  font-family: inherit;
  background: var(--mk-chrome-bg);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--duration-fast);
  -moz-appearance: textfield;
}
.hc-input-num::-webkit-outer-spin-button,
.hc-input-num::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.hc-input-num:hover {
  border-color: var(--border-hover);
}
.hc-input-num:focus {
  border-color: var(--accent-500);
}

.hc-config-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}
.hc-save-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 22px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  background: rgb(var(--accent-rgb), 0.18);
  color: var(--accent-400);
  border: 0.5px solid rgb(var(--accent-rgb), 0.3);
  cursor: pointer;
  transition: all var(--duration-fast);
  font-family: inherit;
}
.hc-save-btn:hover:not(:disabled) {
  background: rgb(var(--accent-rgb), 0.28);
}
.hc-save-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.hc-threshold-free {
  display: flex;
  align-items: center;
  gap: 6px;
}
.hc-threshold-unit {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.hc-save-spin {
  width: 14px;
  height: 14px;
}
</style>
