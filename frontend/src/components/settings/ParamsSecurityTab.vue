<template>
  <div class="params-security">
    <section class="sec-block">
      <header class="sec-hd">
        <h3>{{ t('settings.security.blocksTitle') }}</h3>
        <button class="sec-btn" @click="openBlockModal">{{ t('settings.security.addBlock') }}</button>
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
                <div v-if="b.ip" class="sec-target">IP — {{ b.ip }}</div>
                <div v-if="b.username" class="sec-target">@{{ b.username }}</div>
              </td>
              <td :data-label="t('settings.security.scope')">{{ b.scope }}</td>
              <td :data-label="t('settings.security.kind')">{{ b.permanent ? t('settings.security.permanent') : t('settings.security.temporary') }}</td>
              <td :data-label="t('settings.security.until')">{{ b.blocked_until ? formatDate(b.blocked_until) : '—' }}</td>
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
              <td :data-label="t('settings.security.ip')">{{ a.ip }}</td>
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
      <div class="sec-modal mk-modal-sheet-panel" role="dialog" :aria-label="t('settings.security.addBlock')">
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
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

const { t } = useI18n()
const { apiGet, apiPost, apiDelete } = useApi()
const { showToast } = useToast()

const blocks = ref([])
const attempts = ref([])
const loadingBlocks = ref(false)
const loadingAttempts = ref(false)
const onlyFailures = ref(true)

const modalOpen = ref(false)
const form = ref({ ip: '', username: '', scope: 'all', permanent: true, reason: '' })

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
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
.params-security { display: flex; flex-direction: column; gap: 1.5rem; }
.sec-block { background: rgba(var(--accent-rgb), 0.04); border-radius: var(--radius-card); padding: 1rem; }
.sec-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: .75rem; gap: 1rem; flex-wrap: wrap; }
.sec-hd h3 { margin: 0; font-size: clamp(0.95rem, 1.5vw, 1.15rem); }
.sec-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.sec-table th, .sec-table td { text-align: left; padding: .5rem .75rem; border-bottom: 1px solid rgba(var(--accent-rgb), 0.1); }
.sec-table th { font-weight: var(--font-medium); color: var(--accent-400); }
.sec-table tr.is-fail td { color: inherit; }
.sec-target { font-family: monospace; font-size: var(--text-sm); }
.sec-pill { display: inline-block; padding: 2px 8px; border-radius: var(--radius-btn); font-size: var(--text-xs); }
.sec-pill.is-ok { background: rgba(34, 197, 94, 0.15); color: rgb(34, 197, 94); }
.sec-pill.is-fail { background: rgba(239, 68, 68, 0.15); color: rgb(239, 68, 68); }
.sec-btn, .sec-btn-primary, .sec-btn-danger { cursor: pointer; border: 0; border-radius: var(--radius-btn); padding: .35rem .75rem; font-size: var(--text-sm); }
.sec-btn { background: rgba(var(--accent-rgb), 0.12); color: var(--accent-400); }
.sec-btn-primary { background: var(--accent-500); color: white; }
.sec-btn-danger { background: rgba(239, 68, 68, 0.15); color: rgb(239, 68, 68); }
.sec-loading, .sec-empty { padding: 1rem; color: rgba(var(--accent-rgb), 0.6); font-style: italic; }
.sec-check { display: inline-flex; gap: .5rem; align-items: center; font-size: var(--text-sm); }
.sec-modal-backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.sec-modal { background: var(--bg-panel); border-radius: var(--radius-card); padding: 1.5rem; max-width: 420px; width: 90%; display: flex; flex-direction: column; gap: .75rem; }
.sec-modal h4 { margin: 0 0 .5rem; }
.sec-modal label { display: flex; flex-direction: column; gap: .25rem; font-size: var(--text-sm); }
.sec-modal input, .sec-modal select { padding: .5rem; border-radius: var(--radius-input); border: 1px solid rgba(var(--accent-rgb), 0.2); background: rgba(0, 0, 0, 0.2); color: inherit; }
.sec-modal-actions { display: flex; justify-content: flex-end; gap: .5rem; margin-top: .5rem; }
</style>
