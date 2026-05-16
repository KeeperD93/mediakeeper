<template>
  <div class="params-scheduler-tab">
    <h2 class="params-title">{{ $t('scheduler.title') }}</h2>
    <p class="params-desc">{{ $t('scheduler.desc') }}</p>

    <SchedulerTaskList
      :sched-tasks="schedTasks"
      :sched-loading="schedLoading"
      :sched-edit-values="schedEditValues"
      :interval-to-amount="intervalToAmount"
      :format-seconds="formatSeconds"
      :format-run-date="formatRunDate"
      :sched-status-dot="schedStatusDot"
      :sched-is-dirty="schedIsDirty"
      :sched-toggle="schedToggle"
      :sched-save-interval="schedSaveInterval"
      :sched-reset="schedReset"
      :sched-run-now="schedRunNow"
      :sched-on-amount-change="schedOnAmountChange"
      :sched-on-unit-change="schedOnUnitChange"
    />

    <SchedulerCacheList
      :sched-caches="schedCaches"
      :sched-caches-loading="schedCachesLoading"
      :sched-clear-cache="schedClearCache"
    />
  </div>
</template>

<script setup>
import { onMounted, onDeactivated, onUnmounted } from 'vue'
import { useParamsScheduler } from '@/composables/useParamsScheduler'
import SchedulerTaskList from '@/components/settings/SchedulerTaskList.vue'
import SchedulerCacheList from '@/components/settings/SchedulerCacheList.vue'

const {
  schedTasks,
  schedCaches,
  schedLoading,
  schedCachesLoading,
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
  schedClearCache,
  schedOnAmountChange,
  schedOnUnitChange,
} = useParamsScheduler()

onMounted(ensureLoaded)
onDeactivated(stopPolling)
onUnmounted(stopPolling)
</script>
