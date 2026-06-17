<template>
  <div class="aqh">
    <button
      type="button"
      class="aqh-toggle"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="open = !open"
    >
      <HelpCircle :size="15" />
      <span>{{ $t('portal.admin.settings.autoQuota.help.button') }}</span>
    </button>

    <div v-if="open" :id="panelId" class="aqh-panel">
      <p class="aqh-text">{{ $t('portal.admin.settings.autoQuota.help.intro') }}</p>
      <p class="aqh-text">{{ $t('portal.admin.settings.autoQuota.help.pace') }}</p>
      <p class="aqh-text">{{ $t('portal.admin.settings.autoQuota.help.scoreIntro') }}</p>
      <table class="aqh-table">
        <thead>
          <tr>
            <th>{{ $t('portal.admin.settings.autoQuota.help.colSignal') }}</th>
            <th>{{ $t('portal.admin.settings.autoQuota.help.colWeight') }}</th>
            <th>{{ $t('portal.admin.settings.autoQuota.help.colCap') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in SIGNALS" :key="s.key">
            <td>{{ $t(`portal.admin.settings.autoQuota.help.signals.${s.key}`) }}</td>
            <td>{{ s.weight.toFixed(1) }}</td>
            <td>{{ s.cap }}</td>
          </tr>
        </tbody>
      </table>
      <p class="aqh-note">{{ $t('portal.admin.settings.autoQuota.help.note') }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, useId } from 'vue'
import { HelpCircle } from 'lucide-vue-next'

// Engagement signals: weight × per-signal cap mirror
// services/portal/quota_auto._WEIGHTS / _CAPS (the fixed scoring shape).
const SIGNALS = [
  { key: 'play', weight: 1.0, cap: 20 },
  { key: 'login', weight: 0.5, cap: 15 },
  { key: 'request', weight: 0.4, cap: 10 },
  { key: 'list', weight: 0.6, cap: 5 },
  { key: 'ticket', weight: 0.3, cap: 5 },
]

const open = ref(false)
const panelId = useId()
</script>

<style scoped>
.aqh {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.aqh-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  align-self: flex-start;
  padding: 0.1rem 0;
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  cursor: pointer;
}
@media (hover: hover) {
  .aqh-toggle:hover {
    color: var(--text-primary);
  }
}
.aqh-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.aqh-panel {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.aqh-text {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
  line-height: 1.45;
}
.aqh-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.aqh-table th,
.aqh-table td {
  padding: 0.35rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.aqh-table th {
  color: var(--text-muted);
  font-weight: var(--font-medium);
}
.aqh-table td {
  color: var(--text-primary);
}
.aqh-table th:not(:first-child),
.aqh-table td:not(:first-child) {
  text-align: right;
}
.aqh-note {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
}
</style>
