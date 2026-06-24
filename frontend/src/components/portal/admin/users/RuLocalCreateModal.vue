<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('requestsAdmin.users.drawerLocal.title')"
        @click.self="close"
      >
        <form
          ref="panelRef"
          class="atl-panel mk-modal-sheet-panel ru-create-panel"
          @submit.prevent="submit"
        >
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.drawerLocal.title') }}</h2>
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
            <label>
              <span>{{ $t('requestsAdmin.users.drawerLocal.username') }} *</span>
              <input
                v-model="form.username"
                type="text"
                minlength="3"
                maxlength="50"
                required
                autofocus
              />
            </label>
            <label>
              <span>{{ $t('requestsAdmin.users.drawerLocal.password') }} *</span>
              <div class="ru-pwd-row">
                <input
                  v-model="form.password"
                  :type="showPwd ? 'text' : 'password'"
                  minlength="8"
                  maxlength="128"
                  required
                />
                <button
                  type="button"
                  class="ru-pwd-toggle"
                  :title="showPwd ? $t('common.hide') : $t('common.show')"
                  @click="showPwd = !showPwd"
                >
                  <component :is="showPwd ? EyeOff : Eye" :size="16" />
                </button>
              </div>
            </label>
            <label>
              <span>{{ $t('requestsAdmin.users.drawerLocal.displayName') }}</span>
              <input v-model="form.display_name" type="text" maxlength="50" />
            </label>
            <label>
              <span>{{ $t('requestsAdmin.users.drawerLocal.email') }}</span>
              <input v-model="form.email" type="email" maxlength="255" />
            </label>
            <div class="ru-form-grid">
              <label>
                <span>{{ $t('requestsAdmin.users.drawerLocal.firstName') }}</span>
                <input v-model="form.first_name" type="text" maxlength="100" />
              </label>
              <label>
                <span>{{ $t('requestsAdmin.users.drawerLocal.lastName') }}</span>
                <input v-model="form.last_name" type="text" maxlength="100" />
              </label>
            </div>
            <label>
              <span>{{ $t('requestsAdmin.users.drawerLocal.role') }}</span>
              <select v-model="form.role">
                <option v-for="r in USER_ROLES" :key="r" :value="r">
                  {{ $t(`requestsAdmin.users.filters.role.${r}`) }}
                </option>
              </select>
            </label>
            <label class="ru-form-row ru-form-row--inline">
              <input v-model="form.account_active" type="checkbox" />
              <span>{{ $t('requestsAdmin.users.drawerLocal.active') }}</span>
            </label>

            <p v-if="error" class="ru-form-error">{{ error }}</p>
          </div>

          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--ghost" @click="close">
              {{ $t('common.cancel') }}
            </button>
            <button type="submit" class="ru-btn ru-btn--primary" :disabled="busy">
              {{ $t('requestsAdmin.users.drawerLocal.create') }}
            </button>
          </footer>
        </form>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { reactive, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, EyeOff, X } from 'lucide-vue-next'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { USER_ROLE, USER_ROLES } from '@/constants/portalAdminUsers'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'created'])

const { t } = useI18n()
const api = usePortalAdminUsers()

const empty = () => ({
  username: '',
  password: '',
  display_name: '',
  email: '',
  first_name: '',
  last_name: '',
  role: USER_ROLE.VIEWER,
  account_active: true,
})
const form = reactive(empty())
const busy = ref(false)
const error = ref('')
const showPwd = ref(false)
const panelRef = ref(null)
const closeBtnRef = ref(null)

watch(
  () => props.open,
  v => {
    if (v) {
      Object.assign(form, empty())
      error.value = ''
      showPwd.value = false
    }
  },
)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const res = await api.createLocalUser({ ...form })
    if (res?.error) {
      error.value = t(`requestsAdmin.users.errors.${res.error}`, t('common.error'))
      return
    }
    emit('created', res)
  } finally {
    busy.value = false
  }
}

function close() {
  if (busy.value) return
  emit('close')
}

useFocusTrap({
  active: toRef(props, 'open'),
  containerRef: panelRef,
  initialFocusRef: closeBtnRef,
  onEscape: close,
})
</script>
