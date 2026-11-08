<template>
  <div class="ob-panel">
    <h2 class="ob-panel-title">{{ $t('onboarding.tourTitle') }}</h2>
    <p class="ob-panel-desc ob-panel-desc-tight">{{ $t('onboarding.tourDesc') }}</p>

    <div class="ob-tour-grid">
      <div
        v-for="(mod, i) in modules"
        :key="mod.id"
        class="ob-tour-card"
        :class="{ 'ob-tour-active': tourActive === i }"
        @click="tourActive = i"
      >
        <div class="ob-tour-card-inner">
          <div class="ob-tour-icon" :style="{ background: mod.bg }">
            <component :is="mod.icon" :size="16" :stroke-width="1.8" />
          </div>
          <span class="ob-tour-name">{{ mod.name }}</span>
        </div>
      </div>
    </div>

    <transition name="ob-fade">
      <div v-if="modules[tourActive]" class="ob-tour-detail">
        <div class="ob-tour-detail-header">
          <div class="ob-tour-icon-lg" :style="{ background: modules[tourActive].bg }">
            <component :is="modules[tourActive].icon" :size="22" :stroke-width="1.8" />
          </div>
          <div>
            <div class="ob-tour-detail-name">{{ modules[tourActive].name }}</div>
            <div class="ob-tour-detail-desc">{{ modules[tourActive].desc }}</div>
          </div>
        </div>
        <div class="ob-tour-features">
          <div v-for="feat in modules[tourActive].features" :key="feat" class="ob-tour-feat">
            <Check :size="11" :stroke-width="2.5" class="ob-feature-check" />
            {{ feat }}
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'

defineProps({
  modules: { type: Array, required: true },
})

const tourActive = defineModel('active', { type: Number, required: true })
</script>
