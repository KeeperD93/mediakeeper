<template>
  <div class="params-security">
    <section class="sec-block">
      <header class="sec-hd">
        <h3>{{ t('settings.passwordTitle') }}</h3>
      </header>
      <p class="sec-desc">{{ t('settings.passwordDesc') }}</p>
      <form class="sec-pwd-form" @submit.prevent="submitPassword">
        <label class="sec-pwd-field">
          <span>{{ t('forcePassword.current') }}</span>
          <input
            v-model="current"
            type="password"
            autocomplete="current-password"
            :disabled="savingPwd"
          />
        </label>
        <label class="sec-pwd-field">
          <span>{{ t('forcePassword.new') }}</span>
          <input v-model="next" type="password" autocomplete="new-password" :disabled="savingPwd" />
        </label>
        <label class="sec-pwd-field">
          <span>{{ t('forcePassword.confirm') }}</span>
          <input
            v-model="confirm"
            type="password"
            autocomplete="new-password"
            :disabled="savingPwd"
          />
        </label>
        <ul class="sec-pwd-rules">
          <li>{{ t('forcePassword.rule12Chars') }}</li>
          <li>{{ t('forcePassword.ruleUpper') }}</li>
          <li>{{ t('forcePassword.ruleDigit') }}</li>
          <li>{{ t('forcePassword.ruleSpecial') }}</li>
        </ul>
        <div class="sec-pwd-actions">
          <button type="submit" class="sec-btn-primary" :disabled="!canSubmitPwd || savingPwd">
            {{ savingPwd ? t('forcePassword.submitting') : t('forcePassword.submit') }}
          </button>
        </div>
      </form>
    </section>

    <section class="sec-block">
      <header class="sec-hd">
        <h3>{{ t('settings.security.blocksTitle') }}</h3>
        <button class="sec-btn" @click="openBlockModal">
          {{ t('settings.security.addBlock') }}
        </button>
      </header>
      <div v-if="loadingBlocks" class="sec-loading">{{ t('common.loading') }}</div>
      <div v-else-if="blocks.length" class="mk-table-wrap">
        <table class="sec-table mk-table">
          <thead>
            <tr>
              <th>{{ t('settings.security.target') }}</th>
              <th>{{ t('settings.security.scope') }}</th>
              <th>{{ t('settings.security.kind') }}</th>
              <th>{{ t('settings.security.until') }}</th>
              <th>{{ t('settings.security.reason') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in blocks" :key="b.id">
              <td :data-label="t('settings.security.target')">
                <div v-if="b.ip" class="sec-target">IP — {{ displayIp(b.ip) }}</div>
                <div v-if="b.username" class="sec-target">@{{ b.username }}</div>
              </td>
              <td :data-label="t('settings.security.scope')">{{ b.scope }}</td>
              <td :data-label="t('settings.security.kind')">
                {{
                  b.permanent ? t('settings.security.permanent') : t('settings.security.temporary')
                }}
              </td>
              <td :data-label="t('settings.security.until')">
                {{ b.blocked_until ? formatDate(b.blocked_until) : '—' }}
              </td>
              <td :data-label="t('settings.security.reason')">{{ b.reason || '—' }}</td>
              <td>
                <button class="sec-btn-danger" @click="removeBlock(b.id)">
                  {{ t('settings.security.unblock') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="sec-empty">{{ t('settings.security.noBlocks') }}</div>
    </section>

    <section class="sec-block">
      <header class="sec-hd">
        <h3>{{ t('settings.security.attemptsTitle') }}</h3>
        <label class="sec-check">
          <input v-model="onlyFailures" type="checkbox" @change="loadAttempts" />
          {{ t('settings.security.onlyFailures') }}
        </label>
      </header>
      <div v-if="loadingAttempts" class="sec-loading">{{ t('common.loading') }}</div>
      <div v-else-if="attempts.length" class="mk-table-wrap">
        <table class="sec-table mk-table">
          <thead>
            <tr>
              <th>{{ t('settings.security.when') }}</th>
              <th>{{ t('settings.security.ip') }}</th>
              <th>{{ t('settings.security.username') }}</th>
              <th>{{ t('settings.security.scope') }}</th>
              <th>{{ t('settings.security.result') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in attempts" :key="a.id" :class="{ 'is-fail': !a.success }">
              <td :data-label="t('settings.security.when')">{{ formatDate(a.created_at) }}</td>
              <td :data-label="t('settings.security.ip')">{{ displayIp(a.ip) }}</td>
              <td :data-label="t('settings.security.username')">{{ a.username || '—' }}</td>
              <td :data-label="t('settings.security.scope')">{{ a.scope }}</td>
              <td :data-label="t('settings.security.result')">
                <span class="sec-pill" :class="a.success ? 'is-ok' : 'is-fail'">
                  {{ a.success ? t('settings.security.success') : t('settings.security.failure') }}
                </span>
              </td>
              <td>
                <button class="sec-btn" @click="quickBlockIp(a)">
                  {{ t('settings.security.blockIp') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="sec-empty">{{ t('settings.security.noAttempts') }}</div>
    </section>

    <div v-if="modalOpen" class="sec-modal-backdrop mk-modal-sheet" @click.self="modalOpen = false">
      <div
        class="sec-modal mk-modal-sheet-panel"
        role="dialog"
        :aria-label="t('settings.security.addBlock')"
      >
        <h4>{{ t('settings.security.addBlock') }}</h4>
        <label>
          {{ t('settings.security.ip') }}
          <input v-model.trim="form.ip" placeholder="192.0.2.0" />
        </label>
        <label>
          {{ t('settings.security.username') }}
          <input v-model.trim="form.username" placeholder="attacker" />
        </label>
        <label>
          {{ t('settings.security.scope') }}
          <select v-model="form.scope">
            <option value="all">all</option>
            <option value="admin">admin</option>
            <option value="portal">portal</option>
          </select>
        </label>
        <label>
          <input v-model="form.permanent" type="checkbox" />
          {{ t('settings.security.permanent') }}
        </label>
        <label>
          {{ t('settings.security.reason') }}
          <input v-model.trim="form.reason" />
        </label>
        <div class="sec-modal-actions">
          <button class="sec-btn" @click="modalOpen = false">{{ t('common.cancel') }}</button>
          <button class="sec-btn-primary" @click="submitBlock">{{ t('common.save') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi, resolveApiError } from '@/composables/useApi'
import { useAuth } from '@/composables/useAuth'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { localizedDateTime } from '@/utils/datetime'

const { t } = useI18n()
const { apiGet, apiPost, apiDelete } = useApi()
const { changePassword } = useAuth()
const { showToast } = useToast()

// Loopback (the server itself) reads as "Local" instead of raw ::1 / 127.x.
const LOOPBACK = new Set(['::1', '127.0.0.1', 'localhost', '::ffff:127.0.0.1'])
function displayIp(ip) {
  if (!ip) return '—'
  const v = String(ip).trim().toLowerCase()
  if (LOOPBACK.has(v) || v.startsWith('127.') || v.startsWith('::ffff:127.')) {
    return t('settings.security.localAddress')
  }
  return ip
}

const current = ref('')
const next = ref('')
const confirm = ref('')
const savingPwd = ref(false)
const canSubmitPwd = computed(
  () => current.value && next.value && confirm.value && next.value.length >= 12,
)

async function submitPassword() {
  if (!canSubmitPwd.value) {
    showToast(t('forcePassword.allRequired'), TOAST_TYPE.ERR)
    return
  }
  if (next.value !== confirm.value) {
    showToast(t('forcePassword.mismatch'), TOAST_TYPE.ERR)
    return
  }
  if (next.value.length < 12) {
    showToast(t('forcePassword.tooShort'), TOAST_TYPE.ERR)
    return
  }
  savingPwd.value = true
  try {
    await changePassword(current.value, next.value)
    showToast(t('forcePassword.success'), TOAST_TYPE.OK)
    current.value = ''
    next.value = ''
    confirm.value = ''
  } catch (e) {
    showToast(resolveApiError(e.message), TOAST_TYPE.ERR)
  } finally {
    savingPwd.value = false
  }
}

const blocks = ref([])
const attempts = ref([])
const loadingBlocks = ref(false)
const loadingAttempts = ref(false)
const onlyFailures = ref(true)

const modalOpen = ref(false)
const form = ref({ ip: '', username: '', scope: 'all', permanent: true, reason: '' })

function formatDate(iso) {
  if (!iso) return ''
  return localizedDateTime(new Date(iso))
}

async function loadBlocks() {
  loadingBlocks.value = true
  try {
    const res = await apiGet('/api/security/blocks')
    blocks.value = res?.items || []
  } finally {
    loadingBlocks.value = false
  }
}

async function loadAttempts() {
  loadingAttempts.value = true
  try {
    const query = new URLSearchParams({
      limit: '100',
      only_failures: onlyFailures.value ? 'true' : 'false',
    })
    const res = await apiGet(`/api/security/attempts?${query}`)
    attempts.value = res?.items || []
  } finally {
    loadingAttempts.value = false
  }
}

function openBlockModal() {
  form.value = { ip: '', username: '', scope: 'all', permanent: true, reason: '' }
  modalOpen.value = true
}

async function submitBlock() {
  if (!form.value.ip && !form.value.username) {
    showToast(t('settings.security.needIpOrUser'), TOAST_TYPE.ERR)
    return
  }
  await apiPost('/api/security/blocks', form.value)
  modalOpen.value = false
  await loadBlocks()
}

async function removeBlock(id) {
  await apiDelete(`/api/security/blocks/${id}`)
  await loadBlocks()
}

async function quickBlockIp(attempt) {
  await apiPost('/api/security/blocks', {
    ip: attempt.ip,
    username: null,
    scope: attempt.scope || 'all',
    permanent: true,
    reason: 'manual_from_attempts',
  })
  await loadBlocks()
}

onMounted(async () => {
  await Promise.all([loadBlocks(), loadAttempts()])
})
</script>

<style scoped>
.params-security {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.sec-block {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 1rem;
}
.sec-desc {
  margin: 0 0 0.75rem;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.sec-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  gap: 1rem;
  flex-wrap: wrap;
}
.sec-hd h3 {
  margin: 0;
  font-size: clamp(0.95rem, 1.5vw, 1.15rem);
}
.sec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.sec-table th,
.sec-table td {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
}
.sec-table th {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}
.sec-table tr.is-fail td {
  color: inherit;
}
.sec-target {
  font-family: monospace;
  font-size: var(--text-sm);
}
.sec-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
}
.sec-pill.is-ok {
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
}
.sec-pill.is-fail {
  background: rgb(var(--color-error-strong-rgb), 0.15);
  color: var(--color-error-strong);
}
.sec-btn,
.sec-btn-primary,
.sec-btn-danger {
  cursor: pointer;
  border: 1px solid var(--border);
  border-radius: var(--radius-btn);
  padding: 0.35rem 0.75rem;
  font-size: var(--text-sm);
}
.sec-btn {
  background: var(--surface-2);
  color: var(--text-primary);
}
.sec-btn-primary {
  background: var(--surface-3);
  color: var(--text-primary);
}
.sec-btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.sec-btn-danger {
  background: rgb(var(--color-error-strong-rgb), 0.15);
  color: var(--color-error-strong);
  border-color: transparent;
}
.sec-loading,
.sec-empty {
  padding: 1rem;
  color: var(--text-secondary);
  font-style: italic;
}
.sec-pwd-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 420px;
}
.sec-pwd-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.sec-pwd-field input {
  padding: 9px 12px;
  border-radius: var(--radius-input);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
}
.sec-pwd-field input:focus {
  outline: none;
  border-color: var(--text-secondary);
}
.sec-pwd-rules {
  list-style: disc inside;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.1rem 0.8rem;
}
.sec-pwd-actions {
  display: flex;
  justify-content: flex-end;
}
.sec-check {
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
  font-size: var(--text-sm);
}
.sec-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgb(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.sec-modal {
  background: var(--bg-panel);
  border-radius: var(--radius-card);
  padding: 1.5rem;
  max-width: 420px;
  width: 90%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.sec-modal h4 {
  margin: 0 0 0.5rem;
}
.sec-modal label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: var(--text-sm);
}
.sec-modal input,
.sec-modal select {
  padding: 0.5rem;
  border-radius: var(--radius-input);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: inherit;
}
.sec-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
