<template>
  <section :aria-label="$t('portal.dailyDigest.sections.news')">
    <article class="ddc-news" :class="{ 'dd-news--new': main.isNew }">
      <div class="ddc-thumb">
        <img
          v-if="main.imageUrl && !imageFailed"
          :src="main.imageUrl"
          alt=""
          @error="imageFailed = true"
        />
        <Megaphone v-else :size="24" :stroke-width="1.8" aria-hidden="true" />
      </div>
      <div class="dd-grow">
        <div class="ddc-meta">
          <span v-if="main.isNew" class="dd-new-pill">
            <span class="dd-new-dot" />
            {{ $t('portal.dailyDigest.news.new') }}
          </span>
          <span class="dd-badge" :class="main.badgeClass">{{ $t(main.typeKey) }}</span>
          <span class="ddc-when">{{ main.date }}</span>
        </div>
        <h2 class="ddc-news-title">{{ main.title }}</h2>
        <p
          v-if="main.paragraphs.length"
          ref="firstRef"
          class="ddc-text"
          :class="{ 'ddc-text--clamp': !mainOpen }"
        >
          {{ main.paragraphs[0] }}
        </p>
        <template v-if="mainOpen">
          <p v-for="(text, i) in main.paragraphs.slice(1)" :key="i" class="ddc-text">{{ text }}</p>
        </template>
        <div v-if="hasMore" class="ddc-links">
          <button
            type="button"
            class="ddc-link-button"
            :aria-expanded="mainOpen ? 'true' : 'false'"
            @click="toggleMain"
          >
            {{
              $t(mainOpen ? 'portal.dailyDigest.news.readLess' : 'portal.dailyDigest.news.readMore')
            }}
          </button>
        </div>
      </div>
    </article>

    <div v-if="others.length || releaseRow" class="ddc-box ddc-morelist">
      <div v-if="releaseRow" class="dd-release-row">
        <button
          type="button"
          class="ddc-row ddc-row-item"
          :aria-expanded="openId === RELEASE_ROW ? 'true' : 'false'"
          @click="toggleRow(RELEASE_ROW)"
        >
          <span
            v-if="releaseRow.isNew"
            class="dd-new-mini"
            role="img"
            :aria-label="$t('portal.dailyDigest.news.new')"
          />
          <span class="dd-badge dd-badge--release">
            {{ $t('portal.dailyDigest.release.badge') }}
          </span>
          <span class="ddc-row-title">
            {{
              $t(
                'portal.dailyDigest.release.line',
                { version: releaseRow.version, n: releaseRow.totalLabel },
                releaseRow.total,
              )
            }}
          </span>
          <span class="ddc-when">{{ releaseRow.date }}</span>
        </button>
        <div v-if="openId === RELEASE_ROW" class="ddc-rowbody">
          <DigestReleaseGroups :groups="releaseRow.groups" />
        </div>
      </div>
      <template v-for="item in shownOthers" :key="item.id">
        <button
          type="button"
          class="ddc-row ddc-row-item"
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
          <span class="ddc-row-title">{{ item.title }}</span>
          <span class="ddc-when">{{ item.date }}</span>
        </button>
        <div v-if="openId === item.id" class="ddc-rowbody">
          <p v-for="(text, i) in item.paragraphs" :key="i">{{ text }}</p>
        </div>
      </template>
      <button
        v-if="readOthers.length"
        type="button"
        class="ddc-row ddc-row-more"
        :aria-expanded="moreOpen ? 'true' : 'false'"
        @click="moreOpen = !moreOpen"
      >
        {{
          moreOpen
            ? $t('portal.dailyDigest.news.hideMore')
            : $t('portal.dailyDigest.news.moreCount', { n: readOthers.length }, readOthers.length)
        }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Megaphone } from 'lucide-vue-next'
import { newsView, releaseView } from '@/utils/portal/dailyDigest'
import DigestReleaseGroups from './DigestReleaseGroups.vue'
import '@/assets/styles/portal/daily-digest-compact-news.css'
import '@/assets/styles/portal/daily-digest-release-list.css'

const props = defineProps({
  // Pinned first, then newest: the first one gets the card.
  news: { type: Array, required: true },
  // The new Portal version, as a row heading the other items.
  release: { type: Object, default: null },
})
const emit = defineEmits(['read', 'seen', 'open-release'])

// The version's row shares the « one open at a time » of the news rows.
const RELEASE_ROW = 'release'

const views = computed(() => props.news.map(newsView))
const main = computed(() => views.value[0])
const others = computed(() => views.value.slice(1))
const releaseRow = computed(() => (props.release ? releaseView(props.release) : null))

// Unread at opening stay in view; reading one must not hide it behind « +N ».
const unreadAtOpen = new Set(
  props.news
    .slice(1)
    .filter(item => item.is_new)
    .map(item => item.id),
)
const readOthers = computed(() => others.value.filter(item => !unreadAtOpen.has(item.id)))
const moreOpen = ref(false)
const shownOthers = computed(() => [
  ...others.value.filter(item => unreadAtOpen.has(item.id)),
  ...(moreOpen.value ? readOthers.value : []),
])

const mainOpen = ref(false)
const openId = ref(null)
const imageFailed = ref(false)
const firstRef = ref(null)
const clamped = ref(false)
const hasMore = computed(() => main.value.paragraphs.length > 1 || clamped.value)

function toggleMain() {
  mainOpen.value = !mainOpen.value
  if (mainOpen.value) emit('read', main.value.id)
}

// One row open at a time, under itself; a click anywhere on it closes it.
function toggleRow(id) {
  openId.value = openId.value === id ? null : id
  if (openId.value !== id) return
  if (id === RELEASE_ROW) emit('open-release')
  else emit('read', id)
}

// The first paragraph stops at two lines: « Read more » shows when it is cut.
function measure() {
  const el = firstRef.value
  if (el && !mainOpen.value) clamped.value = el.scrollHeight > el.clientHeight + 1
}

let observer = null
onMounted(() => {
  measure()
  if (!hasMore.value) emit('seen', main.value.id)
  if (firstRef.value) {
    observer = new ResizeObserver(measure)
    observer.observe(firstRef.value)
  }
})
onBeforeUnmount(() => observer?.disconnect())
</script>
