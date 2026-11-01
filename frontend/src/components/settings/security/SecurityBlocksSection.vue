<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.security.blocksTitle') }}</h3>
      <div class="sec-hd-actions">
        <button type="button" class="sec-btn" @click="emit('refresh')">
          {{ t('common.refresh') }}
        </button>
        <button type="button" class="sec-btn" @click="emit('add')">
          {{ t('settings.security.addBlock') }}
        </button>
      </div>
    </header>
    <div v-if="!loaded && !failed" class="sec-loading">{{ t('common.loading') }}</div>
    <div v-else-if="!loaded" class="sec-empty">{{ t('settings.security.listUnavailable') }}</div>
    <div v-else-if="blocks.length" class="mk-table-wrap">
      <table class="sec-table mk-table">
        <thead>
          <tr>
            <th>{{ t('settings.security.target') }}</th>
            <th>{{ t('settings.security.scope') }}</th>
            <th>{{ t('settings.security.kind') }}</th>
            <th>{{ t('settings.security.until') }}</th>
            <th>{{ t('settings.security.reason') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in blocks" :key="b.id">
            <td :data-label="t('settings.security.target')">
              <div v-if="b.ip" class="sec-target">
                {{ t('settings.security.targetIp', { ip: displayIp(b.ip) }) }}
              </div>
              <div v-if="b.username" class="sec-target">@{{ b.username }}</div>
            </td>
            <td :data-label="t('settings.security.scope')">{{ scopeLabel(b.scope) }}</td>
            <td :data-label="t('settings.security.kind')">
              {{
                b.permanent ? t('settings.security.permanent') : t('settings.security.temporary')
              }}
            </td>
            <td :data-label="t('settings.security.until')">
              {{ b.blocked_until ? formatDate(b.blocked_until) : '—' }}
            </td>
            <td :data-label="t('settings.security.reason')">{{ reasonLabel(b) }}</td>
            <td>
              <button
                type="button"
                class="sec-btn-danger"
                :disabled="busy"
                @click="emit('unblock', b)"
              >
                {{ t('settings.security.unblock') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="sec-empty">{{ t('settings.security.noBlocks') }}</div>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  blocks: { type: Array, required: true },
  loaded: { type: Boolean, required: true },
  failed: { type: Boolean, required: true },
  busy: { type: Boolean, required: true },
  displayIp: { type: Function, required: true },
  formatDate: { type: Function, required: true },
  scopeLabel: { type: Function, required: true },
  reasonLabel: { type: Function, required: true },
})
const emit = defineEmits(['refresh', 'add', 'unblock'])

const { t } = useI18n()
</script>

<style scoped>
.sec-target {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
</style>
