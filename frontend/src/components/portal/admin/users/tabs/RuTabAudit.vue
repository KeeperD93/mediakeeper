<template>
  <div class="ru-tab ru-tab-audit">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.tabs.audit') }}</h3>
      <div v-if="loading" class="ru-loading">{{ $t('common.loading') }}</div>
      <div v-else-if="!entries.length" class="ru-help">
        {{ $t('requestsAdmin.users.drawer.audit.empty') }}
      </div>
      <ol v-else class="ru-audit-list">
        <li v-for="entry in entries" :key="entry.id" class="ru-audit-item">
          <span class="ru-audit-date">{{ fmt(entry.created_at) }}</span>
          <div class="ru-audit-body">
            <span class="ru-audit-action">
              {{ $t(`requestsAdmin.users.audit.${entry.action}`, entry.action) }}
            </span>
            <span v-if="describe(entry)" class="ru-audit-detail">{{ describe(entry) }}</span>
          </div>
        </li>
      </ol>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'

const props = defineProps({ user: { type: Object, required: true } })
const api = usePortalAdminUsers()
const { t, te } = useI18n()

const loading = ref(false)
const entries = ref([])

async function load() {
  loading.value = true
  try {
    const res = await api.fetchAudit(props.user.id, { limit: 200 })
    entries.value = res?.items || []
  } finally {
    loading.value = false
  }
}

watch(() => props.user.id, load)
onMounted(load)

function fmt(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function tRole(role) {
  const key = `requestsAdmin.users.filters.role.${role}`
  return te(key) ? t(key) : role
}

function tField(key) {
  const i18nKey = `requestsAdmin.users.drawer.identity.${key}`
  return te(i18nKey) ? t(i18nKey) : key
}

function tPerm(key) {
  const i18nKey = `requestsAdmin.users.permissions.${key}`
  return te(i18nKey) ? t(i18nKey) : key
}

function fmtDate(value) {
  if (!value) return t('requestsAdmin.users.drawer.audit.noLimit')
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}

function describe(entry) {
  const a = entry.action
  const p = entry.payload || {}
  if (a === 'user.role_changed' && p.from && p.to) {
    return t('requestsAdmin.users.drawer.audit.roleChange', {
      from: tRole(p.from),
      to: tRole(p.to),
    })
  }
  if (a === 'user.identity_updated' && Array.isArray(p.changed) && p.changed.length) {
    return t('requestsAdmin.users.drawer.audit.identityChange', {
      fields: p.changed.map(tField).join(', '),
    })
  }
  if (a === 'user.access_window_set') {
    return t('requestsAdmin.users.drawer.audit.accessWindow', {
      from: fmtDate(p.start),
      to: fmtDate(p.end),
    })
  }
  if (a === 'user.access_extended' && p.months) {
    return t('requestsAdmin.users.drawer.audit.accessExtended', { months: p.months })
  }
  if (a === 'user.permissions_changed' && p.changed) {
    const parts = []
    for (const [key, val] of Object.entries(p.changed)) {
      const to = val && typeof val === 'object' && 'to' in val ? val.to : val
      const verb = to
        ? t('requestsAdmin.users.drawer.audit.permEnabled')
        : t('requestsAdmin.users.drawer.audit.permDisabled')
      parts.push(`${tPerm(key)} → ${verb}`)
    }
    return parts.join(' · ')
  }
  if (a === 'user.emby_disabled' && p.error) {
    return t('requestsAdmin.users.drawer.audit.embyError', { error: p.error })
  }
  if (a === 'user.tags_updated' && Array.isArray(p.tags)) {
    return p.tags.length
      ? t('requestsAdmin.users.drawer.audit.tagsSet', { tags: p.tags.join(', ') })
      : t('requestsAdmin.users.drawer.audit.tagsCleared')
  }
  if (a === 'user.notification_sent' && p.title) {
    return t('requestsAdmin.users.drawer.audit.notification', { title: p.title })
  }
  return ''
}
</script>
