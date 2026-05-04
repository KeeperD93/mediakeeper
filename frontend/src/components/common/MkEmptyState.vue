<template>
  <div class="mk-empty" :class="'mk-empty-' + size">
    <component :is="icon" v-if="icon" class="mk-empty-icon" :size="iconSize" :stroke-width="1.5" />
    <div class="mk-empty-title">{{ title }}</div>
    <div v-if="sub" class="mk-empty-sub">{{ sub }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: [Object, Function], default: null },
  title: { type: String, required: true },
  sub: { type: String, default: null },
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md'].includes(v),
  },
})

const iconSize = computed(() => (props.size === 'sm' ? 32 : 48))
</script>

<style scoped>
.mk-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px 16px;
  text-align: center;
}

.mk-empty-icon {
  color: var(--text-faint);
  flex-shrink: 0;
}

.mk-empty-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  text-align: center;
}

.mk-empty-sub {
  font-size: var(--text-xs);
  color: var(--text-faint);
  text-align: center;
  max-width: 320px;
  line-height: 1.5;
}

.mk-empty-sm .mk-empty-title {
  font-size: var(--text-sm);
}

.mk-empty-sm {
  gap: 8px;
  padding: 20px 12px;
}
</style>
