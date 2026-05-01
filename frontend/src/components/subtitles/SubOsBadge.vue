<template>
  <span v-if="count !== null && count > 0" class="sub-os-badge" :title="$t('subtitles.availableSubs')">
    {{ count }} subs
  </span>
</template>

<script setup>
defineProps({
  count: { type: [Number, null], default: null },
})
</script>

<style scoped>
.sub-os-badge {
  font-size: .5rem; font-weight: var(--font-medium); padding: 1px 5px; border-radius: 3px;
  background: rgba(var(--accent-rgb),.1); color: var(--accent-400);
  white-space: nowrap;
}
</style>
