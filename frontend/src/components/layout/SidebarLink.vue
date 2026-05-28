<template>
  <component
    :is="expandable ? 'button' : 'router-link'"
    :to="expandable ? undefined : to"
    :type="expandable ? 'button' : undefined"
    class="sb-link"
    :class="{ active: isActive, collapsed, 'has-chevron': expandable && !collapsed }"
    :title="collapsed ? label + (badge > 0 ? ` (${badge})` : '') : undefined"
    :aria-expanded="expandable ? expanded : undefined"
    @click="onClick"
  >
    <span class="sb-indicator" />

    <span class="sb-icon">
      <component :is="iconComponent" :size="20" :stroke-width="1.8" />
    </span>

    <transition name="sb-label">
      <span v-if="!collapsed" class="sb-label-wrap">
        <span class="sb-label">{{ label }}</span>
        <span v-if="equalizer && badge > 0" class="sb-eq" aria-label="Sessions actives">
          <span class="sb-eq-bar sb-eq-1" />
          <span class="sb-eq-bar sb-eq-2" />
          <span class="sb-eq-bar sb-eq-3" />
        </span>
        <span v-if="expandable" class="sb-chevron" :class="{ open: expanded }" aria-hidden="true">
          <ChevronDown :size="10" :stroke-width="1.8" />
        </span>
      </span>
    </transition>

    <transition name="sb-badge-anim">
      <span
        v-if="badge > 0"
        class="sb-badge"
        :class="{ 'sb-badge-alert': badgeColor === 'red', 'sb-badge-collapsed': collapsed }"
      >
        {{ badge > 99 ? '99+' : badge }}
      </span>
    </transition>

    <span class="sb-hover-glow" />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  BarChart3,
  Bell,
  Captions,
  ChevronDown,
  ClipboardCheck,
  Copy,
  FileText,
  Film,
  Globe2,
  Home,
  MessageSquare,
  Settings,
  ShieldCheck,
  Users,
} from 'lucide-vue-next'

const props = defineProps({
  to: String,
  icon: String,
  label: String,
  collapsed: Boolean,
  badge: { type: Number, default: 0 },
  badgeColor: { type: String, default: 'indigo' },
  equalizer: { type: Boolean, default: false },
  exact: { type: Boolean, default: false },
  expandable: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
})

const emit = defineEmits(['navigate', 'toggle'])
const route = useRoute()

function onClick() {
  // Expandable modules (those with sub-tabs) toggle their sub-tab panel
  // instead of navigating, so the user can open the list while staying
  // on the current page. Plain links navigate as before.
  if (props.expandable) emit('toggle')
  else emit('navigate')
}

const isActive = computed(() => {
  if (props.to === '/') return route.path === '/'
  if (props.exact) return route.path === props.to
  return route.path === props.to || route.path.startsWith(props.to + '/')
})

const ICONS = {
  home: Home,
  media: Film,
  duplicates: Copy,
  notifications: Bell,
  tracker: Globe2,
  watchlist: ClipboardCheck,
  stats: BarChart3,
  portal: MessageSquare,
  settings: Settings,
  logs: FileText,
  healthcheck: ShieldCheck,
  subtitles: Captions,
  users: Users,
}

const iconComponent = computed(() => ICONS[props.icon] || ICONS.home)
</script>

<style scoped>
.sb-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 9px 12px;
  border-radius: var(--radius-btn);
  text-decoration: none;
  color: var(--text-muted);
  transition:
    color var(--duration-base) ease,
    background var(--duration-base) ease;
  overflow: hidden;
  margin: 1px 0;
  /* Button reset: expandable modules render as <button> (toggle sub-tabs
     without navigating); keep them visually identical to the <a>. */
  width: 100%;
  font: inherit;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  appearance: none;
}

.sb-link.collapsed {
  justify-content: center;
  padding: var(--space-2-5);
}

@media (hover: hover) {
  .sb-link:hover {
    color: var(--text-secondary);
    background: var(--surface-1);
  }
}
.sb-link:active {
  background: var(--surface-3);
}
@media (max-width: 1023px) {
  .sb-link {
    min-height: var(--touch-target);
    padding: var(--space-2-5) var(--space-3-5);
  }
  .sb-label {
    font-size: var(--text-base);
  }
}

