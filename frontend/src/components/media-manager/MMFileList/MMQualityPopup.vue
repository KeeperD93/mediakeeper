<template>
  <Teleport to="body">
    <div
      v-if="qualityPopup.visible"
      class="mm-quality-popup"
      :style="{ left: qualityPopup.x + 'px', top: qualityPopup.y + 'px' }"
    >
      <div class="mm-qp-header">
        <span class="mm-qp-score" :style="{ color: getQualityColor(qualityPopup.score) }">
          {{ qualityPopup.score }}/100
        </span>
      </div>
      <div v-if="qualityPopup.penalties.length" class="mm-qp-penalties">
        <div v-for="(p, i) in qualityPopup.penalties" :key="i" class="mm-qp-penalty">
          <span class="mm-qp-penalty-points">-{{ p.points }}</span>
          {{ p.label }}
        </div>
      </div>
      <div v-else class="mm-qp-perfect">{{ $t('mediaManager.qualityPerfect') }}</div>
      <hr class="mm-qp-sep" />
      <div class="mm-qp-example-label">{{ $t('mediaManager.qualityExample100') }}</div>
      <div class="mm-qp-example-code">Avatar (2024) 1080p x265 DTS.mkv</div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  qualityPopup: { type: Object, required: true },
  getQualityColor: { type: Function, required: true },
})
</script>

<style scoped>
.mm-qp-penalty-points {
  color: var(--color-error);
}
.mm-qp-perfect {
  font-size: var(--text-2xs);
  color: var(--mm-green);
}
.mm-qp-sep {
  border-color: var(--border);
  margin: 0.4rem 0;
}
.mm-qp-example-label {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}
.mm-qp-example-code {
  font-family: monospace;
  font-size: 0.63rem;
  color: var(--accent-400);
  margin-top: 0.2rem;
  word-break: break-all;
}
</style>
