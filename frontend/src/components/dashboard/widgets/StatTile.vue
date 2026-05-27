<template>
  <component
    :is="route ? 'button' : 'div'"
    class="st-tile"
    :class="{ 'st-tile-click': !!route && !disabled, 'st-tile-static': !route }"
    :disabled="route ? disabled : null"
    :type="route ? 'button' : undefined"
    :style="{ '--st-accent': accent }"
    @click="onClick"
  >
    <div v-if="icon" class="st-tile-icon">
      <component :is="icon" :size="20" :stroke-width="2" />
    </div>
    <div class="st-tile-text">
      <span class="st-tile-label">{{ label }}</span>
      <span class="st-tile-val">{{ value }}</span>
    </div>
  </component>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  icon: { type: [Object, Function], default: null },
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  /* CSS color expression — hex OR ``var(--token)``. Drives the icon
   * frame tint, border and hover halo via color-mix at runtime. */
  accent: { type: String, default: 'var(--accent-500)' },
  /* Optional router target. Pass a string ("/path") or a location
   * object ({ path, query, name }). When omitted the tile renders as
   * a static div (cursor: default). */
  route: { type: [String, Object], default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])
const router = useRouter()

function onClick(e) {
  if (props.disabled) return
  emit('click', e)
  if (props.route) router.push(props.route)
}
</script>

<style scoped>
.st-tile {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  padding: var(--space-2-5) var(--space-3);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-default);
  border-radius: var(--radius-card);
  color: inherit;
  text-align: left;
  min-width: 0;
  min-height: var(--touch-target);
  transition:
    border-color var(--duration-base),
    background var(--duration-base),
    transform var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.st-tile-click {
  cursor: pointer;
}
.st-tile-static {
  cursor: default;
}
@media (hover: hover) {
  /* Visual feedback on hover even for non-clickable tiles — keeps the
     grid alive and lets every tile read as part of the same family.
     Cursor stays ``default`` on static tiles (handled inline) so users
     don't expect a navigation that doesn't exist. */
  .st-tile:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--st-accent) 35%, transparent);
    background: color-mix(in srgb, var(--st-accent) 5%, transparent);
  }
  .st-tile:not(:disabled):hover .st-tile-icon {
    background: color-mix(in srgb, var(--st-accent) 26%, transparent);
    border-color: color-mix(in srgb, var(--st-accent) 45%, transparent);
  }
}
.st-tile-click:not(:disabled):active {
  transform: scale(0.98);
}

.st-tile-icon {
  flex-shrink: 0;
  width: var(--icon-frame-md);
  height: var(--icon-frame-md);
  border-radius: var(--radius-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--st-accent);
  background: color-mix(in srgb, var(--st-accent) 18%, transparent);
  border: var(--border-width) solid color-mix(in srgb, var(--st-accent) 28%, transparent);
  transition:
    background var(--duration-base),
    border-color var(--duration-base);
}

.st-tile-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.st-tile-label {
  display: block;
  font-size: var(--text-3xs);
  line-height: var(--lh-snug-tight);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.st-tile-val {
  display: block;
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  line-height: var(--lh-tight);
  color: var(--text-primary);
  margin-top: var(--space-half);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
