<template>
  <div class="up-col">
    <div class="up-section">
      <div class="up-stitle">{{ $t('stats.lastPlay') }}</div>
      <div class="up-detail" :title="lastPlayText">{{ lastPlayText }}</div>
      <div class="up-meta" :title="lastMetaText">{{ lastMetaText }}</div>
    </div>
    <div class="up-section">
      <div class="up-stitle">{{ $t('stats.topMoviesUser') }}</div>
      <div v-if="!userProfile.top_movies?.length" class="up-empty">
        {{ $t('common.none') }}
      </div>
      <div
        v-for="(m, i) in userProfile.top_movies"
        :key="'m' + i"
        class="up-rank-item"
        :title="m.name"
      >
        <span class="up-rank-n">{{ i + 1 }}</span>
        <img
          v-if="m.item_id"
          :src="'/api/emby/image/' + m.item_id"
          class="up-rank-thumb"
          @error="e => (e.target.style.display = 'none')"
        />
        <span class="up-rank-name">{{ m.name }}</span>
        <span class="up-rank-val">{{ m.plays }}</span>
      </div>
    </div>
    <div class="up-section">
      <div class="up-stitle">{{ $t('stats.topSeriesUser') }}</div>
      <div v-if="!userProfile.top_series?.length" class="up-empty">
        {{ $t('common.none') }}
      </div>
      <div
        v-for="(s, i) in userProfile.top_series"
        :key="'s' + i"
        class="up-rank-item"
        :title="s.name"
      >
        <span class="up-rank-n">{{ i + 1 }}</span>
        <span class="up-rank-name">{{ s.name }}</span>
        <span class="up-rank-val">{{ s.plays }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  userProfile: { type: Object, required: true },
  lastPlayText: { type: String, required: true },
  lastMetaText: { type: String, required: true },
})
</script>

<style scoped>
.up-col {
  min-width: 0;
  overflow: hidden;
}
.up-section {
  margin-bottom: 12px;
}
.up-stitle {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(255, 255, 255, 0.3);
  margin-bottom: 8px;
}
.up-detail {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.up-meta {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.up-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.up-rank-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 0.5px solid var(--border-subtle);
}
.up-rank-item:last-child {
  border-bottom: none;
}
.up-rank-n {
  width: 14px;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-very-faint);
  text-align: center;
  flex-shrink: 0;
}
.up-rank-thumb {
  width: 22px;
  height: 32px;
  border-radius: 3px;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--surface-2);
}
.up-rank-name {
  flex: 1;
  font-size: var(--text-xs);
  color: rgb(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.up-rank-val {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--accent-400);
  flex-shrink: 0;
}
</style>
