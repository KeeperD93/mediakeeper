<template>
  <div class="flex items-center justify-center h-full p-6">
    <div class="mk-card text-center py-16 px-10 max-w-lg">
      <div class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5 ph-icon-wrap">
        <Calendar class="w-7 h-7 ph-icon" />
      </div>
      <h2 class="text-lg font-semibold mb-2 ph-title">{{ pageTitle }}</h2>
      <p class="text-sm ph-body">
        {{ $t('common.moduleComingSoon') }}
      </p>
      <p class="text-xs mt-4 ph-body">
        {{ $t('common.moduleComingSoonDesc') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar } from 'lucide-vue-next'

const route = useRoute()
const { t } = useI18n()
const pageTitle = computed(() => {
  if (route.meta?.titleKey) return t(route.meta.titleKey)
  return route.meta?.title || 'Module'
})
</script>

<style scoped>
.ph-icon-wrap { background: var(--bg-tertiary); border: 1px solid var(--border); }
.ph-icon { color: var(--text-muted); }
.ph-title { color: var(--text-primary); }
.ph-body { color: var(--text-muted); }
</style>
