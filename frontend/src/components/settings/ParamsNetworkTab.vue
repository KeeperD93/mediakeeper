<template>
  <div class="params-network-tab">
    <h2 class="params-title">{{ $t('settings.network.title') }}</h2>
    <p class="params-desc">{{ $t('settings.network.desc') }}</p>

    <div v-if="loading" class="pn-loading">
      <div v-for="i in 3" :key="i" class="pn-skel" />
    </div>

    <div v-else class="pn-list">
      <!-- Cache d'images -->
      <div class="pn-card">
        <div class="pn-card-head">
          <div class="pn-card-text">
            <div class="pn-card-label">{{ $t('settings.network.imageCache.label') }}</div>
            <p class="pn-card-desc">{{ $t('settings.network.imageCache.desc') }}</p>
          </div>
          <label class="pn-toggle">
            <input
              type="checkbox"
              :checked="form.image_cache_enabled"
              :disabled="saving"
              @change="onToggleImage($event.target.checked)"
            />
            <span class="pn-toggle-track" />
          </label>
        </div>
      </div>

      <!-- Cache DNS -->
      <div class="pn-card">
        <div class="pn-card-head">
          <div class="pn-card-text">
            <div class="pn-card-label">{{ $t('settings.network.dnsCache.label') }}</div>
            <p class="pn-card-desc">{{ $t('settings.network.dnsCache.desc') }}</p>
          </div>
          <label class="pn-toggle">
            <input
              type="checkbox"
              :checked="form.dns_cache_enabled"
              :disabled="saving"
              @change="onToggleDns($event.target.checked)"
            />
            <span class="pn-toggle-track" />
          </label>
        </div>

        <div v-if="form.dns_cache_enabled" class="pn-sub-row">
          <label class="pn-sub-label" for="pn-dns-ttl">
            {{ $t('settings.network.dnsCache.ttlLabel') }}
          </label>
          <input
            id="pn-dns-ttl"
            type="number"
            min="1"
            class="pn-sub-input"
            :value="form.dns_cache_ttl_seconds"
            :disabled="saving"
            @change="onTtlChange($event.target.value)"
          />
          <span class="pn-sub-unit">{{ $t('settings.network.dnsCache.ttlUnit') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'

const { apiGet, apiFetch } = useApi()
const { showToast } = useToast()
const { t } = useI18n()

const loading = ref(true)
const saving = ref(false)
const form = reactive({
  image_cache_enabled: false,
  dns_cache_enabled: false,
  dns_cache_ttl_seconds: 300,
})

async function load() {
  loading.value = true
  try {
    const data = await apiGet('/api/settings/network')
    form.image_cache_enabled = !!data?.image_cache_enabled
    form.dns_cache_enabled = !!data?.dns_cache_enabled
    form.dns_cache_ttl_seconds = Number(data?.dns_cache_ttl_seconds) || 300
  } catch (e) {
    console.error('[ParamsNetworkTab.load] failed', e)
  }
  loading.value = false
}

async function save(patch) {
  saving.value = true
  try {
    const res = await apiFetch('/api/settings/network', {
      method: 'PUT',
      body: JSON.stringify(patch),
    })
    const data = await res.json()
    if (data?.success) {
      showToast(t('settings.network.saved'), TOAST_TYPE.OK)
    } else {
      showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
    }
  } catch (e) {
    console.error('[ParamsNetworkTab.save] failed', e)
    showToast(t('common.apiError.submitFailed'), TOAST_TYPE.ERR)
  }
  saving.value = false
}

function onToggleImage(value) {
  form.image_cache_enabled = value
  save({ image_cache_enabled: value })
}

function onToggleDns(value) {
  form.dns_cache_enabled = value
  save({ dns_cache_enabled: value })
}

function onTtlChange(raw) {
  const ttl = Math.max(1, parseInt(raw, 10) || 300)
  form.dns_cache_ttl_seconds = ttl
  save({ dns_cache_ttl_seconds: ttl })
}

onMounted(load)
</script>

<style scoped>
.pn-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 820px;
}
.pn-loading {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 820px;
}
.pn-skel {
  height: 76px;
  border-radius: var(--radius-card);
  background: var(--bg-secondary);
  opacity: 0.6;
  animation: pn-skel-pulse 1.4s ease-in-out infinite;
}
@keyframes pn-skel-pulse {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.7;
  }
}
.pn-card {
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
  padding: 16px 18px;
}
.pn-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.pn-card-text {
  flex: 1;
  min-width: 0;
}
.pn-card-label {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.pn-card-desc {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin: 4px 0 0;
}
.pn-toggle {
  position: relative;
  display: inline-flex;
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}
.pn-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.pn-toggle input:disabled {
  cursor: not-allowed;
}
.pn-toggle-track {
  display: inline-block;
  width: 34px;
  height: 18px;
  border-radius: var(--radius-pill);
  background: var(--border-hover);
  transition: background var(--duration-base);
  position: relative;
}
.pn-toggle-track::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: transform var(--duration-base);
}
.pn-toggle input:checked ~ .pn-toggle-track {
  background: var(--accent-500);
}
.pn-toggle input:checked ~ .pn-toggle-track::after {
  transform: translateX(16px);
}
.pn-sub-row {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 0.5px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.pn-sub-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.pn-sub-input {
  width: 88px;
  padding: 5px 9px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  text-align: center;
}
.pn-sub-input:focus {
  outline: none;
  border-color: var(--accent-500);
}
.pn-sub-unit {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

@media (max-width: 767px) {
  .pn-sub-input {
    min-height: 44px;
  }
}
</style>
