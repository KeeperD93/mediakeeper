<template>
  <span v-if="!user.access_end_date" class="ru-expiry ru-expiry--none">—</span>
  <span v-else-if="user.is_expired" class="ru-expiry ru-expiry--expired">
    {{ $t('requestsAdmin.users.labels.expired') }}
  </span>
  <span v-else-if="imminent" class="ru-expiry ru-expiry--imminent">
    {{ imminent }}
  </span>
  <span
    v-else-if="user.expires_in_days !== null && user.expires_in_days <= 7"
    class="ru-expiry ru-expiry--warn"
  >
    {{ $t('requestsAdmin.users.labels.expiresInDays', { days: user.expires_in_days }) }}
  </span>
  <span v-else class="ru-expiry">
    {{ $t('requestsAdmin.users.labels.expiresOn', { at: shortDate(user.access_end_date) }) }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  user: { type: Object, required: true },
})

const { t } = useI18n()

const imminent = computed(() => {
  if (!props.user.access_end_date || props.user.is_expired) return ''
  const end = new Date(props.user.access_end_date).getTime()
  const diff = end - Date.now()
  if (diff <= 0 || diff >= 24 * 3600 * 1000) return ''
  const totalMin = Math.floor(diff / 60000)
  const hours = Math.floor(totalMin / 60)
  const mins = totalMin % 60
  if (hours <= 0) return t('requestsAdmin.users.labels.expiresInMinutes', { minutes: mins })
  return t('requestsAdmin.users.labels.expiresInHoursMinutes', { hours, minutes: mins })
})

function shortDate(value) {
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}
</script>
