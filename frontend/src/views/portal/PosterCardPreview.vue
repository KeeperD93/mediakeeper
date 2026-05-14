<template>
  <main class="dev-preview">
    <header class="dev-preview__header">
      <h1>PosterCard — visual matrix</h1>
      <p>Dev-only preview. All states rendered against the portal dark backdrop.</p>
    </header>

    <section v-for="group in groups" :key="group.title" class="dev-preview__section">
      <h2>{{ group.title }}</h2>
      <div class="dev-preview__grid">
        <figure v-for="item in group.items" :key="item.caption" class="dev-preview__item">
          <PosterCard v-bind="item.props" />
          <figcaption>{{ item.caption }}</figcaption>
        </figure>
      </div>
    </section>
  </main>
</template>

<script setup>
import PosterCard from '@/components/portal/PosterCard.vue'

const SAMPLE_TITLE_A = 'Le Comte de Monte-Cristo'
const SAMPLE_TITLE_B = 'Dune: Prophecy'
const SAMPLE_TITLE_C = 'Severance'
const SAMPLE_TITLE_D = 'The Bear'

function poster(overrides) {
  return {
    title: SAMPLE_TITLE_A,
    year: 2024,
    duration: '2 h 58',
    image: null,
    ...overrides,
  }
}

const groups = [
  {
    title: 'Availability',
    items: [
      { caption: 'Available', props: poster({ availability: 'full' }) },
      { caption: 'Available + New', props: poster({ availability: 'full', isNew: true }) },
      {
        caption: 'Partial',
        props: poster({ title: SAMPLE_TITLE_B, year: 2024, availability: 'partial' }),
      },
    ],
  },
  {
    title: 'Request lifecycle',
    items: [
      { caption: 'Pending', props: poster({ title: SAMPLE_TITLE_C, status: 'pending' }) },
      { caption: 'Approved', props: poster({ title: SAMPLE_TITLE_C, status: 'approved' }) },
      {
        caption: 'Rejected ×3',
        props: poster({ title: SAMPLE_TITLE_D, status: 'rejected', count: 3 }),
      },
      { caption: 'Blacklisted', props: poster({ status: 'blacklisted' }) },
    ],
  },
  {
    title: 'Watch status',
    items: [
      {
        caption: 'In progress',
        props: poster({ title: SAMPLE_TITLE_C, status: 'in_progress' }),
      },
      { caption: 'Watched', props: poster({ title: SAMPLE_TITLE_D, status: 'watched' }) },
    ],
  },
  {
    title: 'Bookmark + combos',
    items: [
      { caption: 'Bookmarked', props: poster({ bookmarked: true }) },
      {
        caption: 'Available + Bookmarked + Watched',
        props: poster({
          title: SAMPLE_TITLE_B,
          availability: 'full',
          bookmarked: true,
          status: 'watched',
        }),
      },
      {
        caption: 'Partial + In progress + Bookmarked',
        props: poster({
          title: SAMPLE_TITLE_C,
          availability: 'partial',
          bookmarked: true,
          status: 'in_progress',
        }),
      },
      {
        caption: 'Image fallback (no poster URL)',
        props: poster({
          title: 'A movie with a very long title that should clamp at two lines',
          image: null,
          availability: 'full',
        }),
      },
    ],
  },
]
</script>

<style scoped>
.dev-preview {
  min-height: 100vh;
  background: var(--portal-poster-bg);
  color: var(--portal-text-primary);
  padding: clamp(16px, 4vw, 48px);
  overflow-x: clip;
  -webkit-tap-highlight-color: transparent;
}

.dev-preview__header {
  margin-bottom: 32px;
}

.dev-preview__header h1 {
  font-family: var(--portal-font-display);
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-extrabold);
  margin: 0 0 4px;
}

.dev-preview__header p {
  margin: 0;
  color: var(--portal-text-secondary);
  font-size: var(--portal-text-sm);
}

.dev-preview__section {
  margin-bottom: 40px;
}

.dev-preview__section h2 {
  font-family: var(--portal-font-display);
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  letter-spacing: var(--portal-tracking-eyebrow);
  text-transform: uppercase;
  color: var(--portal-text-body-muted);
  margin: 0 0 16px;
}

.dev-preview__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(185px, 1fr));
  gap: 24px;
}

.dev-preview__item {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.dev-preview__item figcaption {
  font-family: var(--portal-font-mono);
  font-size: var(--portal-text-xs);
  color: var(--portal-text-secondary);
  letter-spacing: var(--portal-tracking-wide);
}
</style>
