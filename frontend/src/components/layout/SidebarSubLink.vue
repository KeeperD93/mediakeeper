<template>
  <button
    type="button"
    class="sb-sublink"
    :class="{ active: isActive }"
    :title="label"
    @click="onClick"
  >
    <span class="sb-sublink-icon">
      <component :is="icon" :size="14" :stroke-width="1.8" />
    </span>
    <span class="sb-sublink-label">{{ label }}</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  parentPath: { type: String, required: true },
  tabId: { type: String, required: true },
  label: { type: String, required: true },
  icon: { type: [Object, Function], required: true },
  defaultTabId: { type: String, default: null },
})

const emit = defineEmits(['navigate'])
const route = useRoute()
const router = useRouter()

const onParentRoute = computed(
  () => route.path === props.parentPath || route.path.startsWith(props.parentPath + '/'),
)

const isActive = computed(() => {
  if (!onParentRoute.value) return false
  const current = route.query.tab
  if (current) return current === props.tabId
  // No `?tab=` yet — highlight the configured default tab so the
  // sidebar mirrors what the view renders on first paint.
  return props.defaultTabId === props.tabId
})

function onClick() {
  const target = { path: props.parentPath, query: { ...route.query, tab: props.tabId } }
  if (onParentRoute.value) {
    router.replace(target)
  } else {
    router.push(target)
  }
  emit('navigate')
}
</script>

<style scoped>
.sb-sublink {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 6px 10px 6px 28px;
  margin: 1px 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: 450;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  letter-spacing: -0.1px;
  transition:
    color var(--duration-base) ease,
    background var(--duration-base) ease;
}

@media (hover: hover) {
  .sb-sublink:hover {
    color: var(--text-secondary);
    background: var(--surface-2);
  }
}

.sb-sublink.active {
  color: var(--text-primary);
  background: rgb(var(--accent-rgb), 0.14);
}

.sb-sublink::before {
  content: '';
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-decorative);
  transition:
    background var(--duration-base) ease,
    box-shadow var(--duration-base) ease;
}

.sb-sublink.active::before {
  background: var(--accent-400);
  box-shadow: 0 0 8px rgb(var(--accent-rgb), 0.6);
}

.sb-sublink-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.85;
}

.sb-sublink.active .sb-sublink-icon {
  opacity: 1;
  color: var(--accent-300);
}

.sb-sublink-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1023px) {
  .sb-sublink {
    min-height: 38px;
    padding: 8px 12px 8px 30px;
    font-size: var(--text-sm);
  }
}
</style>
