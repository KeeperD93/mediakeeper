<template>
  <div class="ru-stats-banner">
    <button
      class="ru-stats-card"
      :class="{ 'is-active': active === 'all' }"
      @click="$emit('apply', { status: STATUS_FILTER.ALL, expires_within: null })"
    >
      <span class="ru-stats-val">{{ stats?.total ?? 0 }}</span>
      <span class="ru-stats-label">{{ $t('requestsAdmin.users.stats.total') }}</span>
    </button>
    <button
      class="ru-stats-card ru-stats-card--success"
      :class="{ 'is-active': active === 'active' }"
      @click="$emit('apply', { status: STATUS_FILTER.ACTIVE, expires_within: null })"
    >
      <span class="ru-stats-val">{{ stats?.active ?? 0 }}</span>
      <span class="ru-stats-label">{{ $t('requestsAdmin.users.stats.active') }}</span>
    </button>
    <button
      class="ru-stats-card ru-stats-card--muted"
      :class="{ 'is-active': active === 'inactive' }"
      @click="$emit('apply', { status: STATUS_FILTER.INACTIVE, expires_within: null })"
    >
      <span class="ru-stats-val">{{ stats?.inactive ?? 0 }}</span>
      <span class="ru-stats-label">{{ $t('requestsAdmin.users.stats.inactive') }}</span>
    </button>
    <button
      class="ru-stats-card ru-stats-card--warn"
      :class="{ 'is-active': active === 'expiring' }"
      @click="$emit('apply', { status: STATUS_FILTER.ALL, expires_within: EXPIRY_WARNING_DAYS })"
    >
      <span class="ru-stats-val">{{ stats?.expiring_soon ?? 0 }}</span>
      <span class="ru-stats-label">{{ $t('requestsAdmin.users.stats.expiringSoon') }}</span>
    </button>
    <button
      class="ru-stats-card ru-stats-card--danger"
      :class="{ 'is-active': active === 'expired' }"
      @click="$emit('apply', { status: STATUS_FILTER.EXPIRED, expires_within: null })"
    >
      <span class="ru-stats-val">{{ stats?.expired ?? 0 }}</span>
      <span class="ru-stats-label">{{ $t('requestsAdmin.users.stats.expired') }}</span>
    </button>
  </div>
</template>

<script setup>
import { STATUS_FILTER, EXPIRY_WARNING_DAYS } from '@/constants/portalAdminUsers'

defineProps({
  stats: { type: Object, default: null },
  active: { type: String, default: '' },
})
defineEmits(['apply'])
</script>

<style scoped>
.ru-stats-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.5rem;
}
.ru-stats-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  padding: 0.65rem 0.85rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  color: var(--text-primary);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background 160ms ease,
    transform 160ms ease;
  text-align: left;
  font: inherit;
}
.ru-stats-card:hover {
  border-color: rgb(var(--accent-rgb), 0.45);
  transform: translateY(-1px);
}
.ru-stats-card.is-active {
  border-color: var(--accent);
  background: rgb(var(--accent-rgb), 0.08);
}
.ru-stats-val {
  font-size: var(--text-xl);
  font-weight: var(--font-extrabold);
  font-variant-numeric: tabular-nums;
}
.ru-stats-label {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color: var(--text-muted);
  font-weight: var(--font-bold);
}
.ru-stats-card--success .ru-stats-val {
  color: #22c55e;
}
.ru-stats-card--muted .ru-stats-val {
  color: #9ca3af;
}
.ru-stats-card--warn .ru-stats-val {
  color: #f59e0b;
}
.ru-stats-card--danger .ru-stats-val {
  color: #ef4444;
}
</style>
