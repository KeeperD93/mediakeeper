<template>
  <div class="arr-filter-menus">
    <select
      class="arr-sort mk-select-chevron"
      :value="status"
      :aria-label="$t('portal.admin.req.statusFilterLabel')"
      @change="emit('update:status', $event.target.value)"
    >
      <option v-for="st in STATUS_FILTERS" :key="st.value" :value="st.value">
        {{ $t(st.label) }}
      </option>
    </select>
    <select
      class="arr-sort mk-select-chevron"
      :value="mediaType"
      :aria-label="$t('portal.admin.req.typeFilterLabel')"
      @change="emit('update:mediaType', $event.target.value)"
    >
      <option v-for="tp in TYPE_FILTERS" :key="tp.value || 'all'" :value="tp.value">
        {{ $t(tp.menuLabel || tp.label) }}
      </option>
    </select>
  </div>
  <div class="arr-pills">
    <button
      v-for="st in STATUS_FILTERS"
      :key="st.value"
      type="button"
      class="arr-pill arr-pill--filter"
      :class="{ 'arr-pill--active': status === st.value }"
      :aria-pressed="status === st.value ? 'true' : 'false'"
      @click="emit('update:status', st.value)"
    >
      {{ $t(st.label) }}
    </button>
    <span class="arr-pills-sep" aria-hidden="true" />
    <button
      v-for="tp in TYPE_FILTERS"
      :key="tp.value || 'all'"
      type="button"
      class="arr-pill arr-pill--filter"
      :class="{ 'arr-pill--active': mediaType === tp.value }"
      :aria-pressed="mediaType === tp.value ? 'true' : 'false'"
      :aria-label="tp.menuLabel ? $t(tp.menuLabel) : undefined"
      @click="emit('update:mediaType', tp.value)"
    >
      {{ $t(tp.label) }}
    </button>
    <template v-if="!status">
      <span class="arr-pills-sep" aria-hidden="true" />
      <div class="arr-switch-line">
        <label class="arr-pill arr-switch">
          {{ $t('portal.admin.req.hideAvailable') }}
          <MkToggle
            :model-value="hideAvailable"
            :aria-label="$t('portal.admin.req.hideAvailable')"
            @update:model-value="emit('update:hideAvailable', $event)"
          />
        </label>
      </div>
    </template>
  </div>
</template>

<script setup>
// Status and type filters of the admin queue, plus the "hide available"
// switch of the all-statuses view. Phones get two menus, tablets up the
// pills: both stay in the DOM and the stylesheet shows one or the other.
import MkToggle from '@/components/common/MkToggle.vue'
import { REQUEST_STATUS } from '@/constants/requests'
import { MEDIA_TYPE } from '@/constants/media'

defineProps({
  status: { type: String, default: '' },
  mediaType: { type: String, default: '' },
  hideAvailable: { type: Boolean, default: false },
})
const emit = defineEmits(['update:status', 'update:mediaType', 'update:hideAvailable'])

const STATUS_FILTERS = [
  { value: '', label: 'portal.requests.allStatus' },
  { value: REQUEST_STATUS.PENDING, label: 'portal.requests.pending' },
  { value: REQUEST_STATUS.APPROVED, label: 'portal.requests.approved' },
  { value: REQUEST_STATUS.AVAILABLE, label: 'portal.requests.available' },
  { value: REQUEST_STATUS.REJECTED, label: 'portal.requests.rejected' },
]

// A closed menu shows only its value: "All" alone would not say what it covers.
const TYPE_FILTERS = [
  { value: '', label: 'portal.admin.req.typeAll', menuLabel: 'portal.admin.req.allTypes' },
  { value: MEDIA_TYPE.MOVIE, label: 'portal.admin.req.typeMovies' },
  { value: MEDIA_TYPE.TV, label: 'portal.admin.req.typeSeries' },
]
</script>