.sb-link.active {
  color: var(--text-primary);
  /* Denser than the shared --gradient-pill-active: a primary nav selection
     needs more presence than a filter pill, and it must read at the default
     glow setting (--mk-glow: 0) where the halo below is invisible. */
  background: linear-gradient(
    135deg,
    rgb(var(--accent-rgb), 0.3),
    rgb(var(--accent-rgb), 0.14)
  );
  box-shadow: var(--mk-pill-shadow-sm);
}

.sb-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 0;
  border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, var(--accent-400), var(--accent-500));
  box-shadow:
    0 0 12px rgb(var(--accent-rgb), 0.5),
    0 0 24px rgb(var(--accent-rgb), 0.2);
  transition: height 0.25s var(--ease-in-out);
}

.sb-link.active .sb-indicator {
  height: 100%;
}

.sb-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  transition: color var(--duration-base);
}

.sb-link.active .sb-icon {
  color: var(--accent-300);
  filter: drop-shadow(0 0 6px rgb(var(--accent-rgb), 0.4));
}

.sb-label-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.sb-label {
  font-size: var(--text-sm);
  font-weight: 450;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.1px;
}

.sb-link.active .sb-label {
  font-weight: 550;
}

.sb-eq {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 12px;
  flex-shrink: 0;
}

.sb-eq-bar {
  width: 2.5px;
  border-radius: 1px;
  background: var(--color-success);
  will-change: height;
}

.sb-eq-1 {
  height: 4px;
  animation: sb-eq-bounce 0.8s ease-in-out infinite alternate;
}
.sb-eq-2 {
  height: 8px;
  animation: sb-eq-bounce 0.6s ease-in-out 0.15s infinite alternate;
}
.sb-eq-3 {
  height: 5px;
  animation: sb-eq-bounce 0.75s ease-in-out 0.3s infinite alternate;
}

@keyframes sb-eq-bounce {
  0% {
    height: 3px;
  }
  100% {
    height: 11px;
  }
}

.sb-badge {
  position: absolute;
  right: var(--space-2-5);
  top: 50%;
  transform: translateY(-50%);
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-btn);
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  line-height: 18px;
  text-align: center;
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  flex-shrink: 0;
}

.sb-badge-alert {
  background: rgb(var(--color-error-strong-rgb), 0.15);
  color: var(--color-error-light);
}

.sb-link.has-chevron .sb-badge:not(.sb-badge-collapsed) {
  right: 30px;
}

.sb-badge-collapsed {
  right: auto;
  top: 4px;
  left: 50%;
  transform: translateX(6px);
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  font-size: 8px;
  line-height: 14px;
  border-radius: var(--radius-sm);
}

.sb-badge-anim-enter-active {
  transition:
    opacity var(--duration-base),
    transform var(--duration-base);
}
.sb-badge-anim-leave-active {
  transition:
    opacity var(--duration-fast),
    transform var(--duration-fast);
}
.sb-badge-anim-enter-from {
  opacity: 0;
  transform: translateY(-50%) scale(0.5);
}
.sb-badge-anim-leave-to {
  opacity: 0;
  transform: translateY(-50%) scale(0.5);
}
.sb-badge-collapsed.sb-badge-anim-enter-from {
  transform: translateX(6px) scale(0.5);
}
.sb-badge-collapsed.sb-badge-anim-leave-to {
  transform: translateX(6px) scale(0.5);
}

.sb-hover-glow {
  position: absolute;
  inset: 0;
  border-radius: var(--radius-btn);
  opacity: 0;
  background: radial-gradient(circle at 50% 50%, rgb(var(--accent-rgb), 0.06) 0%, transparent 60%);
  transition: opacity var(--duration-slow);
  pointer-events: none;
}

.sb-link:hover .sb-hover-glow {
  opacity: 1;
}

.sb-label-enter-active {
  transition:
    opacity var(--duration-base) 0.08s,
    transform var(--duration-base) 0.08s;
}
.sb-label-leave-active {
  transition:
    opacity 0.12s,
    transform 0.12s;
}
.sb-label-enter-from {
  opacity: 0;
  transform: translateX(-6px);
}
.sb-label-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}

.sb-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  margin-left: auto;
  color: var(--text-faint);
  transition:
    transform var(--duration-base) ease,
    color var(--duration-base) ease;
}
.sb-chevron.open {
  transform: rotate(180deg);
  color: var(--accent-300);
}
.sb-link.active .sb-chevron {
  color: var(--text-secondary);
}
.sb-link.active .sb-chevron.open {
  color: var(--accent-300);
}
</style>
