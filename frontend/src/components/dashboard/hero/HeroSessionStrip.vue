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
        :src="s.avatar_url || userImages[s.user_id] || null"
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
import { computed, ref, watch } from 'vue'
import { useUserImages } from '@/composables/useUserImages'
import { useMobile } from '@/composables/useMobile'
import MkAvatar from '@/components/common/MkAvatar.vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  idx: { type: Number, default: 0 },
})
const emit = defineEmits(['go-to'])

const { getUserImageUrl } = useUserImages()
const { isMobile } = useMobile()
const userImages = ref({})

// 28 px on phones keeps four avatars + the "+N" badge inside the
// dashboard hero's compact right column without forcing the rest of
// the layout to wrap. Desktop stays at the original 36 px.
const avatarSize = computed(() => (isMobile.value ? 28 : 36))

watch(
  () => props.sessions,
  async sessions => {
    const userIds = [
      ...new Set(
        (sessions || [])
          .slice(0, 4)
          .map(s => s.user_id)
          .filter(id => id && !userImages.value[id]),
      ),
    ]
    if (!userIds.length) return
    const results = await Promise.all(userIds.map(async id => [id, await getUserImageUrl(id)]))
    const updates = Object.fromEntries(results.filter(([, url]) => url))
    if (Object.keys(updates).length) userImages.value = { ...userImages.value, ...updates }
  },
  { immediate: true },
)
</script>

<style scoped>
.hero-dots {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding-bottom: 4px;
}
.hero-dot-btn {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: rgb(255, 255, 255, 0.15);
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  transition: all var(--duration-slow);
}
.hero-dot-btn.active {
  background: var(--accent-500);
  border-color: rgb(255, 255, 255, 0.3);
  width: 10px;
  height: 10px;
}
.hero-dots-label {
  font-size: 9px;
  color: var(--text-very-faint);
  white-space: nowrap;
}
.hero-avatars {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  padding-bottom: 8px;
}
.hero-av-slot {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  /* Draws the separation between overlapping avatars without
     enlarging the box — keeps MkAvatar's internal sizing intact. */
  box-shadow: 0 0 0 2px var(--hero-bg, #0a0e1a);
}
.hero-av-more {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(255, 255, 255, 0.1);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-faint);
  box-shadow: 0 0 0 2px var(--hero-bg, #0a0e1a);
}
.hero-av-offset {
  margin-left: -8px;
}
.anim-slide-up {
  opacity: 0;
  transform: translateY(16px);
  animation: hero-slide-up 0.6s ease-out forwards;
}
@keyframes hero-slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.stg-55 {
  animation-delay: 0.55s;
}
.stg-60 {
  animation-delay: 0.6s;
}

@media (max-width: 767px) {
  .hero-dots {
    order: 2;
    flex-direction: row;
    padding-bottom: 0;
    align-items: center;
  }
  .hero-dots-label {
    font-size: var(--text-3xs);
  }
  .hero-avatars {
    order: 3;
    padding-bottom: 0;
    margin-left: auto;
  }
  /* Shrink the avatar stack to match the smaller phone hero so the
     row fits without wrapping and avatars no longer visually overlap
     into one blob — the ``avatarSize`` prop and the ring shadow are
     scaled together. */
  .hero-av-slot,
  .hero-av-more {
    width: 28px;
    height: 28px;
    box-shadow: 0 0 0 1.5px var(--hero-bg, #0a0e1a);
  }
  .hero-av-offset {
    margin-left: -6px;
  }
  .hero-av-more {
    font-size: var(--text-3xs);
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
