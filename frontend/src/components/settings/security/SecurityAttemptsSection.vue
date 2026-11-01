<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.security.attemptsTitle') }}</h3>
      <label class="sec-check">
        <input v-model="onlyFailures" type="checkbox" />
        {{ t('settings.security.onlyFailures') }}
      </label>
    </header>
    <div v-if="!loaded && !failed" class="sec-loading">{{ t('common.loading') }}</div>
    <div v-else-if="!loaded" class="sec-empty">{{ t('settings.security.listUnavailable') }}</div>
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
          <tr v-for="a in attempts" :key="a.id">
            <td :data-label="t('settings.security.when')">{{ formatDate(a.created_at) }}</td>
            <td :data-label="t('settings.security.ip')">{{ displayIp(a.ip) }}</td>
            <td :data-label="t('settings.security.username')">{{ a.username || '—' }}</td>
            <td :data-label="t('settings.security.scope')">{{ scopeLabel(a.scope) }}</td>
            <td :data-label="t('settings.security.result')">
              <span class="sec-result">
                <span class="sec-pill" :class="a.success ? 'is-ok' : 'is-fail'">
                  {{ a.success ? t('settings.security.success') : t('settings.security.failure') }}
                </span>
                <span v-if="a.cleared_at" class="sec-pill is-cleared">
                  {{ t('settings.security.cleared') }}
                </span>
              </span>
            </td>
            <td>
              <!-- Blocking the unknown marker would lock out every unreadable address. -->
              <button
                v-if="a.ip !== UNKNOWN_CLIENT_IP"
                type="button"
                class="sec-btn"
                :disabled="busy"
                @click="emit('block-ip', a)"
              >
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
import { UNKNOWN_CLIENT_IP } from '@/constants/security'

const onlyFailures = defineModel('onlyFailures', { type: Boolean, required: true })
defineProps({
  attempts: { type: Array, required: true },
  loaded: { type: Boolean, required: true },
  failed: { type: Boolean, required: true },
  busy: { type: Boolean, required: true },
  displayIp: { type: Function, required: true },
  formatDate: { type: Function, required: true },
  scopeLabel: { type: Function, required: true },
})
const emit = defineEmits(['block-ip'])

const { t } = useI18n()
</script>

<style scoped>
.sec-result {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.sec-pill {
  display: inline-block;
  padding: var(--space-half) var(--space-2);
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
.sec-pill.is-cleared {
  background: var(--surface-2);
  color: var(--text-muted);
}
.sec-check {
  position: relative;
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
  font-size: var(--text-sm);
}
/* A 44 px touch band on phones; the label keeps its look. */
.sec-check::after {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: var(--touch-target);
  transform: translateY(-50%);
}
@media (min-width: 768px) {
  .sec-check::after {
    content: none;
  }
}
</style>
