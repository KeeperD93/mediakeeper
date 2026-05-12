<template>
  <section class="wnns" :aria-label="$t('portal.news.whatsNew')">
    <article v-for="n in news" :key="n.id" class="wnns-card">
      <div v-if="n.image_url" class="wnns-thumb">
        <img :src="n.image_url" :alt="n.title" class="wnns-thumb-img" />
      </div>
      <div v-else class="wnns-thumb wnns-thumb--fallback" :class="`wnns-thumb--${n.type}`">
        <span class="wnns-thumb-mark">{{ initialOf(n) }}</span>
      </div>
      <div class="wnns-body">
        <h3 class="wnns-title">{{ n.title }}</h3>
        <p class="wnns-excerpt">{{ excerptOf(n) }}</p>
      </div>
    </article>
  </section>
</template>

<script setup>
defineProps({
  news: { type: Array, required: true },
})

function excerptOf(n) {
  return (n.content_excerpt || n.content || '').trim()
}

function initialOf(n) {
  return (n.title || '?').trim().charAt(0).toUpperCase()
}
</script>

<style scoped>
.wnns {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 20px 14px;
}
.wnns-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: rgb(var(--accent-rgb), 0.06);
  border: 0.5px solid var(--portal-border-default);
  border-radius: var(--portal-radius-lg);
  box-shadow: var(--portal-shadow-popup);
  transition: background var(--portal-dur-fast);
}
@media (hover: hover) {
  .wnns-card:hover {
    background: rgb(var(--accent-rgb), 0.1);
  }
}
.wnns-thumb {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: var(--portal-radius-md);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.wnns-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wnns-thumb--fallback {
  background: rgb(var(--accent-rgb), 0.15);
  color: var(--accent-300);
  font-weight: var(--portal-font-bold);
}
.wnns-thumb-mark { font-size: var(--portal-text-md); }
.wnns-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}
.wnns-title {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin: 0;
  line-height: 1.25;
}
.wnns-excerpt {
  font-size: var(--portal-text-xs);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
