<template>
  <section v-if="items.length" class="dp-section dp-cw-section">
    <h3 class="dp-section-title">{{ $t('portal.sections.continueWatching') }}</h3>
    <div ref="cwTrackRef" class="dp-cw-track" @scroll="cwOnScroll">
      <a
        v-for="item in safeItems"
        :key="item.emby_item_id || item.id"
        :href="item.embyHref"
        target="_blank"
        rel="noopener noreferrer"
        class="dp-cw-card"
      >
        <img
          :src="item.poster_url || item.backdrop"
          :alt="item.title"
          class="dp-cw-img"
          loading="lazy"
        />
        <div class="dp-cw-info">
          <span class="dp-cw-title">{{ item.title }}</span>
        </div>
      </a>
    </div>
    <button
      class="pt-carousel-arrow pt-carousel-arrow--left dp-cw-arrow"
      :class="{ 'pt-carousel-arrow--visible': cwCanLeft }"
      :aria-label="$t('common.previous')"
      @click="cwScroll(-1)"
    >
      <ChevronLeft :size="26" :stroke-width="2.8" />
    </button>
    <button
      class="pt-carousel-arrow pt-carousel-arrow--right dp-cw-arrow"
      :class="{ 'pt-carousel-arrow--visible': cwCanRight }"
      :aria-label="$t('common.next')"
      @click="cwScroll(1)"
    >
      <ChevronRight :size="26" :stroke-width="2.8" />
    </button>
  </section>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { useCarouselArrows } from '@/composables/portal/useCarouselArrows'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { safeHref } from '@/utils/safeUrl'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

// Precompute a scheme-safe Emby deep-link per card (dead '#' if unsafe).
const safeItems = computed(() =>
  props.items.map(item => ({ ...item, embyHref: safeHref(item.emby_url) || '#' })),
)

const itemsRef = toRef(props, 'items')
const {
  trackRef: cwTrackRef,
  canScrollLeft: cwCanLeft,
  canScrollRight: cwCanRight,
  onScroll: cwOnScroll,
  scroll: cwScroll,
} = useCarouselArrows(itemsRef)
</script>
