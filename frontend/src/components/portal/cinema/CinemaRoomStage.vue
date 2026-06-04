<template>
  <!-- Ceiling: dome with rows of recessed spots + projector beam -->
  <div class="pt-cr-ceiling">
    <div class="pt-cr-ceiling-row">
      <span v-for="i in 16" :key="`ca${i}`" class="pt-cr-spot" />
    </div>
    <div class="pt-cr-ceiling-row pt-cr-ceiling-row--2">
      <span v-for="i in 14" :key="`cb${i}`" class="pt-cr-spot pt-cr-spot--small" />
    </div>
    <div class="pt-cr-projector" />
  </div>

  <!-- Side walls with LED aisle strip -->
  <div class="pt-cr-wall pt-cr-wall--left">
    <span class="pt-cr-led" />
  </div>
  <div class="pt-cr-wall pt-cr-wall--right">
    <span class="pt-cr-led" />
  </div>

  <div class="pt-cr-floor" />

  <div class="pt-cr-curtain pt-cr-curtain--left" />
  <div class="pt-cr-curtain pt-cr-curtain--right" />
  <div class="pt-cr-pelmet" />
</template>

<script setup></script>
