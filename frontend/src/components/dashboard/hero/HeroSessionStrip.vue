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
      class="hero-av"
      :class="{ 'hero-av-offset': i > 0 }"
      :style="{ background: avColors[i % avColors.length], zIndex: 10 - i }"
    >
      <img
        v-if="userImages[s.user_id]"
        :src="userImages[s.user_id]"
        class="hero-av-img"
        @error="$event => $event.target.remove()"
      />
      <span>{{ (s.user || '?')[0].toUpperCase() }}</span>
    </div>
    <div v-if="sessions.length > 4" class="hero-av hero-av-more hero-av-offset">
      +{{ sessions.length - 4 }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useUserImages } from '@/composables/useUserImages'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  idx: { type: Number, default: 0 },
})
const emit = defineEmits(['go-to'])

const { getUserImageUrl } = useUserImages()
const userImages = ref({})
const avColors = ['#6366f1', '#0ea5e9', '#f59e0b', '#ec4899', '#22c55e']

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
.hero-av {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--hero-bg, #0a0e1a);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: #fff;
  position: relative;
  overflow: hidden;
}
.hero-av-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}
.hero-av-more {
  background: rgb(255, 255, 255, 0.1);
  font-size: var(--text-2xs);
  color: var(--text-faint);
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
}
</style>
