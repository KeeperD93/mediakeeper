<template>
  <div v-if="entries.length" class="pt-lb-podium" :data-count="entries.length">
    <router-link
      v-for="(entry, idx) in entries"
      :key="entry.user_id"
      :to="{ name: 'portal-user-profile', params: { id: entry.user_id } }"
      class="pt-lb-podium-card"
      :class="`pt-lb-podium-card--${rankFor(idx)}`"
    >
      <div class="pt-lb-podium-rank">#{{ rankFor(idx) }}</div>
      <component
        :is="medalFor(idx)"
        :size="22"
        :stroke-width="2.5"
        class="pt-lb-podium-medal"
        aria-hidden="true"
      />
      <div class="gc-lb-av" :class="`gc-lb-av--${entry.tier || 'bronze'}`">
        <MkAvatar :name="entry.display_name || ''" :src="entry.avatar_url || null" :size="84" />
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
import { Award, ChevronDown, ChevronUp, Medal } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  entries: { type: Array, default: () => [] },
})

const { t } = useI18n()

// Parent slices ``items.slice(1, 3)``: idx 0 → rank 2, idx 1 → rank 3.
function rankFor(idx) {
  return idx + 2
}
function medalFor(idx) {
  return idx === 0 ? Award : Medal
}
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.pt-lb-podium[data-count='1'] {
  grid-template-columns: minmax(0, 480px);
  justify-content: center;
}
.pt-lb-podium-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 16px 18px;
  min-height: 280px;
  border-radius: var(--portal-radius-lg);
  text-decoration: none;
  color: var(--portal-text-primary);
  transition:
    transform var(--portal-dur-med) var(--portal-ease-emphasis),
    box-shadow var(--portal-dur-med) var(--portal-ease-emphasis),
    border-color var(--portal-dur-med) var(--portal-ease-emphasis);
}
.pt-lb-podium-card--2 {
  background:
    linear-gradient(135deg, rgb(192, 192, 192, 0.08), transparent 70%),
    var(--portal-surface-1);
  border: 1px solid rgb(192, 192, 192, 0.3);
  box-shadow: 0 4px 24px rgb(192, 192, 192, 0.1);
}
.pt-lb-podium-card--3 {
  background:
    linear-gradient(135deg, rgb(205, 127, 50, 0.08), transparent 70%),
    var(--portal-surface-1);
  border: 1px solid rgb(205, 127, 50, 0.3);
  box-shadow: 0 4px 24px rgb(205, 127, 50, 0.1);
}
@media (hover: hover) {
  .pt-lb-podium-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--portal-shadow-popup);
  }
  .pt-lb-podium-card--2:hover {
    box-shadow:
      0 10px 30px rgb(192, 192, 192, 0.22),
      var(--portal-shadow-popup);
  }
  .pt-lb-podium-card--3:hover {
    box-shadow:
      0 10px 30px rgb(205, 127, 50, 0.22),
      var(--portal-shadow-popup);
  }
}
.pt-lb-podium-medal {
  position: absolute;
  top: 14px;
  right: 14px;
}
.pt-lb-podium-card--2 .pt-lb-podium-medal { color: #c0c0c0; }
.pt-lb-podium-card--3 .pt-lb-podium-medal { color: #cd7f32; }
.pt-lb-podium-rank {
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-black);
  font-family: var(--portal-font-display);
  line-height: 1;
}
.pt-lb-podium-card--2 .pt-lb-podium-rank { color: #c0c0c0; }
.pt-lb-podium-card--3 .pt-lb-podium-rank { color: #cd7f32; }
.pt-lb-podium-card :deep(.gc-lb-av) {
  width: 84px;
  height: 84px;
  /* Thicker ring on the larger podium avatar so the tier colour reads
     at this scale. The actual ring is drawn by MkAvatar's CSS border. */
  --mk-avatar-ring-width: 3px;
}
.pt-lb-podium-name {
  font-size: var(--portal-text-lg);
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
  gap: 2px;
  font-size: var(--portal-text-3xs);
  color: var(--portal-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
}
.pt-lb-podium-xp {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-extrabold);
  font-family: var(--portal-font-display);
}
.pt-lb-podium-card--2 .pt-lb-podium-xp { color: #c0c0c0; }
.pt-lb-podium-card--3 .pt-lb-podium-xp { color: #cd7f32; }
.pt-lb-podium-move {
  min-width: 36px;
}
@media (max-width: 640px) {
  .pt-lb-podium {
    grid-template-columns: minmax(0, 1fr);
  }
  .pt-lb-podium-card {
    min-height: 200px;
    padding: 18px 14px;
  }
}
</style>
