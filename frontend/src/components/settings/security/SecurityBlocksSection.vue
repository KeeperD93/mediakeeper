<template>
  <section class="sec-block">
    <header class="sec-hd">
      <h3>{{ t('settings.security.blocksTitle') }}</h3>
      <button class="sec-btn" @click="emit('add')">
        {{ t('settings.security.addBlock') }}
      </button>
    </header>
    <div v-if="loading" class="sec-loading">{{ t('common.loading') }}</div>
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
              <div v-if="b.ip" class="sec-target">IP — {{ displayIp(b.ip) }}</div>
              <div v-if="b.username" class="sec-target">@{{ b.username }}</div>
            </td>
            <td :data-label="t('settings.security.scope')">{{ b.scope }}</td>
            <td :data-label="t('settings.security.kind')">
              {{
                b.permanent ? t('settings.security.permanent') : t('settings.security.temporary')
              }}
            </td>
            <td :data-label="t('settings.security.until')">
              {{ b.blocked_until ? formatDate(b.blocked_until) : '—' }}
            </td>
            <td :data-label="t('settings.security.reason')">{{ b.reason || '—' }}</td>
            <td>
              <button class="sec-btn-danger" @click="emit('unblock', b.id)">
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
  loading: { type: Boolean, default: false },
  displayIp: { type: Function, required: true },
  formatDate: { type: Function, required: true },
})
const emit = defineEmits(['add', 'unblock'])

const { t } = useI18n()
</script>

<style scoped>
.sec-target {
  font-family: monospace;
  font-size: var(--text-sm);
}
</style>
