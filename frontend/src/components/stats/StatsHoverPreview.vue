<template>
  <div
    v-if="preview.show"
    class="hover-preview"
    :style="{ top: preview.y + 'px', left: preview.x + 'px' }"
  >
    <img :src="preview.img" class="preview-img" @error="hidePreview" />
    <span class="preview-name">{{ preview.name }}</span>
  </div>
</template>

<script setup>
import { useStatsUI } from '@/composables/useStatsUI'
const { preview, hidePreview } = useStatsUI()
</script>

<style scoped>
.hover-preview {
  position: fixed;
  z-index: 1000;
  background: rgb(15, 20, 35, 0.95);
  backdrop-filter: var(--blur-sm);
  border: 0.5px solid rgb(255, 255, 255, 0.1);
  border-radius: var(--radius-btn);
  padding: 6px;
  pointer-events: none;
  animation: sh-preview-in var(--duration-fast) ease;
}
.preview-img {
  width: 120px;
  height: 180px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  display: block;
}
.preview-name {
  display: block;
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin-top: 6px;
  text-align: center;
  max-width: 120px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@keyframes sh-preview-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
