<template>
  <div class="mk-ribbon-wrap">
    <div
      class="mk-ribbon"
      :class="{ 'mk-ribbon--pulse': pulse }"
      :style="{ '--mk-ribbon-c': bg }"
    >
      <span>{{ label }}{{ count > 1 ? ` ×${count}` : '' }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  // CSS color expression (typically a portal token reference, e.g.
  // 'var(--portal-color-success)'). The component derives the gradient
  // and pulse glow from it via color-mix.
  bg: { type: String, required: true },
  label: { type: String, required: true },
  count: { type: Number, default: 1 },
  pulse: { type: Boolean, default: false },
})
</script>
