<template>
  <div class="set-row">
    <div class="set-row-info">
      <component
        :is="controlId ? 'label' : 'span'"
        :for="controlId || undefined"
        class="set-row-label"
      >
        {{ label }}
      </component>
      <p v-if="description" class="set-row-desc">{{ description }}</p>
    </div>
    <div class="set-row-control">
      <slot />
    </div>
  </div>
</template>

<script setup>
// ``controlId`` ties the row label to its control via <label for>; omit it for
// custom controls (e.g. a toggle) that carry their own aria-label.
defineProps({
  label: { type: String, required: true },
  description: { type: String, default: '' },
  controlId: { type: String, default: '' },
})
</script>

<style scoped>
.set-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1.25rem;
}
.set-row + .set-row {
  border-top: 1px solid var(--border);
}
.set-row-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}
.set-row-label {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.set-row-desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
}
.set-row-control {
  flex-shrink: 0;
}
</style>
