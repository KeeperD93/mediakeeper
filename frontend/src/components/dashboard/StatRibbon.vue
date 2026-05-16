<template>
  <div class="ribbon">
    <div class="ribbon-item">
      <span class="ribbon-label">{{ $t('dashboard.cpu') }}</span>
      <span class="ribbon-value" :style="{ color: colorByPct(sys.cpuPct) }">{{ sys.cpu }}</span>
      <svg
        v-if="cpuHistory.length > 2"
        class="spark"
        viewBox="0 0 100 28"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient :id="'cpuGrad'" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :style="{ stopColor: colorByPct(sys.cpuPct) }" stop-opacity="0.25" />
            <stop offset="100%" :style="{ stopColor: colorByPct(sys.cpuPct) }" stop-opacity="0" />
          </linearGradient>
        </defs>
        <polygon :points="areaPoints(cpuHistory)" :fill="'url(#cpuGrad)'" />
        <polyline
          :points="sparkPoints(cpuHistory)"
          fill="none"
          :style="{ stroke: colorByPct(sys.cpuPct) }"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </div>
    <div class="ribbon-item">
      <span class="ribbon-label">{{ $t('dashboard.ram') }}</span>
      <span class="ribbon-value" :style="{ color: colorByPct(sys.ramPct) }">{{ sys.ram }}</span>
      <svg
        v-if="ramHistory.length > 2"
        class="spark"
        viewBox="0 0 100 28"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient :id="'ramGrad'" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :style="{ stopColor: colorByPct(sys.ramPct) }" stop-opacity="0.25" />
            <stop offset="100%" :style="{ stopColor: colorByPct(sys.ramPct) }" stop-opacity="0" />
          </linearGradient>
        </defs>
        <polygon :points="areaPoints(ramHistory)" :fill="'url(#ramGrad)'" />
        <polyline
          :points="sparkPoints(ramHistory)"
          fill="none"
          :style="{ stroke: colorByPct(sys.ramPct) }"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </div>
    <div class="ribbon-item">
      <span class="ribbon-label">{{ $t('dashboard.storageLabel') }}</span>
      <span class="ribbon-value" :style="{ color: colorByPct(sys.storagePct) }">
        {{ sys.storage }}
      </span>
    </div>
    <!-- Services -->
    <div class="ribbon-item ribbon-svc">
      <span class="ribbon-label">Services</span>
      <div class="svc-list">
        <div v-for="svc in services" :key="svc.key" class="svc-row">
          <img
            v-if="svc.key === 'emby'"
            class="svc-logo"
            :class="{ 'svc-offline': !svc.online }"
            src="/assets/icons/emby.svg"
            alt="Emby"
          />
          <svg
            v-else-if="svc.key === 'plex'"
            class="svc-logo"
            :class="{ 'svc-offline': !svc.online }"
            viewBox="0 0 24 24"
            fill="none"
          >
            <path d="M3.5 3h6l8 9-8 9h-6l8-9-8-9z" fill="#E5A00D" />
          </svg>
          <svg
            v-else-if="svc.key === 'jellyfin'"
            class="svc-logo"
            :class="{ 'svc-offline': !svc.online }"
            viewBox="0 0 24 24"
            fill="none"
          >
            <path
              d="M12 2C8.5 5.5 5.5 8 4 12c1.5 4 4.5 6.5 8 10 3.5-3.5 6.5-6 8-10-1.5-4-4.5-6.5-8-10z"
              fill="#00A4DC"
            />
            <ellipse cx="12" cy="12" rx="3" ry="4.5" fill="#fff" opacity="0.25" />
          </svg>
          <span v-else class="svc-dot" :class="svc.online ? 'on' : 'off'" />
          <span class="svc-name">{{ svc.label }}</span>
          <span class="svc-status-wrap">
            <span class="svc-pulse" :class="svc.online ? 'pulse-on' : 'pulse-off'" />
            <span class="svc-status-text" :class="svc.online ? 'st-on' : 'st-off'">
              {{ svc.online ? 'En ligne' : 'Hors ligne' }}
            </span>
          </span>
        </div>
        <div v-if="services.length === 0" class="svc-row">
          <span class="svc-dot off" />
          <span class="svc-name svc-name-empty">{{ $t('dashboard.noService') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  sys: { type: Object, default: () => ({}) },
  cpuHistory: { type: Array, default: () => [] },
  ramHistory: { type: Array, default: () => [] },
  services: { type: Array, default: () => [] },
})

