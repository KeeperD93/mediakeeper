<template>
  <Teleport to="body">
    <div class="ru-bulkbar" role="toolbar">
      <div class="ru-bulkbar-count">
        <Users :size="16" />
        {{ $t('requestsAdmin.users.bulk.selected', { count }) }}
      </div>

      <div class="ru-bulkbar-actions">
        <button
          class="ru-btn ru-btn--ghost"
          @click="$emit('action', { action: BULK_ACTION.ACTIVATE })"
        >
          {{ $t('requestsAdmin.users.actions.activate') }}
        </button>
        <button
          class="ru-btn ru-btn--ghost"
          @click="$emit('action', { action: BULK_ACTION.DEACTIVATE })"
        >
          {{ $t('requestsAdmin.users.actions.deactivate') }}
        </button>
        <select class="ru-toolbar-select mk-select-chevron" @change="onSetRole">
          <option value="">{{ $t('requestsAdmin.users.actions.set_role') }}…</option>
          <option value="viewer">{{ $t('requestsAdmin.users.filters.role.viewer') }}</option>
          <option value="moderator">{{ $t('requestsAdmin.users.filters.role.moderator') }}</option>
          <option value="admin">{{ $t('requestsAdmin.users.filters.role.admin') }}</option>
        </select>
        <button class="ru-btn ru-btn--ghost" @click="permsOpen = true">
          {{ $t('requestsAdmin.users.bulkPerms.title') }}…
        </button>
        <button
          class="ru-btn ru-btn--ghost"
          @click="$emit('action', { action: BULK_ACTION.EXPORT })"
        >
          {{ $t('requestsAdmin.users.actions.export') }}
        </button>
        <button
          class="ru-btn ru-btn--danger"
          @click="$emit('action', { action: BULK_ACTION.DELETE })"
        >
          {{ $t('requestsAdmin.users.actions.delete') }}
        </button>
        <button class="ru-btn ru-btn--ghost" @click="$emit('clear')">
          {{ $t('common.cancel') }}
        </button>
      </div>
    </div>
    <RuBulkPermsModal
      :open="permsOpen"
      :count="count"
      @close="permsOpen = false"
      @apply="onApplyBulk"
    />
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { Users } from 'lucide-vue-next'
import RuBulkPermsModal from './RuBulkPermsModal.vue'
import { BULK_ACTION } from '@/constants/portalAdminUsers'

defineProps({ count: { type: Number, default: 0 } })
const emit = defineEmits(['action', 'clear'])
const permsOpen = ref(false)

function onSetRole(event) {
  const role = event.target.value
  if (!role) return
  emit('action', { action: BULK_ACTION.SET_ROLE, payload: { role } })
  event.target.value = ''
}

// One overlay edits permissions + request rights; the page splits this into
// the matching backend bulk calls (set_permissions / set_quota).
function onApplyBulk({ permissions, quota }) {
  permsOpen.value = false
  emit('action', { action: BULK_ACTION.BULK_EDIT, payload: { permissions, quota } })
}
</script>
