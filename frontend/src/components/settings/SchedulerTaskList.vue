<template>
  <div v-if="schedLoading && !schedTasks.length" class="stl-skel-wrap">
    <div v-for="i in 5" :key="i" class="stl-skel" />
  </div>

  <div v-else class="stl-list">
    <section v-for="group in groupedTasks" :key="group.category" class="stl-category">
      <h3 class="stl-category-title">
        {{ $t(SCHEDULER_CATEGORIES[group.category].labelKey) }}
      </h3>
      <div class="stl-category-rows">
        <SchedulerTaskRow
          v-for="task in group.tasks"
          :key="task.key"
          :task="task"
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
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SchedulerTaskRow from './SchedulerTaskRow.vue'
import {
  SCHEDULER_CATEGORIES,
  groupTasksByCategory,
  HIDDEN_TASK_KEYS,
} from '@/constants/schedulerCategories'
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

const visibleTasks = computed(() => props.schedTasks.filter(t => !HIDDEN_TASK_KEYS.includes(t.key)))

const groupedTasks = computed(() => groupTasksByCategory(visibleTasks.value))
</script>
