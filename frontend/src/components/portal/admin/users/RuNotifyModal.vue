<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('requestsAdmin.users.actions.notify')"
        @click.self="close"
      >
        <form class="atl-panel mk-modal-sheet-panel ru-create-panel" @submit.prevent="submit">
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.actions.notify') }}</h2>
            <button class="atl-close" type="button" :aria-label="$t('common.close')" @click="close"><X :size="14" /></button>
          </div>

          <div class="ru-form atl-body">
            <p v-if="user" class="ru-help">
              {{ $t('requestsAdmin.users.drawer.notify.target', { name: user.display_name }) }}
            </p>
            <label>
              <span>{{ $t('requestsAdmin.users.drawer.notify.titleField') }} *</span>
              <input v-model="title" type="text" maxlength="120" required />
            </label>
            <label>
              <span>{{ $t('requestsAdmin.users.drawer.notify.body') }} *</span>
              <textarea v-model="body" class="ru-textarea" rows="5" maxlength="1000" required />
            </label>
          </div>

          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--ghost" @click="close">{{ $t('common.cancel') }}</button>
            <button type="submit" class="ru-btn ru-btn--primary" :disabled="busy || !title || !body">
              {{ $t('requestsAdmin.users.drawer.notify.send') }}
            </button>
          </footer>
        </form>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  user: { type: Object, default: null },
})
const emit = defineEmits(['close', 'sent'])

const { t } = useI18n()
const { showToast } = useToast()
const api = usePortalAdminUsers()
const title = ref('')
const body = ref('')
const busy = ref(false)

watch(() => props.open, (v) => {
  if (v) { title.value = ''; body.value = '' }
})

async function submit() {
  if (!props.user) return
  busy.value = true
  try {
    const res = await api.notifyUser(props.user.id, { title: title.value, body: body.value })
    if (res?.ok) {
      emit('sent', res)
    } else if (res?.error) {
      showToast(t(`requestsAdmin.users.errors.${res.error}`, t('common.error')), TOAST_TYPE.ERR)
    }
  } finally { busy.value = false }
}

function close() { if (!busy.value) emit('close') }
</script>
