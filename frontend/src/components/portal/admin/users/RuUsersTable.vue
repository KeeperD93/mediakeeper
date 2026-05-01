<template>
  <div class="ru-table-wrap">
    <table class="ru-table">
      <thead>
        <tr>
          <th class="ru-col-check">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              @change="$emit('toggle-all')"
            />
          </th>
          <th></th>
          <th class="ru-col--sort" @click="toggleSort('display_name')">
            {{ $t('requestsAdmin.users.col.name') }} <span class="ru-sort-arrow">{{ arrow('display_name') }}</span>
          </th>
          <th>{{ $t('requestsAdmin.users.col.source') }}</th>
          <th>{{ $t('requestsAdmin.users.col.role') }}</th>
          <th>{{ $t('requestsAdmin.users.col.status') }}</th>
          <th class="ru-col--sort" @click="toggleSort('access_end_date')">
            {{ $t('requestsAdmin.users.col.access_end') }} <span class="ru-sort-arrow">{{ arrow('access_end_date') }}</span>
          </th>
          <th class="ru-col--sort" @click="toggleSort('xp')">
            {{ $t('requestsAdmin.users.col.level') }} <span class="ru-sort-arrow">{{ arrow('xp') }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="u in items"
          :key="u.id"
          class="ru-row"
          :class="{
            'ru-row--deleted': u.deleted_at,
            'ru-row--selected': selectedIds.includes(u.id),
            'ru-row--active': activeId === u.id,
          }"
          @click="$emit('open', u.id)"
        >
          <td class="ru-col-check" @click.stop>
            <input type="checkbox" :checked="selectedIds.includes(u.id)" @change="$emit('toggle', u.id)" />
          </td>
          <td class="ru-col-avatar">
            <MkAvatar :src="u.avatar_url" :name="u.display_name || u.username" :size="32" />
          </td>
          <td>
            <div class="ru-name">
              <span>{{ u.display_name }}</span>
              <RuUserBadge v-if="u.deleted_at" variant="muted">
                {{ $t('requestsAdmin.users.labels.deletedShort') }}
              </RuUserBadge>
            </div>
            <div class="ru-username" :title="$t('requestsAdmin.users.labels.usernameHint')">@{{ u.username }}<span v-if="u.email"> · {{ u.email }}</span></div>
          </td>
          <td>
            <div class="ru-source-cell">
              <RuUserBadge :variant="u.source === 'emby' ? 'info' : 'success'">
                {{ u.source === 'emby' ? 'Emby' : $t('requestsAdmin.users.filters.source.local') }}
              </RuUserBadge>
              <RuUserBadge v-if="u.source === 'emby' && u.emby_is_disabled" variant="danger">
                {{ $t('requestsAdmin.users.labels.embyDisabled') }}
              </RuUserBadge>
            </div>
          </td>
          <td>
            <RuUserBadge :variant="roleVariant(u.role)">
              {{ $t(`requestsAdmin.users.filters.role.${u.role}`) }}
            </RuUserBadge>
          </td>
          <td><RuUserStatusCell :user="u" /></td>
          <td><RuExpiryCell :user="u" /></td>
          <td class="ru-col-level">Lv {{ u.level }} · {{ u.xp }} XP</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MkAvatar from '@/components/common/MkAvatar.vue'
import RuUserBadge from './RuUserBadge.vue'
import RuUserStatusCell from './RuUserStatusCell.vue'
import RuExpiryCell from './RuExpiryCell.vue'

const props = defineProps({
  items: { type: Array, required: true },
  selectedIds: { type: Array, required: true },
  activeId: { type: Number, default: null },
  sort: { type: String, default: 'display_name' },
  order: { type: String, default: 'asc' },
})

const emit = defineEmits(['toggle', 'toggle-all', 'open', 'sort'])

function toggleSort(key) {
  const nextOrder = props.sort === key && props.order === 'asc' ? 'desc' : 'asc'
  emit('sort', { sort: key, order: nextOrder })
}

function arrow(key) {
  if (props.sort !== key) return '↕'
  return props.order === 'asc' ? '↑' : '↓'
}

const allSelected = computed(
  () => props.items.length > 0 && props.items.every((u) => props.selectedIds.includes(u.id)),
)
const someSelected = computed(
  () => props.items.some((u) => props.selectedIds.includes(u.id)),
)

function roleVariant(role) {
  if (role === 'admin') return 'premium'
  if (role === 'moderator') return 'info'
  return 'neutral'
}
</script>
