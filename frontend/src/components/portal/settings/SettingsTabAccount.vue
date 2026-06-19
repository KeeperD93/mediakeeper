<template>
  <div class="pt-settings-card">
    <h3 class="pt-settings-section-title">{{ $t('portal.settings.account.passwordSection') }}</h3>
    <p class="pt-settings-section-sub">{{ $t('portal.settings.account.passwordHint') }}</p>

    <div>
      <a
        v-if="embyUrl"
        :href="embyHref"
        target="_blank"
        rel="noopener noreferrer"
        class="pt-settings-btn"
      >
        <ExternalLink :size="14" />
        {{ $t('portal.settings.account.passwordEmbyCta') }}
      </a>
    </div>

    <hr class="pt-settings-divider" />

    <h3 class="pt-settings-section-title">{{ $t('portal.settings.account.infoSection') }}</h3>

    <dl class="pt-settings-info">
      <div class="pt-settings-info-row">
        <dt>{{ $t('portal.settings.account.embyUsername') }}</dt>
        <dd>{{ profileData?.display_name || '—' }}</dd>
      </div>
      <div class="pt-settings-info-row">
        <dt>{{ $t('portal.settings.account.memberSince') }}</dt>
        <dd>{{ memberSinceLabel || '—' }}</dd>
      </div>
      <div class="pt-settings-info-row">
        <dt>{{ $t('portal.settings.account.accessExpires') }}</dt>
        <dd>{{ accessExpiresLabel }}</dd>
      </div>
      <div class="pt-settings-info-row">
        <dt>{{ $t('portal.settings.account.currentLevel') }}</dt>
        <dd>{{ profileData?.level ?? '—' }} · {{ (profileData?.xp ?? 0).toLocaleString() }} XP</dd>
      </div>
    </dl>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ExternalLink } from 'lucide-vue-next'
import { safeHref } from '@/utils/safeUrl'

const props = defineProps({
  profileData: { type: Object, default: null },
  embyUrl: { type: String, default: '' },
})

const { t, locale } = useI18n()

// Gate the Emby account deep-link through the scheme whitelist.
const embyHref = computed(() => safeHref(props.embyUrl) || '#')

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(locale.value, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return ''
  }
}

const memberSinceLabel = computed(() => formatDate(props.profileData?.created_at))

const accessExpiresLabel = computed(() => {
  const iso = props.profileData?.access_end_date
  if (!iso) return t('portal.settings.account.accessExpiresNever')
  return formatDate(iso) || '—'
})
</script>

<style scoped>
.pt-settings-divider {
  border: none;
  border-top: 1px solid var(--portal-border-default);
  margin: 0.5rem 0;
}

.pt-settings-info {
  display: grid;
  gap: 0.5rem;
  margin: 0;
}

.pt-settings-info-row {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) 2fr;
  gap: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--portal-border-faint);
  font-size: var(--portal-text-sm);
}

.pt-settings-info-row dt {
  color: var(--portal-text-secondary);
  margin: 0;
}
.pt-settings-info-row dd {
  color: var(--portal-text-primary);
  font-weight: var(--portal-font-medium);
  margin: 0;
}
</style>
