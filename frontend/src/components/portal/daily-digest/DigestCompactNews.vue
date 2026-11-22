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

    <div v-if="rows.length" class="ddc-box ddc-morelist">
      <template v-for="row in shownRows" :key="row.key">
        <div v-if="row.kind === DIGEST_ROW_KIND.RELEASE" class="dd-release-row">
          <button
            type="button"
            class="ddc-row ddc-row-item"
            :aria-expanded="openId === row.key ? 'true' : 'false'"
            @click="toggleRow(row)"
          >
            <span
              v-if="row.view.isNew"
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
                  { version: row.view.version, n: row.view.totalLabel },
                  row.view.total,
                )
              }}
            </span>
            <span class="ddc-when">{{ row.view.date }}</span>
          </button>
          <div v-if="openId === row.key" class="ddc-rowbody">
            <DigestReleaseGroups :groups="row.view.groups" />
          </div>
        </div>
        <DigestBoostRow
          v-else-if="row.kind === DIGEST_ROW_KIND.BOOST"
          :boost="row.view"
          :open="openId === row.key"
          compact
          @toggle="toggleRow(row)"
        />
        <template v-else>
          <button
            type="button"
            class="ddc-row ddc-row-item"
            :aria-expanded="openId === row.key ? 'true' : 'false'"
            @click="toggleRow(row)"
          >
            <span
              v-if="row.view.isNew"
              class="dd-new-mini"
              role="img"
              :aria-label="$t('portal.dailyDigest.news.new')"
            />
            <span class="dd-badge" :class="row.view.badgeClass">{{ $t(row.view.typeKey) }}</span>
            <span class="ddc-row-title">{{ row.view.title }}</span>
            <span class="ddc-when">{{ row.view.date }}</span>
          </button>
          <div v-if="openId === row.key" class="ddc-rowbody">
            <p v-for="(text, i) in row.view.paragraphs" :key="i">{{ text }}</p>
          </div>
        </template>
      </template>
      <button
        v-if="readCount"
        type="button"
        class="ddc-row ddc-row-more"
        :aria-expanded="moreOpen ? 'true' : 'false'"
        @click="moreOpen = !moreOpen"
      >
        {{
          moreOpen
            ? $t('portal.dailyDigest.news.hideMore')
            : $t('portal.dailyDigest.news.moreCount', { n: readCount }, readCount)
        }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Megaphone } from 'lucide-vue-next'
import { DIGEST_ROW_KIND } from '@/constants/dailyDigest'
import { newsLayout } from '@/utils/portal/dailyDigest'
import DigestBoostRow from './DigestBoostRow.vue'
import DigestReleaseGroups from './DigestReleaseGroups.vue'
import '@/assets/styles/portal/daily-digest-compact-news.css'
import '@/assets/styles/portal/daily-digest-release-list.css'

const props = defineProps({
  // Pinned first, then newest; newsLayout picks the card and orders the rows by kind.
  news: { type: Array, required: true },
  // The new Portal version, as a row of the list.
  release: { type: Object, default: null },
  // The XP boosts running now, a row each, always in sight.
  boosts: { type: Array, default: () => [] },
})
const emit = defineEmits(['read', 'seen', 'open-release'])

const layout = computed(() => newsLayout(props.news, props.release, props.boosts))
const main = computed(() => layout.value.main)
const rows = computed(() => layout.value.rows)

// Unread at opening stay in view; reading one must not hide it behind « +N ».
const unreadAtOpen = new Set(props.news.filter(item => item.is_new).map(item => item.id))
const isRead = row => row.kind === DIGEST_ROW_KIND.NEWS && !unreadAtOpen.has(row.key)
const readCount = computed(() => rows.value.filter(isRead).length)
const moreOpen = ref(false)
// « +N » shows the read items in their place in the list.
const shownRows = computed(() =>
  moreOpen.value ? rows.value : rows.value.filter(row => !isRead(row)),
)

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
function toggleRow(row) {
  openId.value = openId.value === row.key ? null : row.key
  if (openId.value !== row.key) return
  if (row.kind === DIGEST_ROW_KIND.RELEASE) emit('open-release')
  else if (row.kind === DIGEST_ROW_KIND.NEWS) emit('read', row.key)
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
