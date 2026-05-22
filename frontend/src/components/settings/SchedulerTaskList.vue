<template>
  <div v-if="schedLoading && !schedTasks.length" class="stl-skel-wrap">
    <div v-for="i in 5" :key="i" class="stl-skel" />
  </div>

  <div v-else class="stl-list">
    <div
      v-for="task in visibleTasks"
      :key="task.key"
      class="stl-card"
      :class="{ disabled: !task.enabled }"
    >
      <div class="stl-card-header">
        <div class="stl-card-left">
          <span class="stl-dot" :class="schedStatusDot(task)" />
          <div>
            <div class="stl-card-label">
              {{ task.label_key ? $t(task.label_key, task.label) : task.label }}
            </div>
            <div class="stl-card-desc">{{ $t(task.description, task.description) }}</div>
          </div>
        </div>
        <div class="stl-card-right">
          <label class="stl-toggle">
            <input type="checkbox" :checked="task.enabled" @change="schedToggle(task)" />
            <span class="stl-toggle-track" />
          </label>
          <button class="stl-run-btn" :disabled="task._running" @click="schedRunNow(task)">
            <span v-if="task._running" class="mk-spin mk-spin-13" />
            <CirclePlay v-else :size="13" />
            {{ $t('scheduler.runNow') }}
          </button>
        </div>
      </div>

      <div class="stl-interval-row">
        <Clock :size="13" class="stl-clock-icon" />
        <span class="stl-interval-label">{{ $t('scheduler.every') }}</span>
        <input
          type="number"
          min="1"
          class="stl-interval-input"
          :value="
            schedEditValues[task.key]?.amount ??
            intervalToAmount(task.interval_sec, schedEditValues[task.key]?.unit ?? 'h')
          "
          @input="schedOnAmountChange(task.key, $event.target.value)"
        />
        <select
          class="stl-interval-select"
          :value="schedEditValues[task.key]?.unit ?? 'h'"
          @change="schedOnUnitChange(task.key, $event.target.value)"
        >
          <option value="s">{{ $t('scheduler.seconds') }}</option>
          <option value="m">{{ $t('scheduler.minutes') }}</option>
          <option value="h">{{ $t('scheduler.hours') }}</option>
          <option value="d">{{ $t('scheduler.days') }}</option>
        </select>
        <button v-if="schedIsDirty(task)" class="stl-save-btn" @click="schedSaveInterval(task)">
          {{ $t('common.save') }}
        </button>
        <button
          class="stl-reset-btn"
          :title="$t('scheduler.resetDefault', { v: formatSeconds(task.default_sec) })"
          @click="schedReset(task)"
        >
          {{ $t('scheduler.reset') }}
        </button>
      </div>

      <div v-if="task.progress && task.progress.total > 0" class="stl-progress">
        <div class="stl-progress-bar">
          <div
            class="stl-progress-fill"
            :style="{
              width: Math.round((task.progress.current / task.progress.total) * 100) + '%',
            }"
          />
        </div>
        <span class="stl-progress-text">
          {{ task.progress.current }}/{{ task.progress.total
          }}{{ task.progress.label ? ' — ' + task.progress.label : '' }}
        </span>
      </div>

      <div class="stl-meta">
        <span class="stl-last-run" :class="{ muted: !task.last_run }">
          {{
            task.last_run
              ? $t('scheduler.lastRun') + ' ' + formatRunDate(task.last_run)
              : $t('scheduler.neverRun')
          }}
        </span>
        <span class="stl-run-count">{{ $t('scheduler.runCount', { n: task.run_count }) }}</span>
        <span v-if="task.last_error" class="stl-last-error" :title="task.last_error">
          ⚠ {{ task.last_error.slice(0, 80) }}{{ task.last_error.length > 80 ? '…' : '' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CirclePlay, Clock } from 'lucide-vue-next'
import '@/assets/styles/settings/scheduler-task-list.css'

const props = defineProps({
  schedTasks: { type: Array, required: true },
  schedLoading: { type: Boolean, default: false },
  schedEditValues: { type: Object, required: true },
  intervalToAmount: { type: Function, required: true },
  formatSeconds: { type: Function, required: true },
  formatRunDate: { type: Function, required: true },
  schedStatusDot: { type: Function, required: true },
  schedIsDirty: { type: Function, required: true },
  schedToggle: { type: Function, required: true },
  schedSaveInterval: { type: Function, required: true },
  schedReset: { type: Function, required: true },
  schedRunNow: { type: Function, required: true },
  schedOnAmountChange: { type: Function, required: true },
  schedOnUnitChange: { type: Function, required: true },
})

// The "notifications" task is housekeeping for the in-app
// notification queue — it runs every minute and admins have no
// reason to surface it next to the other tasks.
const visibleTasks = computed(() =>
  props.schedTasks.filter(t => t.key !== 'notifications'),
)
</script>

