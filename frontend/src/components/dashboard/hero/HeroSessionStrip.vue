<template>
  <div class="hero-dots anim-slide-up stg-55">
    <button
      v-for="(s, i) in sessions"
      :key="i"
      class="hero-dot-btn"
      :class="{ active: i === idx }"
      @click="emit('go-to', i)"
    />
    <span class="hero-dots-label">
      {{ $t('dashboard.activeCount', { count: sessions.length }) }}
    </span>
  </div>
  <div class="hero-avatars anim-slide-up stg-60">
    <div
      v-for="(s, i) in sessions.slice(0, 4)"
      :key="i"
      class="hero-av-slot"
      :class="{ 'hero-av-offset': i > 0 }"
      :title="s.user || '?'"
      :style="{ zIndex: 10 - i }"
    >
      <MkAvatar
        :src="s.avatar_url"
        :name="s.user || '?'"
        :size="avatarSize"
        :tier="s.tier || 'bronze'"
      />
    </div>
    <div
      v-if="sessions.length > 4"
      class="hero-av-more hero-av-offset"
      :title="$t('dashboard.activeCount', { count: sessions.length })"
    >
      +{{ sessions.length - 4 }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMobile } from '@/composables/useMobile'
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  idx: { type: Number, default: 0 },
})
defineEmits(['go-to'])

const { isMobile } = useMobile()

// 28 px on phones keeps four avatars + the "+N" badge inside the
// dashboard hero's compact right column without forcing the rest of
// the layout to wrap. Desktop stays at the original 36 px.
const avatarSize = computed(() => (isMobile.value ? 28 : 36))
</script>

<style scoped>
.hero-dots {
  display: flex;
  /* Mobile-first — dots inline on phones (order: 2, padding-bottom: 0).
     Desktop stacks them vertically with padding-bottom space-1 via the
     @media (min-width: 768px) block. */
  order: 2;
  flex-direction: row;
  align-items: center;
  /* 6 px between bullets — between --space-1 (4) and --space-2 (8). */
  gap: 6px;
  flex-shrink: 0;
  padding-bottom: 0;
}
.hero-dot-btn {
  /* 9 / 10 px bullets — too small for any --icon-* token (12+). */
  width: 9px;
  height: 9px;
  border-radius: var(--radius-circle);
  background: var(--border-ghost);
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  /* Explicit transitions on the 4 properties that change between the
     idle and active state — avoid `transition: all` for perf + to
     prevent side-effect transitions on unrelated properties. */
  transition:
    background var(--duration-slow),
    border-color var(--duration-slow),
    width var(--duration-slow),
    height var(--duration-slow);
}
.hero-dot-btn.active {
  background: var(--accent-500);
  border-color: var(--border-ghost-hover);
  width: 10px;
  height: 10px;
}
.hero-dots-label {
  /* Mobile-first label — --text-3xs. Desktop bumps to a 9 px literal
     to match the dot cluster's compactness (cf. min-width: 768px). */
  font-size: var(--text-3xs);
  color: var(--text-very-faint);
  white-space: nowrap;
}
.hero-avatars {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  /* Mobile-first — avatars on the right of the row (order: 3),
     no bottom padding. Desktop adds space-2 via min-width: 768px. */
  order: 3;
  margin-left: auto;
  padding-bottom: 0;
}
.hero-av-slot {
  position: relative;
  /* Mobile-first 28 px (icon-frame-sm) — desktop bumps to icon-frame-md
     (36 px) via the @media (min-width: 768px) block. */
  width: var(--icon-frame-sm);
  height: var(--icon-frame-sm);
  border-radius: var(--radius-circle);
  /* Draws the separation between overlapping avatars without
     enlarging the box — keeps MkAvatar's internal sizing intact.
     1.5 px ring on phones — between --border-width-thin (0.5) and
     --border-width (1) to halve the rim without disappearing.
     Desktop uses 2 px via the min-width block. */
  box-shadow: 0 0 0 1.5px var(--hero-bg);
}
.hero-av-more {
  position: relative;
  width: var(--icon-frame-sm);
  height: var(--icon-frame-sm);
  border-radius: var(--radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-3);
  font-size: var(--text-3xs);
  font-weight: var(--font-medium);
  color: var(--text-faint);
  box-shadow: 0 0 0 1.5px var(--hero-bg);
}
.hero-av-offset {
  /* 6 px overlap on phones — between --space-1 and --space-2.
     Desktop uses calc(var(--space-2) * -1) via the min-width block. */
  margin-left: -6px;
}
.anim-slide-up {
  opacity: 0;
  transform: translateY(16px);
  /* 0.6 s — hero-only signature (also used in HeroSlideContent),
     outside the --duration-* scale (slower 0.5). Accepted as literal
     since the value is unique to the hero strip. */
  animation: hero-slide-up 0.6s ease-out forwards;
}
@keyframes hero-slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
/* Stagger delays — orchestrate the cascade of hero strip elements
   (dots → avatars). Sub-second values intentionally unique per stage,
   not tokenized (each delay is one-off by design). */
.stg-55 {
  animation-delay: 0.55s;
}
.stg-60 {
  animation-delay: 0.6s;
}

@media (min-width: 768px) {
  /* Restore the vertical bullet cluster + stacked layout for the
     wider hero — mirrors the original desktop signature. */
  .hero-dots {
    order: 0;
    flex-direction: column;
    padding-bottom: var(--space-1);
  }
  .hero-dots-label {
    /* 9 px micro-meta below --text-3xs (~9.9 px) — keeps the
       bullets-and-count cluster compact on wide screens. */
    font-size: 9px;
  }
  .hero-avatars {
    order: 0;
    padding-bottom: var(--space-2);
    margin-left: 0;
  }
  .hero-av-slot,
  .hero-av-more {
    width: var(--icon-frame-md);
    height: var(--icon-frame-md);
    box-shadow: 0 0 0 2px var(--hero-bg);
  }
  .hero-av-offset {
    margin-left: calc(var(--space-2) * -1);
  }
  .hero-av-more {
    font-size: var(--text-2xs);
  }
}

@media (prefers-reduced-motion: reduce) {
  .anim-slide-up {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
</style>
