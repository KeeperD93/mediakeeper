<template>
  <span ref="wrapRef" class="sub-stars-wrap" @click.stop="open = !open">
    <span class="sub-stars">
      <Star
        v-for="i in 5"
        :key="i"
        :size="11"
        :class="i <= Math.round(score) ? 'star-filled' : 'star-empty'"
        :fill="i <= Math.round(score) ? '#fbbf24' : 'rgba(255,255,255,.08)'"
        stroke="none"
      />
    </span>
    <Teleport to="body">
      <transition name="sq-fade">
        <div v-if="open" class="sq-popup" :style="popupPos" @click.stop>
          <div class="sq-header">
            <span class="sq-title">{{ $t('subtitles.qualityScore') }}</span>
            <span class="sq-total">{{ score.toFixed(1) }}/5</span>
          </div>
          <div class="sq-rows">
            <div class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreBase') }}</span>
              <span class="sq-val sq-neutral">2.5</span>
            </div>
            <div v-if="result.hash_match" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreHash') }}</span>
              <span class="sq-val sq-pos">+1.0</span>
            </div>
            <div v-if="result.from_trusted" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreTrusted') }}</span>
              <span class="sq-val sq-pos">+0.6</span>
            </div>
            <div v-if="result.ratings" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreRatings') }}</span>
              <span class="sq-val sq-pos">+{{ ratingsBonus }}</span>
            </div>
            <div v-if="result.download_count > 1000" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreDownloads') }}</span>
              <span class="sq-val sq-pos">+0.2</span>
            </div>
            <div v-if="result.ai_translated" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreAi') }}</span>
              <span class="sq-val sq-neg">-0.8</span>
            </div>
            <div v-if="result.machine_translated" class="sq-row">
              <span class="sq-label">{{ $t('subtitles.scoreMachine') }}</span>
              <span class="sq-val sq-neg">-1.0</span>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </span>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Star } from 'lucide-vue-next'
import { rootZoom } from '@/utils/zoom'

const props = defineProps({
  score: { type: Number, default: 0 },
  result: { type: Object, default: () => ({}) },
})

const open = ref(false)
const wrapRef = ref(null)
const popupPos = ref({})

const ratingsBonus = computed(() => {
  if (!props.result.ratings) return '0'
  return Math.min(0.5, (props.result.ratings / 10) * 0.5).toFixed(1)
})

function updatePos() {
  if (!wrapRef.value) return
  const z = rootZoom() // admin zoom: divide the final position (utils/zoom)
  const r = wrapRef.value.getBoundingClientRect()
  popupPos.value = {
    position: 'fixed',
    left: r.left / z + 'px',
    top: (r.bottom + 6) / z + 'px',
    zIndex: 9999,
  }
}

function onClickOutside(e) {
  if (open.value && wrapRef.value && !wrapRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  window.addEventListener('scroll', updatePos, true)
})
onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('scroll', updatePos, true)
})

watch(open, v => {
  if (v) updatePos()
})
</script>

<style scoped>
.sub-stars-wrap {
  position: relative;
  cursor: pointer;
  display: inline-flex;
}
.sub-stars {
  display: inline-flex;
  gap: 1px;
  vertical-align: middle;
}
.star-filled {
  filter: drop-shadow(0 0 2px rgb(var(--color-warning-rgb), 0.3));
}

.sq-popup {
  width: 240px;
  padding: 12px 14px;
  border-radius: var(--radius-card);
  background: var(--bg-secondary);
  border: 1px solid var(--border-strong);
  box-shadow: 0 12px 40px rgb(0, 0, 0, 0.5);
}
.sq-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.sq-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.sq-total {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-warning);
}

.sq-rows {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.sq-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sq-label {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.sq-val {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  font-family: 'SF Mono', monospace;
}
.sq-neutral {
  color: var(--text-muted);
}
.sq-pos {
  color: var(--color-success);
}
.sq-neg {
  color: var(--color-error);
}

.sq-fade-enter-active,
.sq-fade-leave-active {
  transition:
    opacity var(--duration-fast),
    transform var(--duration-fast);
}
.sq-fade-enter-from,
.sq-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
