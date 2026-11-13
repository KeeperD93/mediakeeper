<template>
  <section
    class="dd-rail"
    :class="compact ? 'dd-rail--compact' : 'dd-rail--full'"
    :aria-label="$t('portal.dailyDigest.sections.recentAdds')"
  >
    <div v-if="compact" class="ddc-label">
      {{ $t('portal.dailyDigest.sections.recentAddsShort') }}
      <span class="dd-count">{{ items.length }}</span>
    </div>
    <div v-else class="dd-sh">
      <h2 class="dd-st">{{ $t('portal.dailyDigest.sections.recentAdds') }}</h2>
      <span class="dd-count">{{ items.length }}</span>
    </div>

    <!-- Arrows on a wide window; elsewhere the rail is swiped and stops on a poster. -->
    <div class="dd-posters-wrap">
      <button
        type="button"
        class="dd-pnav dd-pnav--prev"
        :aria-label="$t('portal.dailyDigest.aria.scrollLeft')"
        :disabled="!canScrollLeft"
        @click="scroll(-1)"
      >
        <ChevronLeft :size="compact ? 18 : 20" aria-hidden="true" />
      </button>
      <div ref="trackRef" class="dd-posters" @scroll="onScroll">
        <component
          :is="item.tmdb_id ? 'router-link' : 'div'"
          v-for="(item, index) in items"
          :key="item.emby_item_id || index"
          :to="mediaRoute(item)"
          class="dd-poster"
          @click="item.tmdb_id ? $emit('leave') : null"
        >
          <img v-if="item.poster_url" :src="item.poster_url" alt="" loading="lazy" />
          <span v-else class="dd-poster-fallback" aria-hidden="true">
            {{ item.title?.[0] || '?' }}
          </span>
          <span class="dd-poster-cap">
            {{ item.title }}
            <small v-if="!compact && caption(item)">{{ caption(item) }}</small>
          </span>
        </component>
      </div>
      <button
        type="button"
        class="dd-pnav dd-pnav--next"
        :aria-label="$t('portal.dailyDigest.aria.scrollRight')"
        :disabled="!canScrollRight"
        @click="scroll(1)"
      >
        <ChevronRight :size="compact ? 18 : 20" aria-hidden="true" />
      </button>
    </div>
  </section>
</template>

<script setup>
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useCarouselArrows } from '@/composables/portal/useCarouselArrows'
import { DIGEST_POSTERS_PER_CLICK } from '@/constants/dailyDigest'
import { MEDIA_TYPE } from '@/constants/media'
import '@/assets/styles/portal/daily-digest-posters.css'

const props = defineProps({
  // Library additions since the viewer's last visit (`recent_adds`).
  items: { type: Array, required: true },
  compact: { type: Boolean, default: false },
})
defineEmits(['leave'])

const { t } = useI18n()
const { trackRef, canScrollLeft, canScrollRight, onScroll, scroll } = useCarouselArrows(
  toRef(props, 'items'),
  { perClick: DIGEST_POSTERS_PER_CLICK },
)

function mediaRoute(item) {
  if (!item.tmdb_id) return undefined
  return {
    name: 'portal-media-detail',
    params: { type: item.media_type || MEDIA_TYPE.MOVIE, id: item.tmdb_id },
  }
}

function caption(item) {
  if (item.media_type !== MEDIA_TYPE.TV) return item.year || ''
  return item.year
    ? t('portal.dailyDigest.posters.seriesYear', { year: item.year })
    : t('portal.dailyDigest.posters.series')
}
</script>
