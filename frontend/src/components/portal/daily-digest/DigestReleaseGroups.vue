<template>
  <div class="dd-release-all">
    <template v-for="group in groups" :key="group.name">
      <div class="dd-release-group">
        <span class="dd-release-cat" :class="group.toneClass">
          {{ group.labelKey ? $t(group.labelKey) : group.name }}
        </span>
        <span class="dd-release-n">{{ group.count }}</span>
      </div>
      <ul class="dd-release-list">
        <li v-for="(text, i) in group.items" :key="i">{{ text }}</li>
      </ul>
    </template>
  </div>
</template>

<script setup>
import '@/assets/styles/portal/daily-digest-release-list.css'

defineProps({
  // Sections of the version, as releaseView() draws them.
  groups: { type: Array, required: true },
})
</script>
