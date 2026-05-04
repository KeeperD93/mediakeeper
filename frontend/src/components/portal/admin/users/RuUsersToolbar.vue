<template>
  <div class="ru-toolbar">
    <div class="ru-toolbar-search">
      <Search :size="16" class="ru-toolbar-search-icon" />
      <input
        type="search"
        :value="search"
        :placeholder="$t('requestsAdmin.users.search.placeholder')"
        class="ru-toolbar-input"
        @input="$emit('update:search', $event.target.value)"
      />
    </div>

    <div class="ru-toolbar-filters">
      <select
        :value="source"
        class="ru-toolbar-select"
        @change="$emit('update:source', $event.target.value)"
      >
        <option value="">{{ $t('requestsAdmin.users.filters.source.all') }}</option>
        <option value="emby">{{ $t('requestsAdmin.users.filters.source.emby') }}</option>
        <option value="local">{{ $t('requestsAdmin.users.filters.source.local') }}</option>
      </select>

      <select
        :value="role"
        class="ru-toolbar-select"
        @change="$emit('update:role', $event.target.value)"
      >
        <option value="">{{ $t('requestsAdmin.users.filters.role.all') }}</option>
        <option value="viewer">{{ $t('requestsAdmin.users.filters.role.viewer') }}</option>
        <option value="moderator">{{ $t('requestsAdmin.users.filters.role.moderator') }}</option>
        <option value="admin">{{ $t('requestsAdmin.users.filters.role.admin') }}</option>
      </select>

      <select
        :value="status"
        class="ru-toolbar-select"
        @change="$emit('update:status', $event.target.value)"
      >
        <option value="">{{ $t('requestsAdmin.users.filters.status.all') }}</option>
        <option value="active">{{ $t('requestsAdmin.users.filters.status.active') }}</option>
        <option value="inactive">{{ $t('requestsAdmin.users.filters.status.inactive') }}</option>
        <option value="expired">{{ $t('requestsAdmin.users.filters.status.expired') }}</option>
        <option value="never_logged_in">
          {{ $t('requestsAdmin.users.filters.status.never_logged_in') }}
        </option>
      </select>

      <select
        v-if="tagOptions.length"
        :value="tag"
        class="ru-toolbar-select"
        @change="$emit('update:tag', $event.target.value)"
      >
        <option value="">{{ $t('requestsAdmin.users.filters.tag.all') }}</option>
        <option v-for="t in tagOptions" :key="t" :value="t">#{{ t }}</option>
      </select>

      <label class="ru-toolbar-pill-input">
        <Clock :size="14" />
        <span>{{ $t('requestsAdmin.users.filters.expires_within_days') }}</span>
        <input
          type="number"
          min="1"
          max="365"
          :value="expiresWithin || ''"
          @input="onCustomExpire($event.target.value)"
        />
      </label>

      <button
        type="button"
        class="ru-pill"
        :class="{ 'ru-pill--active': includeDeleted }"
        @click="$emit('update:includeDeleted', !includeDeleted)"
      >
        <Trash2 :size="14" />
        <span>{{ $t('requestsAdmin.users.filters.show_deleted') }}</span>
      </button>
    </div>

    <div class="ru-toolbar-right">
      <span class="ru-toolbar-count">
        {{ $t('requestsAdmin.users.totalCount', { count: total }) }}
      </span>
      <div class="ru-toolbar-view" role="tablist">
        <button
          type="button"
          role="tab"
          class="ru-toolbar-view-btn"
          :class="{ 'is-active': viewMode === 'table' }"
          :aria-selected="viewMode === 'table'"
          :title="$t('requestsAdmin.users.view.table')"
          @click="$emit('update:viewMode', 'table')"
        >
          <List :size="16" />
        </button>
        <button
          type="button"
          role="tab"
          class="ru-toolbar-view-btn"
          :class="{ 'is-active': viewMode === 'cards' }"
          :aria-selected="viewMode === 'cards'"
          :title="$t('requestsAdmin.users.view.cards')"
          @click="$emit('update:viewMode', 'cards')"
        >
          <LayoutGrid :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Search, Clock, Trash2, List, LayoutGrid } from 'lucide-vue-next'

defineProps({
  search: { type: String, default: '' },
  source: { type: String, default: '' },
  role: { type: String, default: '' },
  status: { type: String, default: '' },
  tag: { type: String, default: '' },
  tagOptions: { type: Array, default: () => [] },
  expiresWithin: { default: null, validator: v => v === null || typeof v === 'number' },
  includeDeleted: { type: Boolean, default: false },
  viewMode: { type: String, default: 'table' },
  total: { type: Number, default: 0 },
})

const emit = defineEmits([
  'update:search',
  'update:source',
  'update:role',
  'update:status',
  'update:tag',
  'update:expiresWithin',
  'update:includeDeleted',
  'update:viewMode',
])

function onCustomExpire(raw) {
  const n = parseInt(raw, 10)
  emit('update:expiresWithin', Number.isFinite(n) && n > 0 ? n : null)
}
</script>
