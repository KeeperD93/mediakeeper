<template>
  <div class="dmc mk-page-root">
    <div v-if="loading" class="dmc-loading"><MkSpinner size="md" /></div>
    <template v-else-if="data?.collection">
      <header class="dmc-hero">
        <div class="dmc-hero-bg" :style="bgStyle" />
        <div class="dmc-hero-gradient" />
        <div class="dmc-hero-content">
          <img v-if="data.collection.poster" :src="data.collection.poster" :alt="data.collection.name" class="dmc-poster" />
          <div class="dmc-info">
            <span class="dmc-label">{{ $t('portal.detail.franchise') }}</span>
            <h1 class="dmc-name">{{ data.collection.name }}</h1>
            <p v-if="data.collection.overview" class="dmc-over">{{ data.collection.overview }}</p>
            <span class="dmc-count">{{ (data.items || []).length }} {{ $t('portal.detail.parts') }}</span>
          </div>
        </div>
      </header>

      <section class="dmc-section">
        <div v-if="!data.items?.length" class="arr-empty">{{ $t('common.noResults') }}</div>
        <div v-else class="dmc-grid">
          <MediaCard
            v-for="it in data.items"
            :key="`${it.media_type}-${it.tmdb_id || it.id}`"
            :item="it"
            width="180px"
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
import { useApi } from '@/composables/useApi'
import MediaCard from '@/components/portal/MediaCard.vue'
import MkSpinner from '@/components/common/MkSpinner.vue'

import '@/assets/styles/portal/admin-rich-row-header.css'

const route = useRoute()
const router = useRouter()
const { apiGet } = useApi()

const data = ref(null)
const loading = ref(false)

const bgStyle = computed(() => {
  const bg = data.value?.collection?.backdrop
  return bg ? { backgroundImage: `url(${bg})` } : {}
})

async function load() {
  loading.value = true
  try {
    const res = await apiGet(`/api/portal/catalog/collection/${route.params.id}`)
    data.value = res
  } catch { data.value = null }
  finally { loading.value = false }
}

function goToDetail(item) {
  const type = item.media_type || 'movie'
  const id = item.tmdb_id || item.id
  router.push({ name: 'portal-media-detail', params: { type, id } })
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.dmc { min-height: calc(100vh - 64px); }
.dmc-loading { display: flex; justify-content: center; padding: 6rem 1rem; }

.dmc-hero {
  position: relative; padding: 3rem 1.5rem 2.5rem;
  min-height: 340px;
  overflow: hidden;
  border-radius: 0 0 24px 24px;
}
.dmc-hero-bg {
  position: absolute; inset: 0;
  background-size: cover; background-position: center;
  opacity: .45;
}
.dmc-hero-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(3,7,18,0.3) 0%, rgba(3,7,18,0.75) 60%, rgba(3,7,18,1) 100%);
}
.dmc-hero-content {
  position: relative; z-index: 2;
  display: flex; gap: 28px; align-items: flex-end;
  max-width: 1200px; margin: 0 auto;
}
.dmc-poster {
  width: 200px; aspect-ratio: 2/3; object-fit: cover;
  border-radius: var(--portal-radius-lg);
  box-shadow: 0 12px 44px rgba(0,0,0,0.6), 0 0 0 1px var(--portal-border-default);
  flex-shrink: 0;
}
.dmc-info { flex: 1; min-width: 0; color: #fff; }
.dmc-label {
  font-size: var(--portal-text-2xs); font-weight: var(--portal-font-black); color: var(--accent-300);
  text-transform: uppercase; letter-spacing: .14em;
}
.dmc-name {
  font-size: 2.8rem; font-weight: var(--portal-font-black); letter-spacing: var(--portal-tracking-tight);
  margin: 8px 0 14px; line-height: 1.04;
  text-shadow: 0 4px 24px rgba(0,0,0,0.5);
}
.dmc-over {
  font-size: var(--portal-text-base); line-height: var(--portal-lh-relaxed); color: rgba(255,255,255,.78);
  max-width: 780px; margin: 0 0 14px;
}
.dmc-count { color: var(--portal-text-secondary); font-size: var(--portal-text-xs); font-weight: var(--portal-font-bold); }

.dmc-section { max-width: 1400px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
.dmc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 16px;
}

@media (max-width: 767px) {
  .dmc-hero-content { flex-direction: column; align-items: center; text-align: center; }
  .dmc-poster { width: 160px; }
  .dmc-name { font-size: var(--portal-text-3xl); }
}
</style>
