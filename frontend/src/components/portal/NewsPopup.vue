<template>
  <Teleport to="body">
    <div class="pt-popup-overlay" @click.self="$emit('dismiss')">
      <div class="pt-popup">
        <div class="pt-popup-header">
          <h2>{{ $t('portal.news.whatsNew') }}</h2>
          <button
            class="pt-popup-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="$emit('dismiss')"
          >
            <X :size="14" />
          </button>
        </div>
        <div class="pt-popup-body">
          <div v-for="item in items" :key="item.id" class="pt-news-item">
            <div class="pt-news-badge" :class="`pt-news-badge--${item.type}`">
              {{ $t(`portal.news.types.${item.type}`) }}
            </div>
            <h3 class="pt-news-title">{{ item.title }}</h3>
            <p class="pt-news-content">{{ item.content }}</p>
            <span class="pt-news-date">
              {{ new Date(item.created_at).toLocaleDateString() }}
            </span>
          </div>
          <div v-if="!items.length" class="pt-news-empty">
            {{ $t('portal.news.noNews') }}
          </div>
        </div>
        <div class="pt-popup-footer">
          <button class="pt-popup-btn" @click="$emit('dismiss')">
            {{ $t('portal.news.gotIt') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  items: { type: Array, default: () => [] },
})
defineEmits(['dismiss'])
</script>

<style scoped>
.pt-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgb(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.pt-popup {
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  max-width: 520px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}
.pt-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-popup-header h2 {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-popup-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: var(--portal-text-md);
  cursor: pointer;
}
.pt-popup-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem;
}
.pt-news-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}
.pt-news-item:last-child {
  border-bottom: none;
}
.pt-news-badge {
  display: inline-block;
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-sm);
  margin-bottom: 0.4rem;
}
.pt-news-badge--announcement {
  background: rgb(var(--accent-rgb), 0.2);
  color: var(--accent);
}
.pt-news-badge--additions {
  background: rgb(var(--portal-color-success-rgb), 0.2);
  color: var(--portal-color-success);
}
.pt-news-badge--maintenance {
  background: rgb(234, 179, 8, 0.2);
  color: #eab308;
}
.pt-news-badge--event {
  background: rgb(var(--portal-color-premium-rgb), 0.2);
  color: var(--portal-color-premium);
}
.pt-news-badge--other {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}
.pt-news-title {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}
.pt-news-content {
  font-size: var(--portal-text-sm);
  color: var(--text-secondary);
  margin-top: 0.25rem;
  line-height: var(--portal-lh-normal);
}
.pt-news-date {
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
}
.pt-news-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem 0;
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  text-align: right;
}
.pt-popup-btn {
  padding: 0.5rem 1.5rem;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent);
  color: var(--portal-text-primary);
  font-weight: var(--portal-font-medium);
  cursor: pointer;
}
</style>
