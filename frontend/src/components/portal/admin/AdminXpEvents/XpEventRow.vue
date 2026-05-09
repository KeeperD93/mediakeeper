<template>
  <div
    class="pt-xp-row"
    :class="{ 'pt-xp-row--active': ev.is_active }"
  >
    <span
      class="pt-xp-status"
      :class="{ 'pt-xp-status--on': ev.is_active }"
      :title="
        ev.is_active
          ? $t('portal.admin.xpEvents.active')
          : ev.enabled
            ? $t('portal.admin.xpEvents.scheduled')
            : $t('portal.admin.xpEvents.disabled')
      "
    >
      ●
    </span>
    <span class="pt-xp-mult">×{{ ev.multiplier }}</span>
    <div class="pt-xp-info">
      <div class="pt-xp-name">{{ ev.name }}</div>
      <div class="pt-xp-dates">
        {{ formatDate(ev.starts_at) }} → {{ formatDate(ev.ends_at) }}
      </div>
      <div v-if="ev.action_filter" class="pt-xp-filters">
        <span
          v-for="a in ev.action_filter
            .split(',')
            .map(s => s.trim())
            .filter(Boolean)"
          :key="a"
          class="pt-xp-filter"
        >
          {{ $t(`portal.admin.xpEvents.actions.${a}`, a) }}
        </span>
      </div>
    </div>
    <button class="pt-icon-btn" :title="$t('common.edit')" @click="$emit('edit', ev)">✎</button>
    <button
      class="pt-icon-btn pt-icon-btn--danger"
      :title="$t('common.delete')"
      @click="$emit('remove', ev.id)"
    >
      <Trash2 :size="14" />
    </button>
  </div>
</template>

<script setup>
import { Trash2 } from 'lucide-vue-next'

defineProps({
  ev: { type: Object, required: true },
  formatDate: { type: Function, required: true },
})
defineEmits(['edit', 'remove'])
</script>

<style scoped>
.pt-xp-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-xp-row--active {
  background: rgb(var(--accent-rgb), 0.06);
}
.pt-xp-status {
  font-size: var(--portal-text-md);
  color: var(--text-muted);
}
.pt-xp-status--on {
  color: var(--portal-color-success);
  text-shadow: 0 0 6px rgb(var(--portal-color-success-rgb), 0.5);
}
.pt-xp-mult {
  font-weight: var(--portal-font-extrabold);
  font-size: var(--portal-text-base);
  color: var(--accent);
  font-family: var(--portal-font-display);
  min-width: 40px;
}
.pt-xp-info {
  min-width: 0;
}
.pt-xp-name {
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  font-size: var(--portal-text-base);
}
.pt-xp-dates {
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.pt-xp-filters {
  grid-column: 3;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.25rem;
}
.pt-xp-filter {
  background: rgb(var(--accent-rgb), 0.12);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: var(--portal-radius-xs);
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-medium);
}
.pt-icon-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--portal-text-md);
  padding: 0.25rem 0.5rem;
  border-radius: var(--portal-radius-xs);
}
.pt-icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.pt-icon-btn--danger:hover {
  color: var(--portal-color-error);
}
</style>
