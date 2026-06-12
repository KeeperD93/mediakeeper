<template>
  <div class="pt-gdpr-pending">
    <div class="pt-gdpr-pending-head">
      <h4>
        {{ $t('portal.admin.settings.gdpr.pending.title') }}
        <span v-if="total">({{ total }})</span>
      </h4>
      <button
        type="button"
        class="pt-gdpr-pending-refresh"
        :disabled="loading || loadingMore"
        @click="$emit('refresh')"
      >
        <RefreshCw :size="14" />
        <span>{{ $t('common.refresh') }}</span>
      </button>
    </div>

    <p class="pt-gdpr-pending-desc">
      {{ $t('portal.admin.settings.gdpr.pending.desc') }}
    </p>

    <div v-if="loading" class="pt-gdpr-pending-loading">
      {{ $t('common.loading') }}
    </div>

    <div v-else-if="!rows.length" class="pt-gdpr-pending-empty">
      <ShieldCheck :size="20" />
      <span>{{ $t('portal.admin.settings.gdpr.pending.empty') }}</span>
    </div>

    <div v-else class="mk-table-wrap">
      <table class="pt-gdpr-pending-table mk-table">
        <thead>
          <tr>
            <th>{{ $t('portal.admin.settings.gdpr.pending.colUsername') }}</th>
            <th>{{ $t('portal.admin.settings.gdpr.pending.colRequestedAt') }}</th>
            <th>{{ $t('portal.admin.settings.gdpr.pending.colScheduledAt') }}</th>
            <th class="pt-gdpr-pending-th--act">
              {{ $t('portal.admin.settings.gdpr.pending.colAction') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td :data-label="$t('portal.admin.settings.gdpr.pending.colUsername')">
              <span class="pt-gdpr-pending-username">{{ row.username }}</span>
            </td>
            <td :data-label="$t('portal.admin.settings.gdpr.pending.colRequestedAt')">
              {{ formatDate(row.deletion_requested_at) }}
            </td>
            <td :data-label="$t('portal.admin.settings.gdpr.pending.colScheduledAt')">
              <span
                :class="[
                  'pt-gdpr-pending-scheduled',
                  isOverdue(row.pending_deletion_at) && 'pt-gdpr-pending-scheduled--overdue',
                ]"
              >
                {{ formatDate(row.pending_deletion_at) }}
              </span>
            </td>
            <td
              class="pt-gdpr-pending-td--act"
              :data-label="$t('portal.admin.settings.gdpr.pending.colAction')"
            >
              <button
                type="button"
                class="pt-gdpr-pending-cancel"
                :disabled="cancellingId !== null"
                @click="$emit('cancel', row)"
              >
                <Undo2 :size="14" />
                <span>{{ $t('portal.admin.settings.gdpr.pending.cancel') }}</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <PortalLoadMore :show="hasMore" :loading="loadingMore" @load="$emit('load-more')" />
  </div>
</template>

<script setup>
import { RefreshCw, ShieldCheck, Undo2 } from 'lucide-vue-next'
import PortalLoadMore from '@/components/portal/PortalLoadMore.vue'
import { localizedDateTime } from '@/utils/datetime'

import '@/assets/styles/portal/admin-gdpr.css'

defineProps({
  rows: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
  cancellingId: { type: Number, default: null },
})
defineEmits(['refresh', 'cancel', 'load-more'])

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  // Locale-aware (viewer's language): a fixed DD/MM/YYYY order is ambiguous
  // for an EN admin. Compact form — date + time, no seconds.
  return localizedDateTime(d, { dateStyle: 'short', timeStyle: 'short' })
}

function isOverdue(iso) {
  if (!iso) return false
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  return d.getTime() <= Date.now()
}
</script>

<!-- Styles externalised to assets/styles/portal/admin-gdpr.css -->
