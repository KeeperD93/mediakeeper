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
        <form class="atl-panel mk-modal-sheet-panel ru-create-panel" @submit.prevent="submit">
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.bulkPerms.title') }}</h2>
            <button class="atl-close" type="button" :aria-label="$t('common.close')" @click="close"><X :size="14" /></button>
          </div>
          <div class="ru-form atl-body">
            <p class="ru-help">{{ $t('requestsAdmin.users.bulkPerms.help', { count }) }}</p>
            <ul class="ru-bulk-perm-list">
              <li v-for="key in PERMISSION_KEYS" :key="key">
                <span>{{ $t(`requestsAdmin.users.permissions.${key}`) }}</span>
                <select v-model="state[key]">
                  <option value="">{{ $t('requestsAdmin.users.bulkPerms.noChange') }}</option>
                  <option value="on">{{ $t('requestsAdmin.users.bulkPerms.enable') }}</option>
                  <option value="off">{{ $t('requestsAdmin.users.bulkPerms.disable') }}</option>
                </select>
              </li>
            </ul>
          </div>
          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--ghost" @click="close">{{ $t('common.cancel') }}</button>
            <button type="submit" class="ru-btn ru-btn--primary" :disabled="!hasChanges">
              {{ $t('requestsAdmin.users.bulkPerms.apply') }}
            </button>
          </footer>
        </form>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { PERMISSION_KEYS } from '@/constants/portalAdminUsers'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  count: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'apply'])

const empty = () => Object.fromEntries(PERMISSION_KEYS.map((k) => [k, '']))
const state = reactive(empty())

watch(() => props.open, (v) => { if (v) Object.assign(state, empty()) })

const hasChanges = computed(() => Object.values(state).some((v) => v))

function submit() {
  const permissions = {}
  for (const k of PERMISSION_KEYS) {
    if (state[k] === 'on') permissions[k] = true
    else if (state[k] === 'off') permissions[k] = false
  }
  emit('apply', permissions)
}

function close() { emit('close') }
</script>

<style scoped>
.ru-bulk-perm-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .55rem; }
.ru-bulk-perm-list li { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.ru-bulk-perm-list span { font-weight: var(--font-medium); color: var(--text-primary); font-size: var(--text-sm); }
.ru-bulk-perm-list select { min-width: 160px; }
</style>
