<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('requestsAdmin.users.bulkPerms.title')"
        @click.self="close"
      >
        <form
          ref="panelRef"
          class="atl-panel mk-modal-sheet-panel ru-create-panel"
          @submit.prevent="submit"
        >
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.bulkPerms.title') }}</h2>
            <button
              ref="closeBtnRef"
              class="atl-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="close"
            >
              <X :size="14" />
            </button>
          </div>
          <div class="ru-form atl-body">
            <p class="ru-help">{{ $t('requestsAdmin.users.bulkPerms.help', { count }) }}</p>

            <!-- Permissions group. Each row is a <label> so the control gets an
                 implicit accessible name from its text, like the sibling forms. -->
            <fieldset class="ru-bulk-group">
              <legend>{{ $t('requestsAdmin.users.bulkPerms.permsGroup') }}</legend>
              <label v-for="key in PERMISSION_KEYS" :key="key" class="ru-bulk-row">
                <span class="ru-bulk-label">
                  {{ $t(`requestsAdmin.users.permissions.${key}`) }}
                </span>
                <select v-model="perms[key]" class="ru-bulk-control">
                  <option value="">{{ $t('requestsAdmin.users.bulkPerms.noChange') }}</option>
                  <option value="on">{{ $t('requestsAdmin.users.bulkPerms.enable') }}</option>
                  <option value="off">{{ $t('requestsAdmin.users.bulkPerms.disable') }}</option>
                </select>
              </label>
            </fieldset>

            <!-- Requests / quota group -->
            <fieldset class="ru-bulk-group">
              <legend>{{ $t('requestsAdmin.users.bulkPerms.requestsGroup') }}</legend>
              <label class="ru-bulk-row">
                <span class="ru-bulk-label">
                  {{ $t('requestsAdmin.users.drawer.quota.autoApprove') }}
                </span>
                <select v-model="quota.auto_approve" class="ru-bulk-control">
                  <option value="">{{ $t('requestsAdmin.users.bulkPerms.noChange') }}</option>
                  <option value="on">{{ $t('requestsAdmin.users.bulkPerms.enable') }}</option>
                  <option value="off">{{ $t('requestsAdmin.users.bulkPerms.disable') }}</option>
                </select>
              </label>
              <label class="ru-bulk-row">
                <span class="ru-bulk-label">{{ $t('requestsAdmin.users.drawer.quota.mode') }}</span>
                <select v-model="quota.mode" class="ru-bulk-control">
                  <option value="">{{ $t('requestsAdmin.users.bulkPerms.noChange') }}</option>
                  <option value="manual">
                    {{ $t('requestsAdmin.users.drawer.quota.modeManual') }}
                  </option>
                  <option value="auto">
                    {{ $t('requestsAdmin.users.drawer.quota.modeAuto') }}
                  </option>
                </select>
              </label>

              <template v-if="quota.mode === 'manual'">
                <label class="ru-bulk-row">
                  <span class="ru-bulk-label">
                    {{ $t('requestsAdmin.users.drawer.quota.unlimited') }}
                  </span>
                  <select v-model="quota.unlimited" class="ru-bulk-control">
                    <option value="">{{ $t('requestsAdmin.users.bulkPerms.noChange') }}</option>
                    <option value="on">{{ $t('requestsAdmin.users.bulkPerms.enable') }}</option>
                    <option value="off">{{ $t('requestsAdmin.users.bulkPerms.disable') }}</option>
                  </select>
                </label>
                <label v-if="quota.unlimited !== 'on'" class="ru-bulk-row">
                  <span class="ru-bulk-label">
                    {{ $t('requestsAdmin.users.drawer.quota.maxAllowed') }}
                  </span>
                  <input
                    v-model="quota.max_allowed"
                    type="number"
                    min="1"
                    max="100"
                    class="ru-bulk-control"
                    :placeholder="$t('requestsAdmin.users.bulkPerms.noChange')"
                  />
                </label>
              </template>

              <template v-else-if="quota.mode === 'auto'">
                <label class="ru-bulk-row">
                  <span class="ru-bulk-label">
                    {{ $t('requestsAdmin.users.drawer.quota.autoMin') }}
                  </span>
                  <input
                    v-model="quota.auto_min"
                    type="number"
                    min="1"
                    max="100"
                    class="ru-bulk-control"
                    :placeholder="$t('requestsAdmin.users.bulkPerms.noChange')"
                  />
                </label>
                <label class="ru-bulk-row">
                  <span class="ru-bulk-label">
                    {{ $t('requestsAdmin.users.drawer.quota.autoMax') }}
                  </span>
                  <input
                    v-model="quota.auto_max"
                    type="number"
                    min="1"
                    max="100"
                    class="ru-bulk-control"
                    :placeholder="$t('requestsAdmin.users.bulkPerms.noChange')"
                  />
                </label>
                <p v-if="boundsError" class="ru-form-error">
                  {{ $t('requestsAdmin.users.drawer.quota.boundsError') }}
                </p>
              </template>
            </fieldset>
          </div>
          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--ghost" @click="close">
              {{ $t('common.cancel') }}
            </button>
            <button
              type="submit"
              class="ru-btn ru-btn--primary"
              :disabled="!hasChanges || boundsError"
            >
              {{ $t('requestsAdmin.users.bulkPerms.apply') }}
            </button>
          </footer>
        </form>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { reactive, ref, computed, toRef, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { PERMISSION_KEYS } from '@/constants/portalAdminUsers'

import { useFocusTrap } from '@/composables/useFocusTrap'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  count: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'apply'])

