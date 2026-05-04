<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('requestsAdmin.users.drawer.security.passwordReset')"
        @click.self="close"
      >
        <div class="atl-panel mk-modal-sheet-panel ru-create-panel">
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.drawer.security.passwordReset') }}</h2>
            <button class="atl-close" type="button" :aria-label="$t('common.close')" @click="close">
              <X :size="14" />
            </button>
          </div>
          <div class="ru-form atl-body">
            <p class="ru-help">{{ $t('requestsAdmin.users.drawer.security.passwordResetHelp') }}</p>
            <div class="ru-pwd-row">
              <input :value="password" type="text" readonly class="ru-mono" />
              <button type="button" class="ru-pwd-toggle" :title="$t('common.copy')" @click="copy">
                <component :is="copied ? Check : Copy" :size="16" />
              </button>
            </div>
            <p v-if="copied" class="ru-help">{{ $t('common.copied') }}</p>
          </div>
          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--primary" @click="close">
              {{ $t('common.close') }}
            </button>
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { Check, Copy, X } from 'lucide-vue-next'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  password: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const copied = ref(false)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.password)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    /* Clipboard API unavailable — admin can still select manually. */
  }
}

function close() {
  emit('close')
}
</script>