function colorByPct(p) {
  return p < 60 ? 'var(--color-success)' : p < 80 ? 'var(--color-warning)' : 'var(--color-error)'
}

function sparkPoints(data) {
  if (data.length < 2) return ''
  const max = Math.max(...data, 1)
  const step = 100 / (data.length - 1)
  return data.map((v, i) => `${Math.round(i * step)},${Math.round(26 - (v / max) * 24)}`).join(' ')
}

function areaPoints(data) {
  if (data.length < 2) return ''
  const max = Math.max(...data, 1)
  const step = 100 / (data.length - 1)
  const line = data.map((v, i) => `${Math.round(i * step)},${Math.round(26 - (v / max) * 24)}`)
  const last = Math.round((data.length - 1) * step)
  return `0,28 ${line.join(' ')} ${last},28`
}
</script>

<style scoped>
.ribbon {
  display: flex;
  flex-wrap: wrap;
  gap: 1px;
  background: var(--ribbon-gap, var(--surface-2));
  position: relative;
  z-index: 3;
}
.ribbon-item {
  flex: 1 1 33%;
  min-width: 0;
  padding: 10px 10px 8px;
  background: var(--ribbon-bg, #0b1020);
  display: flex; flex-direction: column; gap: 2px; position: relative; min-height: 60px;
}
.ribbon-label { font-size: var(--text-3xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.ribbon-value {
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  line-height: var(--lh-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.spark { width: 100%; height: 18px; margin-top: 2px; }

.ribbon-svc { flex: 1 1 100%; padding-bottom: 12px; }
.svc-list { display: flex; flex-direction: column; gap: 5px; margin-top: 6px; }
.svc-row { display: flex; align-items: center; gap: 8px; }
.svc-logo { width: 18px; height: 18px; flex-shrink: 0; transition: filter var(--duration-base); }
.svc-offline { filter: grayscale(1) opacity(0.4); }
.svc-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.on { background: #22c55e; }
.off { background: var(--color-error); }
.svc-name { font-size: var(--text-sm); color: var(--text-secondary); font-weight: var(--font-regular); }

/* Status with pulse */
.svc-status-wrap { display: flex; align-items: center; gap: 6px; margin-left: auto; }
.svc-pulse {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  position: relative;
}
.svc-pulse::after {
  content: ''; position: absolute; inset: -3px;
  border-radius: 50%; opacity: 0;
  animation: svc-ping var(--duration-pulse) ease-out infinite;
}
.pulse-on { background: #22c55e; }
.pulse-on::after { border: 2px solid #22c55e; }
.pulse-off { background: var(--color-error); }
.pulse-off::after { border: 2px solid var(--color-error); animation-duration: 3s; }

@keyframes svc-ping {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(2.2); opacity: 0; }
}

.svc-status-text { font-size: var(--text-2xs); }
.st-on { color: #22c55e; }
.st-off { color: var(--color-error); }
.svc-name-empty { opacity: 0.4; }

/* Desktop: 4 cells in a single row, taller items, larger value text. */
@media (min-width: 768px) {
  .ribbon { flex-wrap: nowrap; }
  .ribbon-item {
    flex: 1;
    padding: 14px 20px 10px;
    min-height: 72px;
  }
  .ribbon-label { font-size: var(--text-2xs); }
  .ribbon-value {
    font-size: 22px;
    line-height: normal;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }
  .spark { height: 28px; }
  .ribbon-svc { flex: initial; }
}
</style>
