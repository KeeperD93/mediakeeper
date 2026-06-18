<template>
  <section class="vmd2-section">
    <template v-if="media.videos?.length">
      <h2>{{ $t('portal.detail.videos') }}</h2>
      <div class="vmd2-scroller">
        <a
          v-for="v in media.videos"
          :key="v.key"
          class="vmd2-video-card"
          :href="`https://www.youtube.com/watch?v=${encodeURIComponent(v.key)}`"
          target="_blank"
          rel="noopener"
        >
          <div class="vmd2-video-thumb-wrap">
            <img
              v-if="v.thumb"
              :src="v.thumb"
              :alt="v.name"
              class="vmd2-video-thumb"
              loading="lazy"
            />
            <div class="vmd2-video-play">
              <Play :size="22" fill="currentColor" />
            </div>
            <span class="vmd2-video-type">{{ translateType(v.type) }}</span>
          </div>
          <span class="vmd2-video-title">{{ v.name }}</span>
        </a>
      </div>
    </template>

    <template v-if="media.reviews?.length">
      <h2 class="vmd2-section-break">{{ $t('portal.detail.recentReviews') }}</h2>
      <div class="vmd2-reviews">
        <article v-for="r in media.reviews" :key="r.author + (r.date || '')" class="vmd2-review">
          <header>
            <div class="vmd2-review-avatar">{{ (r.author || '?')[0].toUpperCase() }}</div>
            <div class="vmd2-review-meta">
              <span class="vmd2-review-author">{{ r.author }}</span>
              <span v-if="r.date" class="vmd2-review-date">{{ formatDate(r.date) }}</span>
            </div>
            <span v-if="r.rating" class="vmd2-review-score">{{ r.rating }}/10</span>
          </header>
          <p class="vmd2-review-content">{{ r.content }}</p>
        </article>
      </div>
    </template>

    <div v-if="!media.videos?.length && !media.reviews?.length" class="vmd2-empty">
      {{ $t('portal.detail.noExtras') }}
    </div>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { Play } from 'lucide-vue-next'
import { localizedDate } from '@/utils/datetime'

defineProps({
  media: { type: Object, required: true },
})

const { t, te } = useI18n()

function translateType(type) {
  const key = `portal.detail.videoType.${type}`
  return te(key) ? t(key) : type
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return localizedDate(new Date(iso))
  } catch {
    return iso
  }
}
</script>
