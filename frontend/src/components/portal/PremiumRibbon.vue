<template>
  <div class="mk-ribbon-wrap">
    <div
      class="mk-ribbon"
      :class="{ 'mk-ribbon--pulse': pulse }"
      :style="{ '--mk-ribbon-c': bg }"
      :title="title || null"
    >
      <span>{{ label }}{{ count > 1 ? ` ×${count}` : '' }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  // CSS color expression (typically a portal token reference, e.g.
  // 'var(--portal-color-success)'). The ribbon gradient + pulse glow
  // are derived from it in poster-card.css via color-mix / opacity.
  bg: { type: String, required: true },
  label: { type: String, required: true },
  count: { type: Number, default: 1 },
  pulse: { type: Boolean, default: false },
  // Native `title` attribute. Surfaces the request/watch date so the
  // ribbon can replace the legacy bronze post-it tooltip.
  title: { type: String, default: '' },
})
</script>
