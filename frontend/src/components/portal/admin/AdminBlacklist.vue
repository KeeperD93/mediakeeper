<template>
  <div class="ab-wrap">
    <p v-if="loading" class="ab-state">{{ $t('common.loading') }}</p>
    <p v-else-if="!items.length" class="ab-state">
      {{ $t('portal.admin.blacklist.empty') || 'No blocked media' }}
    </p>

    <div v-else class="ab-grid">
      <div v-for="bl in items" :key="bl.id" class="ab-row">
        <div class="ab-poster">
          <img v-if="bl.poster_url" :src="bl.poster_url" :alt="bl.title" />
          <div v-else class="ab-poster-ph">🎬</div>
        </div>
        <div class="ab-info">
          <div class="ab-title">
            {{ bl.title }}
            <span v-if="bl.year" class="ab-year">({{ bl.year }})</span>
          </div>
          <div class="ab-meta">
            <span class="ab-pill ab-pill--type">
              {{ isTv(bl) ? $t('portal.type.tv') : $t('portal.type.movie') }}
            </span>
            <span class="ab-pill">
              {{ bl.reject_count }} {{ $t('portal.admin.blacklist.rejections') || 'rejections' }}
            </span>
            <span v-if="bl.blocked_at" class="ab-pill ab-pill--date">
              {{ fmtDate(bl.blocked_at) }}
            </span>
          </div>
          <div v-if="bl.requesters?.length" class="ab-requesters">
            <span class="ab-requesters-label">
              {{ $t('portal.admin.blacklist.requesters') || 'Requested by' }}:
            </span>
            <span v-for="(r, i) in bl.requesters" :key="r.user_id" class="ab-requester">
              {{ r.display_name }}
              <span v-if="i < bl.requesters.length - 1">,</span>
            </span>
          </div>
        </div>
        <button class="ab-unblock" :disabled="busyId === bl.id" @click="unblock(bl)">
          {{
            busyId === bl.id
              ? $t('common.loading')
              : $t('portal.admin.blacklist.unblock') || 'Unblock'
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { isTv } from '@/constants/media'
import { localizedDate } from '@/utils/datetime'

const { t } = useI18n()
const { apiGet, apiDelete } = useApi()
const { showToast } = useToast()

const items = ref([])
const loading = ref(true)
const busyId = ref(null)

async function fetchList() {
  loading.value = true
  const res = await apiGet('/api/portal/requests/admin/blacklist').catch(() => null)
  items.value = res?.items || []
  loading.value = false
}

async function unblock(bl) {
  busyId.value = bl.id
  const res = await apiDelete(`/api/portal/requests/admin/blacklist/${bl.id}`).catch(() => null)
  busyId.value = null
  if (res?.success) {
    showToast(t('portal.admin.blacklist.unblocked') || 'Media unblocked', TOAST_TYPE.OK)
    await fetchList()
  } else {
    showToast(t('common.error'), TOAST_TYPE.ERR)
  }
}

function fmtDate(iso) {
  if (!iso) return ''
  return localizedDate(new Date(iso))
}

onMounted(fetchList)
</script>

<style scoped>
.ab-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.ab-state {
  font-size: var(--portal-text-sm);
  color: var(--text-muted);
  text-align: center;
  padding: 2rem 1rem;
}
.ab-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.ab-row {
  display: grid;
  grid-template-columns: 70px 1fr auto;
  gap: 0.9rem;
  align-items: center;
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.ab-poster {
  width: 70px;
  height: 100px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--portal-surface-2);
}
.ab-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ab-poster-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--portal-text-2xl);
  opacity: 0.3;
}
.ab-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.ab-title {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.ab-year {
  color: var(--text-muted);
  font-weight: var(--portal-font-regular);
}
.ab-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.ab-pill {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  padding: 2px 8px;
  border-radius: var(--radius-input);
  background: var(--portal-surface-3);
  color: var(--portal-text-body-muted);
  border: 1px solid var(--portal-border-default);
  letter-spacing: var(--portal-tracking-wide);
}
.ab-pill--type {
  background: rgb(99, 102, 241, 0.15);
  border-color: rgb(99, 102, 241, 0.3);
  color: var(--accent-300);
}
.ab-pill--date {
  background: transparent;
  border-color: transparent;
  color: var(--portal-text-muted);
}
.ab-requesters {
  font-size: var(--portal-text-xs);
  color: var(--portal-text-secondary);
}
.ab-requesters-label {
  font-weight: var(--portal-font-medium);
  color: rgb(255, 255, 255, 0.45);
  margin-right: 0.25rem;
}
.ab-requester {
  color: var(--portal-text-body-muted);
  margin-right: 0.15rem;
}
.ab-unblock {
  padding: 0.55rem 1rem;
  border-radius: var(--radius-btn);
  border: 1px solid rgb(var(--portal-color-success-rgb), 0.4);
  background: rgb(var(--portal-color-success-rgb), 0.15);
  color: var(--portal-color-success-soft);
  font-size: var(--portal-text-sm);
  font-weight: var(--portal-font-bold);
  cursor: pointer;
  white-space: nowrap;
}
.ab-unblock:hover:not(:disabled) {
  background: rgb(var(--portal-color-success-rgb), 0.25);
}
.ab-unblock:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
