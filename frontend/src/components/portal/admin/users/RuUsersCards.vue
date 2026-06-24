<template>
  <ul class="ru-cards">
    <li
      v-for="u in items"
      :key="u.id"
      class="ru-card"
      :class="{
        'ru-card--deleted': u.deleted_at,
        'ru-card--selected': selectedIds.includes(u.id),
        'ru-card--active': activeId === u.id,
      }"
      @click="$emit('open', u.id)"
    >
      <input
        type="checkbox"
        class="ru-card-check"
        :checked="selectedIds.includes(u.id)"
        @click.stop
        @change="$emit('toggle', u.id)"
      />
      <div class="ru-card-head">
        <MkAvatar
          :src="u.avatar_url"
          :name="u.display_name || u.username"
          :size="56"
          :tier="u.tier || 'bronze'"
        />
        <div>
          <div class="ru-card-name">{{ u.display_name }}</div>
          <div class="ru-card-username">@{{ u.username }}</div>
        </div>
      </div>
      <div class="ru-card-meta">
        <RuUserBadge :variant="u.source === USER_SOURCE.EMBY ? 'info' : 'success'">
          {{
            u.source === USER_SOURCE.EMBY ? 'Emby' : $t('requestsAdmin.users.filters.source.local')
          }}
        </RuUserBadge>
        <RuUserBadge v-if="u.emby_is_disabled" variant="danger">
          {{ $t('requestsAdmin.users.labels.embyDisabled') }}
        </RuUserBadge>
        <RuUserBadge :variant="roleVariant(u.role)">
          {{ $t(`requestsAdmin.users.filters.role.${u.role}`) }}
        </RuUserBadge>
        <RuUserBadge v-if="u.deleted_at" variant="muted">
          {{ $t('requestsAdmin.users.labels.deletedShort') }}
        </RuUserBadge>
      </div>
      <div class="ru-card-foot">
        <RuUserStatusCell :user="u" />
        <span class="ru-card-level">Lv {{ u.level }} · {{ u.xp }} XP</span>
      </div>
      <RuExpiryCell :user="u" class="ru-card-expiry" />
    </li>
  </ul>
</template>

<script setup>
import MkAvatar from '@/components/common/MkAvatar.vue'
import RuUserBadge from './RuUserBadge.vue'
import RuUserStatusCell from './RuUserStatusCell.vue'
import RuExpiryCell from './RuExpiryCell.vue'
import { USER_ROLE, USER_SOURCE } from '@/constants/portalAdminUsers'

defineProps({
  items: { type: Array, required: true },
  selectedIds: { type: Array, required: true },
  activeId: { type: Number, default: null },
})

defineEmits(['toggle', 'open'])

function roleVariant(role) {
  if (role === USER_ROLE.ADMIN) return 'premium'
  if (role === USER_ROLE.MODERATOR) return 'info'
  return 'neutral'
}
</script>
