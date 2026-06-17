<template>
  <section class="set-section">
    <header class="set-section-head">
      <span v-if="icon" class="set-section-ico" aria-hidden="true">
        <component :is="icon" :size="18" />
      </span>
      <div class="set-section-heading">
        <h3 class="set-section-title">{{ title }}</h3>
        <p v-if="description" class="set-section-desc">{{ description }}</p>
      </div>
      <div v-if="$slots.action" class="set-section-action">
        <slot name="action" />
      </div>
    </header>
    <div class="set-section-body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
})
</script>

<style scoped>
.set-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.set-section-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.set-section-ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-input);
  background: rgb(var(--accent-rgb), 0.14);
  color: var(--accent);
}
.set-section-heading {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  flex: 1;
}
.set-section-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.set-section-desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
  line-height: 1.4;
}
.set-section-action {
  flex-shrink: 0;
}
.set-section-body {
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
</style>
