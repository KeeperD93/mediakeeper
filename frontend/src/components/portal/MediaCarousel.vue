<template>
  <section
    class="pt-carousel"
    :class="{ 'pt-carousel--has-title-link': !!effectiveTitleRoute }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="pt-carousel-header">
      <!-- Title: clickable when `titleRoute` (or the legacy
           `seeAllRoute` alias) is passed, plain otherwise. Becomes the
           "see all" affordance — no more separate button in the corner. -->
      <component
        :is="effectiveTitleRoute ? 'button' : 'h3'"
        class="pt-carousel-title"
        :class="{ 'pt-carousel-title--link': !!effectiveTitleRoute }"
        @click="onTitleClick"
      >
        <span>{{ title }}</span>
        <ChevronRight
          v-if="effectiveTitleRoute"
          class="pt-carousel-title-chevron"
          :size="18"
          :stroke-width="2.5"
        />
      </component>
    </div>

    <!-- Scrollable track. scroll-snap aligns cards on their left edge
         so a click on the arrows (or any swipe/drag/wheel) can never
         leave a poster half-cut in the viewport. -->
    <div
      ref="trackRef"
      class="pt-carousel-track"
      @scroll="onScroll"
    >
      <MediaCard
        v-for="item in items"
        :key="item.id || item.tmdb_id"
        :item="item"
        :width="cardWidth"
        :show-info="showInfo"
        @select="$emit('select', $event)"
        @play="$emit('play', $event)"
        @request="$emit('request', $event)"
      />
    </div>

    <!-- Edge gradients: visually signal that there is more content to
         scroll to. They auto-hide when you reach either end of the
         track. Pointer-events: none so they don't block clicks on the
         first/last card underneath. -->
    <div
      class="pt-edge-fade pt-edge-fade--left"
      :class="{ 'pt-edge-fade--visible': canScrollLeft }"
    />
    <div
      class="pt-edge-fade pt-edge-fade--right"
      :class="{ 'pt-edge-fade--visible': canScrollRight }"
    />

    <!-- Scroll arrows: always visible on desktop when there is more
         content, with a strong contrasted pill style. -->
    <button
      class="pt-carousel-arrow pt-carousel-arrow--left"
      :class="{ 'pt-carousel-arrow--visible': canScrollLeft }"
      :aria-label="$t('common.previous')"
      @click="scroll(-1)"
    >
      <ChevronLeft :size="26" :stroke-width="2.8" />
    </button>
    <button
      class="pt-carousel-arrow pt-carousel-arrow--right"
      :class="{ 'pt-carousel-arrow--visible': canScrollRight }"
      :aria-label="$t('common.next')"
      @click="scroll(1)"
    >
      <ChevronRight :size="26" :stroke-width="2.8" />
    </button>
  </section>
</template>

<script setup>
import { ref, computed, toRef } from 'vue'
import { useRouter } from 'vue-router'
import MediaCard from './MediaCard.vue'
import { useCarouselArrows } from '@/composables/portal/useCarouselArrows'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

import '@/assets/styles/portal/media-carousel.css'

const props = defineProps({
  title: { type: String, required: true },
  items: { type: Array, default: () => [] },
  cardWidth: { type: String, default: '185px' },
  showInfo: { type: Boolean, default: false },
  // Backwards-compat alias — old callers used `seeAllRoute`, new ones
  // use `titleRoute`. They mean exactly the same thing.
  seeAllRoute: { type: [String, Object], default: null },
  titleRoute:  { type: [String, Object], default: null },
})

defineEmits(['select', 'play', 'request'])

const router = useRouter()
const hovered = ref(false)

const { trackRef, canScrollLeft, canScrollRight, onScroll, scroll } =
  useCarouselArrows(toRef(props, 'items'))

// Unify the two prop aliases in a single computed used everywhere
// in the template. titleRoute wins if both are set.
const effectiveTitleRoute = computed(() => props.titleRoute || props.seeAllRoute)

function onTitleClick() {
  const route = effectiveTitleRoute.value
  if (route) router.push(route)
}
</script>
