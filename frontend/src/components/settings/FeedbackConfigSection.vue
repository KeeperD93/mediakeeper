<template>
  <section class="params-section">
    <h3 class="params-section-title">{{ $t('feedback.config.title') }}</h3>
    <p class="params-section-desc">{{ $t('feedback.config.desc') }}</p>

    <div v-if="loading" class="fbc-skel" />
    <div v-else class="params-cards">
      <div class="fbc" :class="{ active: config?.enabled }">
        <div class="fbc-header" @click="open = !open">
          <div class="fbc-header-left">
            <IconDiscord class="fbc-icon" />
            <span class="fbc-label">{{ $t('feedback.config.channel') }}</span>
          </div>
          <div class="fbc-header-right" @click.stop>
            <span class="fbc-status" :class="config?.enabled ? 'on' : 'off'">
              {{ config?.enabled ? $t('common.active') : $t('common.inactive') }}
            </span>
            <label class="fbc-switch">
              <input
                type="checkbox"
                :checked="config?.enabled"
                :disabled="busy"
                @change="onToggle($event.target.checked)"
              />
              <div class="fbc-switch-track" />
            </label>
          </div>
        </div>

        <div v-if="open" class="fbc-body">
          <div class="fbc-field">
            <label class="fbc-field-label" for="fbc-code">
              {{ $t('feedback.config.codeLabel') }}
            </label>
            <input
              id="fbc-code"
              class="fbc-input"
              :type="codeInputType"
              :value="codeDisplay"
              :placeholder="$t('feedback.config.codePlaceholder')"
              autocomplete="off"
              :disabled="busy"
              @focus="onCodeFocus"
              @input="onCodeInput($event.target.value)"
            />
            <p class="fbc-field-help">{{ $t('feedback.config.codeHint') }}</p>
          </div>

          <div class="fbc-field">
            <label class="fbc-field-label" for="fbc-pseudo">
              {{ $t('feedback.config.pseudoLabel') }}
            </label>
            <input
              id="fbc-pseudo"
              v-model="pseudo"
              class="fbc-input"
              type="text"
              maxlength="100"
              :disabled="busy"
            />
            <p class="fbc-field-help">{{ $t('feedback.config.pseudoDesc') }}</p>
          </div>

          <div class="fbc-actions">
            <button class="fbc-save-btn" :disabled="busy" @click="onSave">
              {{ busy ? $t('common.saving') : $t('common.save') }}
            </button>
            <button
              class="fbc-ping-btn"
              :disabled="busy || !config?.webhook_configured"
              @click="onTest"
            >
              {{ $t('feedback.config.test') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import IconDiscord from '@/components/icons/IconDiscord.vue'
import { useFeedbackConfig } from '@/composables/useFeedbackConfig'
import { useToast } from '@/composables/useToast'
import { resolveApiError } from '@/composables/useApi'
import { TOAST_TYPE } from '@/constants/toast'

const { t } = useI18n()
const { showToast } = useToast()
const { config, loadFeedbackConfig, saveFeedbackConfig, testFeedbackLink } = useFeedbackConfig()

// Fixed-length mask — the real code length is never exposed to the browser.
const MASK = '*'.repeat(16)

const loading = ref(true)
const busy = ref(false)
const open = ref(false)
const pseudo = ref('')
const code = ref('') // typed code, empty unless the admin is editing
const codeEditing = ref(false)

const codeConfigured = computed(() => !!config.value?.webhook_configured)
const codeDisplay = computed(() => (codeConfigured.value && !codeEditing.value ? MASK : code.value))
const codeInputType = computed(() =>
  codeConfigured.value && !codeEditing.value ? 'text' : 'password',
)

async function load() {
  loading.value = true
  try {
    await loadFeedbackConfig()
    pseudo.value = config.value?.discord_pseudo || ''
    code.value = ''
    codeEditing.value = false
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    loading.value = false
  }
}

function onCodeFocus() {
  // First focus on a masked field clears it so the admin types a fresh code.
  if (codeConfigured.value && !codeEditing.value) {
    codeEditing.value = true
    code.value = ''
  }
}
function onCodeInput(value) {
  codeEditing.value = true
  code.value = value
}

async function onToggle(value) {
  const previous = config.value?.enabled
  // Optimistic flip so the bound :checked tracks the DOM; on a failed save we
  // revert it — leaving enabled unchanged would strand the switch flipped.
  if (config.value) config.value = { ...config.value, enabled: value }
  busy.value = true
  try {
    await saveFeedbackConfig({ enabled: value })
  } catch (e) {
    if (config.value) config.value = { ...config.value, enabled: previous }
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    busy.value = false
  }
}

async function onSave() {
  busy.value = true
  try {
    const patch = { discord_pseudo: pseudo.value }
    // Only send the code when a new one was typed — an untouched masked field
    // must never overwrite the stored secret.
    if (codeEditing.value && code.value.trim()) patch.webhook_url = code.value.trim()
    await saveFeedbackConfig(patch)
    code.value = ''
    codeEditing.value = false
    showToast(t('feedback.config.saved'), TOAST_TYPE.OK)
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    busy.value = false
  }
}

async function onTest() {
  busy.value = true
  try {
    await testFeedbackLink()
    showToast(t('feedback.config.testSent'), TOAST_TYPE.OK, 5000)
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.fbc-skel {
  height: 46px;
  max-width: 820px;
  border-radius: var(--radius-btn);
  background: var(--bg-secondary);
  opacity: 0.6;
}
.fbc {
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: border-color var(--duration-base);
}
.fbc.active {
  border-color: var(--accent-500);
}
.fbc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.fbc.active .fbc-header {
  background: rgb(var(--accent-rgb), 0.08);
}
.fbc-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fbc-icon {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
}
.fbc-label {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.fbc-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.fbc-status {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.fbc-status.on {
  color: var(--color-success);
}
.fbc-switch {
  position: relative;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 44px;
  min-height: 44px;
}
.fbc-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.fbc-switch-track {
  width: 38px;
  height: 20px;
  border-radius: var(--radius-pill);
  background: var(--bg-primary);
  border: 1px solid var(--border);
  position: relative;
  transition: all var(--duration-base);
}
.fbc-switch-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: var(--radius-circle);
  background: var(--color-on-accent);
  transition: all var(--duration-base);
}
.fbc-switch input:checked + .fbc-switch-track {
  background: var(--accent-500);
  border-color: var(--accent-500);
}
.fbc-switch input:checked + .fbc-switch-track::after {
  left: 21px;
}
.fbc-body {
  padding: 16px;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.fbc-field-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: 5px;
}
.fbc-field-help {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.4;
}
.fbc-input {
  width: 100%;
  min-height: 44px;
  padding: 8px 12px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  outline: none;
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}
.fbc-input:focus {
  border-color: var(--accent-500);
}
.fbc-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.fbc-save-btn {
  min-height: 44px;
  padding: 8px 18px;
  border-radius: var(--radius-btn);
  background: var(--accent-600);
  color: var(--text-primary);
  border: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.fbc-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.fbc-ping-btn {
  min-height: 44px;
  padding: 8px 14px;
  border-radius: var(--radius-btn);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.fbc-ping-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (min-width: 768px) {
  .fbc-input,
  .fbc-save-btn,
  .fbc-ping-btn {
    min-height: 0;
  }
  .fbc-switch {
    min-width: 0;
    min-height: 0;
  }
}

@media (hover: hover) {
  .fbc-header:hover {
    background: var(--bg-secondary);
  }
  .fbc.active .fbc-header:hover {
    background: rgb(var(--accent-rgb), 0.12);
  }
  .fbc-save-btn:hover {
    background: var(--accent-700);
  }
  .fbc-ping-btn:hover:not(:disabled) {
    border-color: var(--accent-500);
    color: var(--text-primary);
  }
}
</style>
