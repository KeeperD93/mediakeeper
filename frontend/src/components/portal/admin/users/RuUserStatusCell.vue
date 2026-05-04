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
      {{
        user.account_active
          ? $t('requestsAdmin.users.labels.active')
          : $t('requestsAdmin.users.labels.inactive')
      }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  user: { type: Object, required: true },
})

function shortDate(value) {
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}
</script>
