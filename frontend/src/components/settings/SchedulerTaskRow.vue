<template>
  <div class="str-row" :class="{ disabled: !task.enabled }">
    <div class="str-row-main">
      <label
        class="str-toggle"
        :aria-label="task.enabled ? $t('scheduler.disable') : $t('scheduler.enable')"
      >
        <input type="checkbox" :checked="task.enabled" @change="schedToggle(task)" />
        <span class="str-toggle-track" />
      </label>
      <span
        class="str-dot"
        :class="schedStatusDot(task)"
        role="img"
        :aria-label="statusAriaLabel"
      />
      <div class="str-row-title">
        <div class="str-label">
          {{ task.label_key ? $t(task.label_key, task.label) : task.label }}
        </div>
        <div class="str-meta">
          <span>
            {{
              task.last_run
                ? $t('scheduler.lastRun') + ' ' + formatRunDate(task.last_run)
                : $t('scheduler.neverRun')
            }}
          </span>
          <span class="str-meta-sep">·</span>
          <span>{{ $t('scheduler.runCount', { n: task.run_count }) }}</span>
          <span v-if="task.last_error" class="str-meta-error" :title="task.last_error">
            {{ $t('scheduler.lastError') }}
          </span>
        </div>
      </div>
      <div class="str-controls">
        <span class="str-interval-label">{{ $t('scheduler.every') }}</span>
        <input
          type="number"
          min="1"
          class="str-interval-amount"
          :aria-label="$t('scheduler.intervalAmountAria')"
          :value="
            schedEditValues[task.key]?.amount ??
            intervalToAmount(task.interval_sec, schedEditValues[task.key]?.unit ?? 'h')
          "
          @input="schedOnAmountChange(task.key, $event.target.value)"
        />
        <select
          class="str-interval-unit"
          :aria-label="$t('scheduler.intervalUnitAria')"
          :value="schedEditValues[task.key]?.unit ?? 'h'"
          @change="schedOnUnitChange(task.key, $event.target.value)"
        >
          <option value="s">{{ $t('scheduler.seconds') }}</option>
          <option value="m">{{ $t('scheduler.minutes') }}</option>
          <option value="h">{{ $t('scheduler.hours') }}</option>
          <option value="d">{{ $t('scheduler.days') }}</option>
        </select>
        <button v-if="schedIsDirty(task)" class="str-save-btn" @click="schedSaveInterval(task)">
          {{ $t('common.save') }}
        </button>
        <button
          class="str-run-btn"
          :disabled="task._running"
          :aria-label="$t('scheduler.runNow')"
          @click="schedRunNow(task)"
        >
          <span v-if="task._running" class="mk-spin mk-spin-13" />
          <CirclePlay v-else :size="13" />
          <span class="str-run-btn-label">{{ $t('scheduler.runNow') }}</span>
        </button>
        <button
          class="str-menu-btn"
          :aria-label="$t('scheduler.moreActions')"
          :aria-expanded="menuOpen"
          aria-haspopup="dialog"
          @click="toggleMenu"
        >
          <MoreVertical :size="14" />
        </button>
      </div>
    </div>
    <div v-if="task.progress && task.progress.total > 0" class="str-progress">
      <div class="str-progress-bar">
        <div class="str-progress-fill" :style="{ width: progressPercent + '%' }" />
      </div>
      <span class="str-progress-text">
        {{ task.progress.current }}/{{ task.progress.total
        }}{{ task.progress.label ? ' — ' + task.progress.label : '' }}
      </span>
    </div>
    <SchedulerTaskRowMenu
      v-if="menuOpen"
      :task="task"
      :format-seconds="formatSeconds"
      @close="menuOpen = false"
      @reset="onMenuReset"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CirclePlay, MoreVertical } from 'lucide-vue-next'
import SchedulerTaskRowMenu from './SchedulerTaskRowMenu.vue'
import '@/assets/styles/settings/scheduler-task-row.css'

const { t } = useI18n()

const props = defineProps({
  task: { type: Object, required: true },
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

const menuOpen = ref(false)
const progressPercent = computed(() => {
  const p = props.task.progress
  if (!p || !p.total) return 0
  return Math.round((p.current / p.total) * 100)
})

const statusAriaLabel = computed(() => {
  const dot = props.schedStatusDot(props.task)
  const map = {
    'dot-ok': 'scheduler.statusAria.ok',
    'dot-error': 'scheduler.statusAria.error',
    'dot-running': 'scheduler.statusAria.running',
    'dot-idle': 'scheduler.statusAria.idle',
    'dot-off': 'scheduler.statusAria.off',
  }
  return t(map[dot] ?? 'scheduler.statusAria.idle')
})

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}
function onMenuReset() {
  props.schedReset(props.task)
  menuOpen.value = false
}
</script>
