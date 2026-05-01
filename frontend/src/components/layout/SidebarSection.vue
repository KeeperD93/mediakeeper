<template>
  <div class="sb-section" :class="{ collapsed }">
    <template v-if="!collapsed">
      <span class="sb-section-line sb-section-line-left" />
      <span class="sb-section-label">{{ label }}</span>
      <span class="sb-section-line sb-section-line-right" />
    </template>
    <div v-else class="sb-section-dot" />
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  collapsed: { type: Boolean, default: false },
})
</script>

<style scoped>
.sb-section {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 8px 8px;
  user-select: none;
}

.sb-section.collapsed {
  display: block;
  padding: 14px 0 8px;
}

.sb-section-label {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 1.6px;
  color: rgba(255, 255, 255, 0.55);
  flex-shrink: 0;
  text-shadow: 0 0 12px rgba(var(--accent-rgb), 0.25);
}

.sb-section-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--accent-rgb), 0.35) 50%,
    rgba(255, 255, 255, 0.04) 100%
  );
}

.sb-section-line-left {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.04) 0%,
    rgba(var(--accent-rgb), 0.35) 100%
  );
  max-width: 12px;
}

.sb-section-line-right {
  background: linear-gradient(
    90deg,
    rgba(var(--accent-rgb), 0.35) 0%,
    rgba(255, 255, 255, 0.04) 100%
  );
}

.sb-section-dot {
  width: 16px;
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--accent-rgb), 0.5) 50%,
    transparent 100%
  );
  margin: 0 auto;
}
</style>
