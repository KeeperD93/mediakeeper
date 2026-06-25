<template>
  <div class="vmd-detail-carousels">
    <!-- By the director X -->
    <MediaCarousel
      v-if="directorFilmo.items.length"
      :title="$t('portal.detail.byDirector', { name: director?.name || '' })"
      :items="directorFilmo.items.slice(0, 20)"
      card-width="160px"
      :title-route="
        director?.id
          ? {
              name: 'portal-person',
              params: { id: director.id },
              query: { role: PERSON_ROLE.DIRECTOR },
            }
          : null
      "
      @select="$emit('select', $event)"
      @request="$emit('request', $event)"
    />

    <!-- With lead actor Y -->
    <MediaCarousel
      v-if="actorFilmo.items.length"
      :title="$t('portal.detail.withActor', { name: leadActor?.name || '' })"
      :items="actorFilmo.items.slice(0, 20)"
      card-width="160px"
      :title-route="
        leadActor?.id
          ? {
              name: 'portal-person',
              params: { id: leadActor.id },
              query: { role: PERSON_ROLE.ACTING },
            }
          : null
      "
      @select="$emit('select', $event)"
      @request="$emit('request', $event)"
    />

    <!-- In the same franchise -->
    <MediaCarousel
      v-if="collection?.items?.length"
      :title="$t('portal.detail.inFranchise', { name: collection.collection?.name || '' })"
      :items="collection.items"
      card-width="160px"
      :title-route="
        collection.collection?.id
          ? { name: 'portal-collection', params: { id: collection.collection.id } }
          : null
      "
      @select="$emit('select', $event)"
      @request="$emit('request', $event)"
    />
  </div>
</template>

<script setup>
import MediaCarousel from '@/components/portal/MediaCarousel.vue'
import { PERSON_ROLE } from '@/constants/portal'

defineProps({
  director: { type: Object, default: null },
  leadActor: { type: Object, default: null },
  directorFilmo: { type: Object, default: () => ({ items: [] }) },
  actorFilmo: { type: Object, default: () => ({ items: [] }) },
  collection: { type: Object, default: null },
})
defineEmits(['select', 'request'])
</script>

<style scoped>
/* Plain flex column — vertical rhythm between the nested MediaCarousels
   is entirely driven by .pt-carousel-header's margin-top/bottom tokens,
   so the spacing reads identically to the portal home (no extra gap, no
   wrapper-level margin-top that would stack on top of the header's). */
.vmd-detail-carousels {
  display: flex;
  flex-direction: column;
}
</style>
