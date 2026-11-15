<template>
  <div class="wzh-pv-page">
    <div class="wzh-pv-head">
      <div>
        <p class="wzh-pv-at">
          <i />
          {{ $t('portal.lists.title') }}
        </p>
        <p class="wzh-pv-asub">{{ $t('portal.lists.subtitle') }}</p>
      </div>
      <span class="wzh-pv-cta" :class="{ 'wzh-prs': pressCreate }">
        <Plus :size="16" :stroke-width="2.5" />
        {{ $t('portal.lists.createButton') }}
        <MousePointer2 v-if="pressCreate" class="wzh-cur" :size="22" />
      </span>
    </div>
    <p class="wzh-pv-ltabs">
      <span class="is-on">{{ $t('portal.lists.tabMine') }}</span>
      <span>{{ $t('portal.lists.tabPublic') }}</span>
    </p>
    <p class="wzh-pv-empty">{{ $t('portal.lists.emptyOwn') }}</p>
  </div>
</template>

<script setup>
// The « Listes » page, reduced, before the member has any list.
import { MousePointer2, Plus } from 'lucide-vue-next'

defineProps({
  pressCreate: { type: Boolean, default: false },
})
</script>
