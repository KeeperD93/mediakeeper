<template>
  <div class="dmp mk-page-root">
    <div v-if="loading" class="dmp-loading"><MkSpinner size="md" /></div>
    <template v-else-if="data?.person">
      <header class="dmp-hero">
        <div class="dmp-hero-bg" :style="bgStyle" />
        <div class="dmp-hero-gradient" />
        <div class="dmp-hero-content">
          <img
            v-if="data.person.photo"
            :src="data.person.photo"
            :alt="data.person.name"
            class="dmp-photo"
          />
          <div class="dmp-info">
            <span class="dmp-known">{{ knownForLabel }}</span>
            <h1 class="dmp-name">{{ data.person.name }}</h1>
            <p v-if="data.person.biography" class="dmp-bio">{{ trimmedBio }}</p>
            <div class="dmp-role-pills">
              <TabStrip v-model="role" :tabs="roleTabs" placement="top" />
            </div>
          </div>
        </div>
      </header>

      <section class="dmp-section">
        <div class="dmp-sec-head">
          <h2>{{ $t('portal.detail.filmography') }}</h2>
          <span class="dmp-sec-count">{{ filteredItems.length }}</span>
        </div>
        <div v-if="!filteredItems.length" class="arr-empty">{{ $t('common.noResults') }}</div>
        <div v-else class="dmp-grid">
          <MediaCard
            v-for="it in filteredItems"
            :key="`${it.media_type}-${it.tmdb_id || it.id}`"
            :item="it"
            fill
            width="160px"
            @select="goToDetail(it)"
          />
        </div>
      </section>
    </template>

    <div v-else class="arr-empty">{{ $t('common.noResults') }}</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import MediaCard from '@/components/portal/MediaCard.vue'
import TabStrip from '@/components/common/TabStrip.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'
import { MEDIA_TYPE } from '@/constants/media'
import { PERSON_ROLE } from '@/constants/portal'

import '@/assets/styles/portal/admin-rich-row-header.css'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { apiGet } = useApi()

const data = ref(null)
const loading = ref(false)
const role = ref(route.query.role || PERSON_ROLE.ALL)

const roleTabs = computed(() => [
  { id: PERSON_ROLE.ALL, label: t('portal.detail.roleAll') },
  { id: PERSON_ROLE.DIRECTOR, label: t('portal.detail.roleDirector') },
  { id: PERSON_ROLE.ACTING, label: t('portal.detail.roleActing') },
])

const filteredItems = computed(() => data.value?.items || [])

const bgStyle = computed(() => {
  const items = data.value?.items || []
  const first = items.find(i => i.backdrop || i.backdrop_url)
  const bg = first?.backdrop || first?.backdrop_url || ''
  return bg ? { backgroundImage: `url(${bg})` } : {}
})

const trimmedBio = computed(() => {
  const bio = data.value?.person?.biography || ''
  if (bio.length <= 420) return bio
  return bio.slice(0, 420).trim() + '…'
})

const knownForLabel = computed(() => {
  const kf = data.value?.person?.known_for || ''
  return kf ? kf.toUpperCase() : ''
})

async function load() {
  loading.value = true
  try {
    const id = route.params.id
    const res = await apiGet(`/api/portal/catalog/person/${id}?role=${role.value}`)
    data.value = res
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

function goToDetail(item) {
  const type = item.media_type || MEDIA_TYPE.MOVIE
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

watch([() => route.params.id, role], load, { immediate: false })
onMounted(load)
</script>

<style scoped>
.dmp {
  min-height: calc(100vh - 64px);
}
.dmp-loading {
  display: flex;
  justify-content: center;
  padding: 6rem 1rem;
}

.dmp-hero {
  position: relative;
  padding: 3rem 1.5rem 2rem;
  min-height: 320px;
  overflow: hidden;
  border-radius: 0 0 var(--portal-radius-2xl) var(--portal-radius-2xl);
}
.dmp-hero-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center 25%;
  opacity: 0.3;
  filter: blur(8px) saturate(1.2);
}
.dmp-hero-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgb(var(--portal-bg-primary-rgb), 0.3) 0%,
    rgb(var(--portal-bg-primary-rgb), 0.75) 60%,
    rgb(var(--portal-bg-primary-rgb), 1) 100%
  );
}
.dmp-hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: center;
  text-align: center;
  max-width: 1200px;
  margin: 0 auto;
}
@media (min-width: 768px) {
  .dmp-hero-content {
    flex-direction: row;
    align-items: flex-start;
    text-align: left;
  }
}
.dmp-photo {
  width: 140px;
  height: 210px;
  object-fit: cover;
  border-radius: var(--portal-radius-lg);
  /* One-off hero-photo elevation: no portal-shadow-* token matches 40px/.6 and
     it is used only here, so kept inline rather than adding a single-use token. */
  box-shadow:
    0 10px 40px rgb(0, 0, 0, 0.6),
    0 0 0 1px var(--portal-border-default);
  flex-shrink: 0;
}
@media (min-width: 768px) {
  .dmp-photo {
    width: 180px;
    height: 270px;
  }
}
.dmp-info {
  flex: 1;
  min-width: 0;
  color: var(--portal-text-primary);
}
.dmp-known {
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-black);
  color: var(--portal-accent-light);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.dmp-name {
  font-size: 1.7rem;
  font-weight: var(--portal-font-black);
  letter-spacing: var(--portal-tracking-tight);
  margin: 8px 0 14px;
  line-height: 1.05;
  /* One-off title glow: no portal text-shadow token family exists; single use. */
  text-shadow: 0 4px 24px rgb(0, 0, 0, 0.5);
}
@media (min-width: 768px) {
  .dmp-name {
    font-size: 2.5rem;
  }
}
.dmp-bio {
  font-size: var(--portal-text-base);
  line-height: var(--portal-lh-relaxed);
  color: var(--portal-text-body-muted);
  max-width: 780px;
  margin: 0 0 18px;
}
.dmp-role-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dmp-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 8px 2rem;
}
@media (min-width: 768px) {
  .dmp-section {
    padding: 2rem 1.5rem 3rem;
  }
}
.dmp-sec-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}
.dmp-sec-head h2 {
  font-size: var(--portal-text-lg);
  font-weight: var(--portal-font-extrabold);
  color: var(--portal-text-primary);
  margin: 0;
}
.dmp-sec-count {
  color: var(--portal-text-muted);
  font-weight: var(--portal-font-bold);
  font-size: var(--portal-text-sm);
}
.dmp-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
}
@media (min-width: 641px) {
  .dmp-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }
}
@media (min-width: 1024px) {
  .dmp-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
  }
}
</style>
