<template>
  <section
    :aria-label="$t('portal.dailyDigest.boost.section')"
    :class="compact ? 'ddc-box' : 'dd-more-news dd-boost-list'"
  >
    <DigestBoostRow
      v-for="view in views"
      :key="view.key"
      :boost="view"
      :open="openKey === view.key"
      :compact="compact"
      @toggle="toggle(view.key)"
    />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { boostView } from '@/utils/portal/dailyDigest'
import DigestBoostRow from './DigestBoostRow.vue'

const props = defineProps({
  // The XP boosts running now, alone when there is no news to list them under.
  boosts: { type: Array, required: true },
  compact: { type: Boolean, default: false },
})

const views = computed(() => props.boosts.map(boost => boostView(boost)))
const openKey = ref(null)

// One open at a time, like the rows of the news list.
function toggle(key) {
  openKey.value = openKey.value === key ? null : key
}
</script>
