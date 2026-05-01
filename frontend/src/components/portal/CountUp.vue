<template>
  <span ref="el">{{ display }}</span>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 800 },
  // Optional: custom formatter (toLocaleString by default).
  formatter: { type: Function, default: (n) => Math.round(n).toLocaleString() },
  // Optional: delay (ms) before the animation actually starts — lets
  // siblings stagger their count-up so the screen reveals progressively.
  delay: { type: Number, default: 0 },
})

const display = ref('')
const el = ref(null)
let rafId = null
let timeoutId = null
let observer = null

function prefersReduced() {
  return typeof window !== 'undefined'
    && window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function animate(target) {
  if (rafId) cancelAnimationFrame(rafId)
  const start = 0
  const end = Number(target) || 0
  if (prefersReduced() || !props.duration || end === start) {
    display.value = props.formatter(end)
    return
  }
  const startTime = performance.now()
  const step = (now) => {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / props.duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = props.formatter(start + (end - start) * eased)
    if (progress < 1) {
      rafId = requestAnimationFrame(step)
    } else {
      rafId = null
    }
  }
  rafId = requestAnimationFrame(step)
}

function scheduleAnimate(target) {
  if (timeoutId) clearTimeout(timeoutId)
  display.value = props.formatter(0)
  if (props.delay > 0) {
    timeoutId = setTimeout(() => animate(target), props.delay)
  } else {
    animate(target)
  }
}

watch(() => props.value, (val) => scheduleAnimate(val))

onMounted(() => {
  display.value = props.formatter(0)
  if (!props.value) return
  // Kick in as soon as the element is on screen so counters that sit
  // below the fold still play their animation when the user scrolls to
  // them (avoids "already finished" when the section appears).
  if (typeof IntersectionObserver === 'undefined' || !el.value) {
    scheduleAnimate(props.value)
    return
  }
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        scheduleAnimate(props.value)
        observer.disconnect()
        observer = null
      }
    },
    { threshold: 0.3 },
  )
  observer.observe(el.value)
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (timeoutId) clearTimeout(timeoutId)
  if (observer) observer.disconnect()
})
</script>
