<template>
  <div class="params-scheduler-tab">
    <h2 class="params-title">{{ $t('scheduler.title') }}</h2>
    <p class="params-desc">{{ $t('scheduler.desc') }}</p>

    <div v-if="schedLoading && !schedTasks.length" class="params-loading">
      <div v-for="i in 5" :key="i" class="params-skel" />
    </div>

    <div v-else class="sched-list">
      <div
        v-for="task in schedTasks.filter(t => t.key !== 'notifications')"
        :key="task.key"
        class="sched-card"
        :class="{ disabled: !task.enabled }"
      >
        <div class="sched-card-header">
          <div class="sched-card-left">
            <span class="sched-dot" :class="schedStatusDot(task)" />
            <div>
              <div class="sched-card-label">{{ task.label }}</div>
              <div class="sched-card-desc">{{ $t(task.description, task.description) }}</div>
            </div>
          </div>
          <div class="sched-card-right">
            <label class="sched-toggle">
              <input type="checkbox" :checked="task.enabled" @change="schedToggle(task)" />
              <span class="sched-toggle-track" />
            </label>
            <button class="sched-run-btn" :disabled="task._running" @click="schedRunNow(task)">
              <span v-if="task._running" class="mk-spin mk-spin-13" />
              <CirclePlay v-else :size="13" />
              {{ $t('scheduler.runNow') }}
            </button>
          </div>
        </div>

        <div class="sched-interval-row">
          <Clock :size="13" class="sched-clock-icon" />
          <span class="sched-interval-label">{{ $t('scheduler.every') }}</span>
          <input
            type="number"
            min="1"
            class="sched-interval-input"
            :value="
              schedEditValues[task.key]?.amount ??
              intervalToAmount(task.interval_sec, schedEditValues[task.key]?.unit ?? 'h')
            "
            @input="schedOnAmountChange(task.key, $event.target.value)"
          />
          <select
            class="sched-interval-select"
            :value="schedEditValues[task.key]?.unit ?? 'h'"
            @change="schedOnUnitChange(task.key, $event.target.value)"
          >
            <option value="s">{{ $t('scheduler.seconds') }}</option>
            <option value="m">{{ $t('scheduler.minutes') }}</option>
            <option value="h">{{ $t('scheduler.hours') }}</option>
            <option value="d">{{ $t('scheduler.days') }}</option>
          </select>
          <button v-if="schedIsDirty(task)" class="sched-save-btn" @click="schedSaveInterval(task)">
            {{ $t('common.save') }}
          </button>
          <button
            class="sched-reset-btn"
            :title="$t('scheduler.resetDefault', { v: formatSeconds(task.default_sec) })"
            @click="schedReset(task)"
          >
            {{ $t('scheduler.reset') }}
          </button>
        </div>

        <div v-if="task.progress && task.progress.total > 0" class="sched-progress">
          <div class="sched-progress-bar">
            <div
              class="sched-progress-fill"
              :style="{
                width: Math.round((task.progress.current / task.progress.total) * 100) + '%',
              }"
            />
          </div>
          <span class="sched-progress-text">
            {{ task.progress.current }}/{{ task.progress.total
            }}{{ task.progress.label ? ' — ' + task.progress.label : '' }}
          </span>
        </div>

        <div class="sched-meta">
          <span class="sched-last-run" :class="{ muted: !task.last_run }">
            {{
              task.last_run
                ? $t('scheduler.lastRun') + ' ' + formatRunDate(task.last_run)
                : $t('scheduler.neverRun')
            }}
          </span>
          <span class="sched-run-count">{{ $t('scheduler.runCount', { n: task.run_count }) }}</span>
          <span v-if="task.last_error" class="sched-last-error" :title="task.last_error">
            ⚠ {{ task.last_error.slice(0, 80) }}{{ task.last_error.length > 80 ? '…' : '' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onDeactivated, onUnmounted } from 'vue'
import { useParamsScheduler } from '@/composables/useParamsScheduler'
import { CirclePlay, Clock } from 'lucide-vue-next'

const {
  schedTasks,
  schedLoading,
  schedEditValues,
  intervalToAmount,
  formatSeconds,
  formatRunDate,
  schedStatusDot,
  schedIsDirty,
  ensureLoaded,
  stopPolling,
  schedToggle,
  schedSaveInterval,
  schedReset,
  schedRunNow,
  schedOnAmountChange,
  schedOnUnitChange,
} = useParamsScheduler()

onMounted(ensureLoaded)
onDeactivated(stopPolling)
onUnmounted(stopPolling)
</script>

<style scoped>
.sched-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 860px;
}
.sched-card {
  background: var(--bg-secondary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-card);
  padding: 16px 18px;
  transition: border-color var(--duration-fast);
}
.sched-card:hover {
  border-color: var(--border-hover);
}
.sched-card.disabled {
  opacity: 0.6;
}
.sched-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.sched-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.sched-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.sched-card-label {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.sched-card-desc {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 1px;
}
.sched-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-ok {
  background: #22c55e;
}
.dot-error {
  background: #f43f5e;
}
.dot-running {
  background: #f59e0b;
  animation: sched-pulse-dot 0.8s ease-in-out infinite alternate;
}
.dot-idle {
  background: var(--border-hover);
}
.dot-off {
  background: var(--border);
}
@keyframes sched-pulse-dot {
  from {
    opacity: 0.4;
  }
  to {
    opacity: 1;
  }
}
.sched-toggle {
  position: relative;
  display: inline-flex;
  cursor: pointer;
}
.sched-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.sched-toggle-track {
  display: inline-block;
  width: 34px;
  height: 18px;
  border-radius: var(--radius-pill);
  background: var(--border-hover);
  transition: background var(--duration-base);
  position: relative;
}
.sched-toggle-track::after {
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
.sched-toggle input:checked ~ .sched-toggle-track {
  background: var(--accent-500);
}
.sched-toggle input:checked ~ .sched-toggle-track::after {
  transform: translateX(16px);
}
.sched-run-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 11px;
  border-radius: var(--radius-sm);
  background: rgb(var(--accent-rgb), 0.1);
  border: 0.5px solid rgb(var(--accent-rgb), 0.2);
  color: var(--accent-400);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--duration-fast);
}
.sched-run-btn:hover:not(:disabled) {
  background: rgb(var(--accent-rgb), 0.2);
}
.sched-run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.sched-interval-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  background: var(--bg-primary);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-btn);
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.sched-clock-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}
.sched-interval-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}
.sched-interval-input {
  width: 58px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  text-align: center;
}
.sched-interval-input:focus {
  outline: none;
  border-color: var(--accent-500);
}
.sched-interval-select {
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  border: 0.5px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
}
.sched-save-btn {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: var(--accent-600);
  color: #fff;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.sched-save-btn:hover {
  background: var(--accent-500);
}
.sched-reset-btn {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 0.5px solid var(--border);
  color: var(--text-muted);
  font-size: var(--text-2xs);
  cursor: pointer;
  font-family: inherit;
  margin-left: auto;
}
.sched-reset-btn:hover {
  border-color: var(--border-hover);
  color: var(--text-secondary);
}
.sched-progress {
  margin-bottom: 10px;
}
.sched-progress-bar {
  height: 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  overflow: hidden;
  border: 0.5px solid var(--border);
}
.sched-progress-fill {
  height: 100%;
  background: var(--accent-500);
  border-radius: 3px;
  transition: width 0.4s ease;
  min-width: 2px;
}
.sched-progress-text {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 4px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sched-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.sched-last-run {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.sched-last-run.muted {
  opacity: 0.6;
}
.sched-run-count {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-left: auto;
}
.sched-last-error {
  font-size: var(--text-2xs);
  color: var(--color-error);
  background: rgb(var(--color-error-rgb), 0.08);
  padding: 2px 8px;
  border-radius: 5px;
}
</style>
