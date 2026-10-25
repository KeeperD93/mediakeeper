<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.security.attemptsTitle') }}</h3>
      <label class="sec-check">
        <input v-model="onlyFailures" type="checkbox" @change="emit('filter-change')" />
        {{ t('settings.security.onlyFailures') }}
      </label>
    </header>
    <div v-if="loading" class="sec-loading">{{ t('common.loading') }}</div>
    <div v-else-if="attempts.length" class="mk-table-wrap">
      <table class="sec-table mk-table">
        <thead>
          <tr>
            <th>{{ t('settings.security.when') }}</th>
            <th>{{ t('settings.security.ip') }}</th>
            <th>{{ t('settings.security.username') }}</th>
            <th>{{ t('settings.security.scope') }}</th>
            <th>{{ t('settings.security.result') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in attempts" :key="a.id" :class="{ 'is-fail': !a.success }">
            <td :data-label="t('settings.security.when')">{{ formatDate(a.created_at) }}</td>
            <td :data-label="t('settings.security.ip')">{{ displayIp(a.ip) }}</td>
            <td :data-label="t('settings.security.username')">{{ a.username || '—' }}</td>
            <td :data-label="t('settings.security.scope')">{{ a.scope }}</td>
            <td :data-label="t('settings.security.result')">
              <span class="sec-pill" :class="a.success ? 'is-ok' : 'is-fail'">
                {{ a.success ? t('settings.security.success') : t('settings.security.failure') }}
              </span>
            </td>
            <td>
              <button class="sec-btn" @click="emit('block-ip', a)">
                {{ t('settings.security.blockIp') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="sec-empty">{{ t('settings.security.noAttempts') }}</div>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const onlyFailures = defineModel('onlyFailures', { type: Boolean, required: true })
defineProps({
  attempts: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  displayIp: { type: Function, required: true },
  formatDate: { type: Function, required: true },
})
const emit = defineEmits(['filter-change', 'block-ip'])

const { t } = useI18n()
</script>

<style scoped>
.sec-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
}
.sec-pill.is-ok {
  background: rgb(var(--color-success-rgb), 0.15);
  color: var(--color-success);
}
.sec-pill.is-fail {
  background: rgb(var(--color-error-strong-rgb), 0.15);
  color: var(--color-error-strong);
}
.sec-check {
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
  font-size: var(--text-sm);
}
</style>
