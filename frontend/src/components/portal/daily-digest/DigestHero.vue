<template>
  <header class="dd-hero">
    <AvatarFrame
      class="dd-hero-av"
      :src="me?.avatar_url || null"
      :name="me?.display_name || ''"
      :size="56"
      :tier="me?.tier || null"
      :effect="me?.avatar_effect || null"
      aria-hidden="true"
    />
    <div class="dd-grow">
      <span class="dd-date">{{ date }}</span>
      <h1 class="dd-hello">{{ greeting }}</h1>
      <p class="dd-sub">{{ $t('portal.dailyDigest.subtitle') }}</p>
    </div>
  </header>
</template>

<script setup>
import AvatarFrame from '@/components/portal/common/AvatarFrame.vue'

defineProps({
  // The viewer as others see them: public name, avatar, frame and tier.
  me: { type: Object, default: null },
  date: { type: String, required: true },
  greeting: { type: String, required: true },
})
</script>
