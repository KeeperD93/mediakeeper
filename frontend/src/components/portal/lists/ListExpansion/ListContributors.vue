<template>
  <div class="ale-side-block">
    <div class="ale-col-head">
      <h4>{{ $t('portal.lists.contributors') }}</h4>
    </div>
    <ul v-if="contributors.length" class="ale-contributors">
      <li v-for="c in contributors" :key="c.user_id" class="ale-contrib">
        <MkAvatar
          :name="c.username || ''"
          :src="c.avatar_url || null"
          :size="26"
          :tier="c.tier || 'bronze'"
          class="ale-contrib-avatar"
        />
        <span class="ale-contrib-name">{{ c.username || `#${c.user_id}` }}</span>
        <span v-if="c.is_owner_row" class="ale-contrib-owner">
          {{ $t('portal.lists.ownerBadge') }}
        </span>
        <span
          v-if="c.muted"
          class="ale-contrib-muted"
          :title="$t('portal.lists.errors.contributor_muted')"
        >
          🔇
        </span>
        <button
          v-if="isOwner && !c.is_owner_row"
          class="ale-contrib-remove"
          type="button"
          :title="$t('common.delete')"
          @click="$emit('remove', c.user_id)"
        >
          ✕
        </button>
      </li>
    </ul>
    <p v-else class="ale-empty">—</p>
  </div>
</template>

<script setup>
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  contributors: { type: Array, required: true },
  isOwner: { type: Boolean, default: false },
})
defineEmits(['remove'])
</script>

<style scoped>
.ale-side-block {
  margin-bottom: 16px;
}
.ale-col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.ale-col-head h4 {
  font-size: var(--portal-text-3xs);
  font-weight: var(--portal-font-black);
  color: rgb(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
  margin: 0;
}
.ale-empty {
  color: rgb(255, 255, 255, 0.3);
  font-size: var(--portal-text-xs);
  padding: 12px 0;
  text-align: center;
}
.ale-contributors {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ale-contrib {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgb(255, 255, 255, 0.03);
  font-size: var(--portal-text-sm);
}
.ale-contrib-avatar {
  flex-shrink: 0;
}
.ale-contrib-name {
  flex: 1;
  color: var(--portal-text-body);
  font-weight: var(--portal-font-medium);
  min-width: 0;
}
.ale-contrib-muted {
  font-size: var(--portal-text-sm);
}
.ale-contrib-owner {
  font-size: var(--portal-text-4xs);
  font-weight: var(--portal-font-extrabold);
  padding: 2px 6px;
  border-radius: var(--portal-radius-xs);
  background: rgb(var(--accent-rgb), 0.18);
  color: var(--accent-300);
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-caps);
  flex-shrink: 0;
}
.ale-contrib-remove {
  background: transparent;
  border: none;
  color: rgb(255, 255, 255, 0.35);
  cursor: pointer;
  font-size: var(--portal-text-base);
  padding: 0 6px;
}
.ale-contrib-remove:hover {
  color: var(--portal-color-error-soft);
}
</style>
