<template>
  <span class="ru-badge" :class="`ru-badge--${variant}`">
    <slot />
  </span>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'neutral' },
})
</script>
