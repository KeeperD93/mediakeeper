<template>
  <div v-if="entries.length >= 3" class="pt-lb-podium">
    <router-link
      v-for="(entry, idx) in entries"
      :key="entry.user_id"
      :to="{ name: 'portal-user-profile', params: { id: entry.user_id } }"
      class="pt-lb-podium-card"
      :class="`pt-lb-podium-card--${idx + 1}`"
    >
      <div class="pt-lb-podium-rank">#{{ idx + 1 }}</div>
      <div class="gc-lb-av" :class="`gc-lb-av--${entry.tier || 'bronze'}`">
        <MkAvatar :name="entry.display_name || ''" :src="entry.avatar_url || null" :size="64" />
      </div>
      <div class="pt-lb-podium-name">{{ entry.display_name }}</div>
      <div class="pt-lb-podium-meta">
        <span class="pt-lb-podium-level">{{ $t('portal.level') }} {{ entry.level }}</span>
        <span class="pt-lb-podium-title">
          {{ $t(`portal.profile.titles.${entry.title_key || 'spectator'}`) }}
        </span>
      </div>
      <div class="pt-lb-podium-xp">{{ (entry.month_xp || 0).toLocaleString() }} XP</div>
      <span
        class="gc-lb-move pt-lb-podium-move"
        :class="moveClass(entry.movement)"
        :title="moveTooltip(entry.movement)"
      >
        <ChevronUp v-if="entry.movement > 0" :size="11" :stroke-width="3.5" />
        <ChevronDown v-else-if="entry.movement < 0" :size="11" :stroke-width="3.5" />
        <span v-else>—</span>
        <span v-if="entry.movement">{{ Math.abs(entry.movement) }}</span>
      </span>
    </router-link>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  entries: { type: Array, default: () => [] },
})

const { t } = useI18n()
function moveClass(movement) {
  if (!movement) return 'gc-lb-move--flat'
  return movement > 0 ? 'gc-lb-move--up' : 'gc-lb-move--down'
}
function moveTooltip(movement) {
  if (!movement) return t('portal.profile.rankStable')
  const key = movement > 0 ? 'portal.profile.rankUp' : 'portal.profile.rankDown'
  return t(key, { n: Math.abs(movement) })
}
</script>

<style scoped>
.pt-lb-podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}
.pt-lb-podium-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
  padding: 1.25rem 0.85rem 1.1rem;
  border-radius: var(--radius-card);
  background:
    linear-gradient(180deg, rgb(var(--accent-rgb), 0.05) 0%, transparent 70%),
    var(--portal-surface-1);
  border: 1px solid rgb(255, 255, 255, 0.06);
  color: var(--text-primary);
  text-decoration: none;
  transition:
    transform var(--portal-dur-fast) var(--portal-ease-emphasis),
    box-shadow var(--portal-dur-fast) var(--portal-ease-emphasis),
    border-color var(--portal-dur-fast) var(--portal-ease-emphasis);
}
.pt-lb-podium-card--1 {
  order: 2;
  border-color: rgb(var(--portal-color-warning-rgb), 0.45);
  box-shadow: 0 6px 20px rgb(var(--portal-color-warning-rgb), 0.12);
}
.pt-lb-podium-card--2 {
  order: 1;
  border-color: rgb(192, 192, 192, 0.4);
}
.pt-lb-podium-card--3 {
  order: 3;
  border-color: rgb(205, 127, 50, 0.45);
}
@media (hover: hover) {
  .pt-lb-podium-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--portal-shadow-popup);
  }
}
.pt-lb-podium-rank {
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-black);
  font-family: var(--portal-font-display);
  color: var(--accent);
}
.pt-lb-podium-card--1 .pt-lb-podium-rank {
  color: var(--portal-color-warning);
}
.pt-lb-podium-card--2 .pt-lb-podium-rank {
  color: #c0c0c0;
}
.pt-lb-podium-card--3 .pt-lb-podium-rank {
  color: #cd7f32;
}
.pt-lb-podium-card :deep(.gc-lb-av) {
  width: 72px;
  height: 72px;
  padding: 3px;
}
.pt-lb-podium-name {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pt-lb-podium-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  font-size: var(--portal-text-3xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.pt-lb-podium-xp {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--accent);
  font-family: var(--portal-font-display);
}
.pt-lb-podium-move {
  min-width: 36px;
}
@media (max-width: 640px) {
  .pt-lb-podium {
    grid-template-columns: 1fr;
  }
  .pt-lb-podium-card--1,
  .pt-lb-podium-card--2,
  .pt-lb-podium-card--3 {
    order: unset;
  }
}
</style>