// Each control defaults to "" = no change. Permissions + auto-approve +
// unlimited use a tri-state select (''/on/off); the quota numbers stay blank
// until the admin types one. mode gates which quota numbers are shown.
const emptyPerms = () => Object.fromEntries(PERMISSION_KEYS.map(k => [k, '']))
const emptyQuota = () => ({
  auto_approve: '',
  mode: '',
  unlimited: '',
  max_allowed: '',
  auto_min: '',
  auto_max: '',
})
const perms = reactive(emptyPerms())
const quota = reactive(emptyQuota())
const panelRef = ref(null)
const closeBtnRef = ref(null)

watch(
  () => props.open,
  v => {
    if (v) {
      Object.assign(perms, emptyPerms())
      Object.assign(quota, emptyQuota())
    }
  },
)

const boundsError = computed(
  () =>
    quota.mode === 'auto' &&
    quota.auto_min !== '' &&
    quota.auto_max !== '' &&
    Number(quota.auto_min) > Number(quota.auto_max),
)

function buildPerms() {
  const out = {}
  for (const k of PERMISSION_KEYS) {
    if (perms[k] === 'on') out[k] = true
    else if (perms[k] === 'off') out[k] = false
  }
  return out
}

function buildQuota() {
  const out = {}
  if (quota.auto_approve) out.auto_approve = quota.auto_approve === 'on'
  if (quota.mode) out.mode = quota.mode
  if (quota.mode === 'manual') {
    if (quota.unlimited) out.unlimited = quota.unlimited === 'on'
    if (quota.max_allowed !== '') out.max_allowed = Number(quota.max_allowed)
  } else if (quota.mode === 'auto') {
    if (quota.auto_min !== '') out.auto_min = Number(quota.auto_min)
    if (quota.auto_max !== '') out.auto_max = Number(quota.auto_max)
  }
  return out
}

const hasChanges = computed(
  () => Object.keys(buildPerms()).length > 0 || Object.keys(buildQuota()).length > 0,
)

function submit() {
  if (boundsError.value || !hasChanges.value) return
  emit('apply', { permissions: buildPerms(), quota: buildQuota() })
}

function close() {
  emit('close')
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>

<style scoped>
.ru-bulk-group {
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 0.75rem 1rem 0.4rem;
  margin: 0.25rem 0 0;
}
.ru-bulk-group + .ru-bulk-group {
  margin-top: 0.85rem;
}
.ru-bulk-group legend {
  padding: 0 0.4rem;
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  color: var(--text-primary);
}
/* Label takes the remaining width (no more two-line wrapping); every control
   sits in the same fixed column so the right edge stays uniform. */
.ru-bulk-row {
  display: grid;
  grid-template-columns: 1fr 190px;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.55rem;
}
.ru-bulk-label {
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-size: var(--text-sm);
}
.ru-bulk-control {
  width: 100%;
  padding: 0.45rem 0.6rem;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
}
.ru-bulk-control:focus {
  border-color: var(--accent);
  outline: none;
}
</style>
