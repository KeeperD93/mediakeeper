<template>
  <div class="ru-status">
    <span
      class="ru-online-dot"
      :class="user.account_active ? 'ru-online-dot--on' : 'ru-online-dot--ko'"
      :title="
        user.online
          ? $t('requestsAdmin.users.labels.online')
          : user.last_seen_at
            ? $t('requestsAdmin.users.labels.lastSeenAt', { at: shortDate(user.last_seen_at) })
            : $t('requestsAdmin.users.labels.neverLoggedIn')
      "
    />
    <span
      class="ru-status-text"
      :class="user.account_active ? 'ru-status-text--ok' : 'ru-status-text--ko'"
    >
      {{ $t(`requestsAdmin.users.labels.${status}`) }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { localizedDate } from '@/utils/datetime'

const props = defineProps({
  user: { type: Object, required: true },
})

// An account never activated still earns XP and trophies; a deactivated one no longer does.
const status = computed(() => {
  if (props.user.account_active) return 'active'
  return props.user.deactivated ? 'deactivated' : 'neverActivated'
})

function shortDate(value) {
  try {
    return localizedDate(new Date(value))
  } catch {
    return value
  }
}
</script>
