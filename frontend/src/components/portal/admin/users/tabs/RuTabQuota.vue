<template>
  <div class="ru-tab ru-tab-quota">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.quota.mode') }}</h3>
      <div class="ru-pill-row">
        <button
          type="button"
          class="ru-pill"
          :class="{ 'ru-pill--active': form.mode === 'manual' }"
          :disabled="busy"
          @click="form.mode = 'manual'"
        >
          {{ $t('requestsAdmin.users.drawer.quota.modeManual') }}
        </button>
        <button
          type="button"
          class="ru-pill"
          :class="{ 'ru-pill--active': form.mode === 'auto' }"
          :disabled="busy"
          @click="form.mode = 'auto'"
        >
          {{ $t('requestsAdmin.users.drawer.quota.modeAuto') }}
        </button>
      </div>
      <p class="ru-help">{{ $t('requestsAdmin.users.drawer.quota.modeHelp') }}</p>
    </section>

    <section v-if="form.mode === 'manual'" class="ru-tab-section">
      <div class="ru-toggle-row">
        <label class="ru-switch">
          <input v-model="form.unlimited" type="checkbox" :disabled="busy" />
          <span />
        </label>
        <div>
          <strong>{{ $t('requestsAdmin.users.drawer.quota.unlimited') }}</strong>
          <p class="ru-help">{{ $t('requestsAdmin.users.drawer.quota.unlimitedHelp') }}</p>
        </div>
      </div>
      <div class="ru-form-grid">
        <label>
          <span>{{ $t('requestsAdmin.users.drawer.quota.maxAllowed') }}</span>
          <input
            v-model.number="form.max_allowed"
            type="number"
            min="1"
            max="100"
            :disabled="busy || form.unlimited"
          />
        </label>
      </div>
    </section>

    <section v-else class="ru-tab-section">
      <div class="ru-form-grid">
        <label>
          <span>{{ $t('requestsAdmin.users.drawer.quota.autoMin') }}</span>
          <input v-model.number="form.auto_min" type="number" min="1" max="100" :disabled="busy" />
        </label>
        <label>
          <span>{{ $t('requestsAdmin.users.drawer.quota.autoMax') }}</span>
          <input v-model.number="form.auto_max" type="number" min="1" max="100" :disabled="busy" />
        </label>
      </div>
      <p v-if="boundsError" class="ru-form-error">
        {{ $t('requestsAdmin.users.drawer.quota.boundsError') }}
      </p>
      <p class="ru-help">
        {{ $t('requestsAdmin.users.drawer.quota.autoCurrent', { cap: quota.max_allowed ?? '—' }) }}
        <template v-if="quota.last_recomputed_at">
          ·
          {{
            $t('requestsAdmin.users.drawer.quota.autoLastRun', {
              date: fmtDate(quota.last_recomputed_at),
            })
          }}
        </template>
      </p>
    </section>

    <section class="ru-tab-section">
      <div class="ru-toggle-row">
        <label class="ru-switch">
          <input v-model="form.auto_approve" type="checkbox" :disabled="busy" />
          <span />
        </label>
        <div>
          <strong>{{ $t('requestsAdmin.users.drawer.quota.autoApprove') }}</strong>
          <p class="ru-help">{{ $t('requestsAdmin.users.drawer.quota.autoApproveHelp') }}</p>
        </div>
      </div>
      <p class="ru-help">
        {{ $t('requestsAdmin.users.drawer.quota.usage', { used: quota.used ?? 0, cap: capLabel }) }}
      </p>
    </section>

    <div class="ru-form-actions ru-form-actions--inline">
      <button
        type="button"
        class="ru-btn ru-btn--primary"
        :disabled="busy || boundsError"
        @click="save"
      >
        {{ $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { localizedDate } from '@/utils/datetime'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const { t } = useI18n()
const { showToast } = useToast()
const api = usePortalAdminUsers()

const busy = ref(false)
const quota = computed(() => props.user.quota || {})

const form = reactive({
  mode: 'manual',
  max_allowed: 5,
  unlimited: false,
  auto_approve: false,
  auto_min: 2,
  auto_max: 15,
})

function hydrate(q) {
  form.mode = q.mode === 'auto' ? 'auto' : 'manual'
  form.max_allowed = q.max_allowed ?? 5
  form.unlimited = !!q.unlimited
  form.auto_approve = !!q.auto_approve
  form.auto_min = q.auto_min ?? 2
  form.auto_max = q.auto_max ?? 15
}
hydrate(quota.value)
watch(quota, hydrate)

const boundsError = computed(
  () => form.mode === 'auto' && Number(form.auto_min) > Number(form.auto_max),
)
const capLabel = computed(() => (quota.value.unlimited ? '∞' : (quota.value.max_allowed ?? '—')))

function fmtDate(value) {
  try {
    return localizedDate(new Date(value))
  } catch {
    return value
  }
}

async function save() {
  if (boundsError.value) return
  const payload = { mode: form.mode, auto_approve: form.auto_approve }
  if (form.mode === 'manual') {
    payload.unlimited = form.unlimited
    if (!form.unlimited) payload.max_allowed = form.max_allowed
  } else {
    payload.auto_min = form.auto_min
    payload.auto_max = form.auto_max
  }
  busy.value = true
  try {
    const res = await api.patchQuota(props.user.id, payload)
    if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
      return
    }
    showToast(t('requestsAdmin.users.toasts.saved'), TOAST_TYPE.OK)
    emit('changed')
  } finally {
    busy.value = false
  }
}
</script>
