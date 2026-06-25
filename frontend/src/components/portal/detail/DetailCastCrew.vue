<template>
  <section class="vmd2-section">
    <template v-if="media.cast?.length">
      <h2>{{ $t('portal.detail.cast') }}</h2>
      <div class="vmd2-cast-grid">
        <router-link
          v-for="c in media.cast"
          :key="c.id || c.name"
          :to="{ name: 'portal-person', params: { id: c.id }, query: { role: PERSON_ROLE.ACTING } }"
          class="vmd2-cast-card"
        >
          <img v-if="c.photo" :src="c.photo" :alt="c.name" class="vmd2-cast-photo" loading="lazy" />
          <div v-else class="vmd2-cast-photo vmd2-cast-photo--empty">
            <User :size="28" :stroke-width="1.5" :opacity="0.3" />
          </div>
          <span class="vmd2-cast-name">{{ c.name }}</span>
          <span v-if="c.character" class="vmd2-cast-role">{{ c.character }}</span>
        </router-link>
      </div>
    </template>

    <template v-if="keyCrewGroups.length">
      <h2 class="vmd2-section-break">{{ $t('portal.detail.keyCrew') }}</h2>
      <div class="vmd2-crew-grid">
        <div v-for="entry in keyCrewGroups" :key="entry.job + entry.names" class="vmd2-crew-card">
          <span class="vmd2-crew-role">{{ translateJob(entry.job) }}</span>
          <span class="vmd2-crew-name">{{ entry.names }}</span>
        </div>
      </div>
    </template>

    <div v-if="!media.cast?.length && !keyCrewGroups.length" class="vmd2-empty">
      {{ $t('portal.detail.noCredits') }}
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { User } from 'lucide-vue-next'
import { PERSON_ROLE } from '@/constants/portal'

const props = defineProps({
  media: { type: Object, required: true },
})

const { t, te } = useI18n()

const keyCrewGroups = computed(() => {
  const list = props.media.key_crew || []
  const byJob = new Map()
  for (const c of list) {
    if (!byJob.has(c.job)) byJob.set(c.job, [])
    byJob.get(c.job).push(c.name)
  }
  return Array.from(byJob.entries()).map(([job, names]) => ({
    job,
    names: Array.from(new Set(names)).join(', '),
  }))
})

function translateJob(job) {
  const key = `portal.detail.job.${job}`
  return te(key) ? t(key) : job
}
</script>

<style scoped>
.vmd2-cast-photo--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--portal-surface-3);
}
</style>
