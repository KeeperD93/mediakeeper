<template>
  <div>
    <div class="top-head">
      <span class="top-title">{{ card.title }}</span>
      <span class="top-unit">{{ card.unit }}</span>
    </div>
    <div v-if="!card.items?.length" class="top-empty">{{ $t('stats.noData') }}</div>
    <div v-for="(it, i) in card.items" :key="i" class="top-item">
      <span class="top-rank">{{ i + 1 }}</span>
      <img
        v-if="card.imgKey && it[card.imgKey]"
        :src="'/api/emby/image/' + it[card.imgKey]"
        class="top-thumb"
        @error="e => (e.target.style.display = 'none')"
        @mouseenter="showPreview($event, it, card.imgKey)"
        @mouseleave="hidePreview"
        @click="goToActivitySearch(it.name)"
      />
      <div
        v-if="card.avatar"
        class="top-avatar"
        :style="{ background: avatarColors[i % avatarColors.length] }"
      >
        {{ (it.name || '?')[0].toUpperCase() }}
      </div>
      <span
        class="top-name"
        :class="{ 'top-name-clickable': card.avatar && it.user_id }"
        @click="
          card.avatar && it.user_id ? openUserProfile(it.user_id, it.name, $event) : null
        "
      >
        {{ it.name }}
      </span>
      <span class="top-val">{{ card.valFn ? card.valFn(it) : it[card.valKey] }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  card: { type: Object, required: true },
  avatarColors: { type: Array, required: true },
  showPreview: { type: Function, required: true },
  hidePreview: { type: Function, required: true },
  openUserProfile: { type: Function, required: true },
  goToActivitySearch: { type: Function, required: true },
})
</script>

<style scoped>
.top-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.top-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: rgb(255, 255, 255, 0.7);
}
.top-unit {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  color: rgb(255, 255, 255, 0.3);
}
.top-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: 6px 0;
}
.top-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 0.5px solid var(--border-subtle);
}
.top-item:last-child {
  border-bottom: none;
}
.top-rank {
  width: 16px;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-very-faint);
  text-align: center;
  flex-shrink: 0;
}
.top-thumb {
  width: 24px;
  height: 34px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--surface-2);
  cursor: pointer;
}
.top-name {
  flex: 1;
  font-size: var(--text-xs);
  color: rgb(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.top-name-clickable {
  cursor: pointer;
}
.top-name-clickable:hover {
  color: var(--accent-400);
  text-decoration: underline;
}
.top-val {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--accent-400);
  flex-shrink: 0;
}
.top-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.55rem;
  font-weight: var(--font-bold);
  color: var(--text-primary);
  flex-shrink: 0;
}
</style>
