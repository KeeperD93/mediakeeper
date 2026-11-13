<template>
  <section :aria-label="$t('portal.dailyDigest.sections.news')">
    <div class="dd-sh">
      <h2 class="dd-st">{{ $t('portal.dailyDigest.sections.news') }}</h2>
    </div>

    <article class="dd-news" :class="{ 'dd-news--new': main.isNew }">
      <div class="dd-news-img">
        <img
          v-if="main.imageUrl && !imageFailed"
          :src="main.imageUrl"
          alt=""
          @error="imageFailed = true"
        />
        <Megaphone v-else :size="40" :stroke-width="1.6" aria-hidden="true" />
      </div>
      <div class="dd-news-body">
        <div class="dd-news-meta">
          <span v-if="main.isNew" class="dd-new-pill">
            <span class="dd-new-dot" />
            {{ $t('portal.dailyDigest.news.new') }}
          </span>
          <span class="dd-badge" :class="main.badgeClass">{{ $t(main.typeKey) }}</span>
          <span v-if="main.pinned" class="dd-badge dd-badge--pin">
            {{ $t('portal.dailyDigest.news.pinned') }}
          </span>
          <span class="dd-news-date">{{ main.date }}</span>
        </div>
        <h3 class="dd-news-title">{{ main.title }}</h3>
        <p v-if="main.paragraphs.length" class="dd-news-text">{{ main.paragraphs[0] }}</p>
        <template v-if="mainOpen">
          <p v-for="(text, i) in main.paragraphs.slice(1)" :key="i" class="dd-news-more">
            {{ text }}
          </p>
        </template>
        <button
          v-if="main.paragraphs.length > 1"
          type="button"
          class="dd-link-button"
          :aria-expanded="mainOpen ? 'true' : 'false'"
          @click="toggleMain"
        >
          {{
            $t(mainOpen ? 'portal.dailyDigest.news.readLess' : 'portal.dailyDigest.news.readMore')
          }}
        </button>
      </div>
    </article>

    <div v-if="others.length" class="dd-more-news">
      <div
        v-for="item in others"
        :key="item.id"
        class="dd-more-item"
        :class="{ 'dd-more-item--open': openId === item.id }"
      >
        <button
          type="button"
          class="dd-more-row"
          :aria-expanded="openId === item.id ? 'true' : 'false'"
          @click="toggleRow(item.id)"
        >
          <span
            v-if="item.isNew"
            class="dd-new-mini"
            role="img"
            :aria-label="$t('portal.dailyDigest.news.new')"
          />
          <span class="dd-badge" :class="item.badgeClass">{{ $t(item.typeKey) }}</span>
          <span class="dd-more-title">{{ item.title }}</span>
          <span class="dd-more-date">{{ item.date }}</span>
          <span class="dd-chev" :class="{ 'dd-chev--up': openId === item.id }">
            <ChevronDown :size="16" aria-hidden="true" />
          </span>
        </button>
        <div v-if="openId === item.id" class="dd-more-body">
          <p v-for="(text, i) in item.paragraphs" :key="i">{{ text }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, Megaphone } from 'lucide-vue-next'
import { newsView } from '@/utils/portal/dailyDigest'
import '@/assets/styles/portal/daily-digest-news.css'

const props = defineProps({
  // Pinned first, then newest: the first one gets the large card.
  news: { type: Array, required: true },
})
const emit = defineEmits(['read', 'seen'])

const views = computed(() => props.news.map(newsView))
const main = computed(() => views.value[0])
const others = computed(() => views.value.slice(1))

const mainOpen = ref(false)
const openId = ref(null)
const imageFailed = ref(false)

function toggleMain() {
  mainOpen.value = !mainOpen.value
  if (mainOpen.value) emit('read', main.value.id)
}

// One other news item open at a time, under its row.
function toggleRow(id) {
  openId.value = openId.value === id ? null : id
  if (openId.value === id) emit('read', id)
}

// A text that fits on the card has no « Read more »: it counts as read on close.
onMounted(() => {
  if (main.value.paragraphs.length <= 1) emit('seen', main.value.id)
})
</script>
