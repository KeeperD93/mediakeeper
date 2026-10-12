<template>
  <a
    v-if="releaseHref"
    :href="releaseHref"
    target="_blank"
    rel="noopener noreferrer"
    class="sb-update"
    :title="label"
    :aria-label="label"
  >
    <CircleArrowUp :size="collapsed ? 16 : 12" :stroke-width="2" aria-hidden="true" />
    <span v-if="!collapsed">{{ t('sidebar.updateAvailable', { version }) }}</span>
  </a>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleArrowUp } from 'lucide-vue-next'
import { useUpdateCheck } from '@/composables/useUpdateCheck'
import { safeHref } from '@/utils/safeUrl'

defineProps({ collapsed: Boolean })

const { t } = useI18n()
const { status, load } = useUpdateCheck()

const version = computed(() => status.value?.latest_version)
const releaseHref = computed(() =>
  status.value?.update_available ? safeHref(status.value.release_url) : null,
)
const label = computed(() => t('sidebar.updateAvailableTitle', { version: version.value }))

onMounted(load)
</script>

<style scoped>
/* Mobile-first: full touch target in the drawer, compact in the desktop sidebar. */
.sb-update {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  min-height: var(--touch-target);
  margin-top: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-btn);
  background: var(--surface-2);
  color: var(--accent-300);
  font-size: var(--text-3xs);
  letter-spacing: var(--tracking-wide);
  text-decoration: none;
  transition: var(--transition-bg);
}
.sb-update:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
@media (min-width: 1024px) {
  .sb-update {
    min-height: 0;
  }
}
@media (hover: hover) {
  .sb-update:hover {
    background: var(--surface-3);
  }
}
@media (prefers-reduced-motion: reduce) {
  .sb-update {
    transition: none;
  }
}
</style>
