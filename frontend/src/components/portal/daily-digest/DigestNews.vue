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

    <div v-if="rows.length" class="dd-more-news">
      <template v-for="row in rows" :key="row.key">
        <DigestBoostRow
          v-if="row.kind === DIGEST_ROW_KIND.BOOST"
          :boost="row.view"
          :open="openId === row.key"
          @toggle="toggleRow(row)"
        />
        <div
          v-else
          class="dd-more-item"
          :class="{
            'dd-more-item--release': row.kind === DIGEST_ROW_KIND.RELEASE,
            'dd-more-item--open': openId === row.key,
          }"
        >
          <button
            type="button"
            class="dd-more-row"
            :aria-expanded="openId === row.key ? 'true' : 'false'"
            @click="toggleRow(row)"
          >
            <span
              v-if="row.view.isNew"
              class="dd-new-mini"
              role="img"
              :aria-label="$t('portal.dailyDigest.news.new')"
            />
            <template v-if="row.kind === DIGEST_ROW_KIND.RELEASE">
              <span class="dd-badge dd-badge--release">
                {{ $t('portal.dailyDigest.release.badge') }}
              </span>
              <span class="dd-more-title">
                {{
                  $t(
                    'portal.dailyDigest.release.line',
                    { version: row.view.version, n: row.view.totalLabel },
                    row.view.total,
                  )
                }}
              </span>
            </template>
            <template v-else>
              <span class="dd-badge" :class="row.view.badgeClass">{{ $t(row.view.typeKey) }}</span>
              <span class="dd-more-title">{{ row.view.title }}</span>
            </template>
            <span class="dd-more-date">{{ row.view.date }}</span>
            <span class="dd-chev" :class="{ 'dd-chev--up': openId === row.key }">
              <ChevronDown :size="16" aria-hidden="true" />
            </span>
          </button>
          <div v-if="openId === row.key" class="dd-more-body">
            <DigestReleaseGroups
              v-if="row.kind === DIGEST_ROW_KIND.RELEASE"
              :groups="row.view.groups"
            />
            <template v-else>
              <p v-for="(text, i) in row.view.paragraphs" :key="i">{{ text }}</p>
            </template>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, Megaphone } from 'lucide-vue-next'
import { DIGEST_ROW_KIND } from '@/constants/dailyDigest'
import { newsLayout } from '@/utils/portal/dailyDigest'
import DigestBoostRow from './DigestBoostRow.vue'
import DigestReleaseGroups from './DigestReleaseGroups.vue'
import '@/assets/styles/portal/daily-digest-news.css'
import '@/assets/styles/portal/daily-digest-release-list.css'

const props = defineProps({
  // Pinned first, then newest; newsLayout picks the card and orders the rows by kind.
  news: { type: Array, required: true },
  // The new Portal version, as a row of the list.
  release: { type: Object, default: null },
  // The XP boosts running now, a row each.
  boosts: { type: Array, default: () => [] },
})
const emit = defineEmits(['read', 'seen', 'open-release'])

const layout = computed(() => newsLayout(props.news, props.release, props.boosts))
const main = computed(() => layout.value.main)
const rows = computed(() => layout.value.rows)

const mainOpen = ref(false)
const openId = ref(null)
const imageFailed = ref(false)

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

// A text that fits on the card has no « Read more »: it counts as read on close.
onMounted(() => {
  if (main.value.paragraphs.length <= 1) emit('seen', main.value.id)
})
</script>
