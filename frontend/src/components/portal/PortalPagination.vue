<template>
  <nav v-if="total > 0" class="rqp" :aria-label="$t('common.pagination.label')">
    <div class="rqp-size">
      <label class="rqp-size-label" :for="sizeId">{{ $t('common.pagination.perPage') }}</label>
      <select
        :id="sizeId"
        class="rqp-size-select mk-select-chevron"
        :value="perPage"
        :disabled="disabled"
        @change="onSize"
      >
        <option v-for="s in sizes" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <div v-if="totalPages > 1" class="rqp-pages">
      <button
        type="button"
        class="rqp-btn"
        :disabled="disabled || page <= 1"
        :aria-label="$t('common.pagination.prevPage')"
        @click="emit('update:page', page - 1)"
      >
        <ChevronLeft :size="16" />
      </button>
      <button
        v-for="(p, i) in visiblePages"
        :key="`${p}-${i}`"
        type="button"
        class="rqp-btn"
        :class="{ 'rqp-btn--active': p === page, 'rqp-btn--dots': p === ELLIPSIS }"
        :disabled="disabled || p === ELLIPSIS"
        :aria-current="p === page ? 'page' : undefined"
        @click="p !== ELLIPSIS && emit('update:page', p)"
      >
        {{ p }}
      </button>
      <button
        type="button"
        class="rqp-btn"
        :disabled="disabled || page >= totalPages"
        :aria-label="$t('common.pagination.nextPage')"
        @click="emit('update:page', page + 1)"
      >
        <ChevronRight :size="16" />
      </button>
    </div>

    <span class="rqp-info">{{ rangeFrom }}–{{ rangeTo }} {{ $t('common.of') }} {{ total }}</span>
  </nav>
</template>

<script setup>
import { computed, useId } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { DEFAULT_PAGE_SIZE, PAGE_SIZES } from '@/constants/pagination'

const ELLIPSIS = '…'

const props = defineProps({
  page: { type: Number, default: 1 },
  perPage: { type: Number, default: DEFAULT_PAGE_SIZE },
  total: { type: Number, default: 0 },
  sizes: { type: Array, default: () => PAGE_SIZES },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:page', 'update:perPage'])

const sizeId = useId()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))
const rangeFrom = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.perPage + 1))
const rangeTo = computed(() => Math.min(props.page * props.perPage, props.total))

// Compact window: first, last, current ±1; collapsed gaps render as a dot.
const visiblePages = computed(() => {
  const last = totalPages.value
  const wanted = [1, last, props.page, props.page - 1, props.page + 1]
  const kept = [...new Set(wanted)].filter(p => p >= 1 && p <= last).sort((a, b) => a - b)
  const out = []
  let prev = 0
  for (const p of kept) {
    if (p - prev > 1) out.push(ELLIPSIS)
    out.push(p)
    prev = p
  }
  return out
})

function onSize(e) {
  emit('update:perPage', Number(e.target.value))
}
</script>

<style scoped>
.rqp {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.rqp-size {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rqp-size-label {
  font-size: var(--portal-text-xs);
  color: var(--portal-text-body-muted);
}
.rqp-size-select {
  min-height: 44px;
  /* padding-right is owned by .mk-select-chevron (28px) so the value clears
     the custom chevron; padding-left mirrors the chevron's right gap. */
  padding-block: 8px;
  padding-left: 12px;
  /* background-color (not the shorthand) so .mk-select-chevron's
     background-image survives — the caller owns surface + border only. */
  background-color: var(--portal-surface-3);
  border: 1px solid var(--portal-border-default);
  border-radius: var(--portal-radius-md);
  color: var(--portal-text-primary);
  font-family: inherit;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  cursor: pointer;
}
.rqp-size-select option {
  background: var(--portal-chrome-bg);
  color: var(--portal-text-primary);
}
.rqp-pages {
  display: flex;
  align-items: center;
  gap: 4px;
}
.rqp-btn {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border: 1px solid var(--portal-border-default);
  border-radius: var(--portal-radius-md);
  background: var(--portal-surface-3);
  color: var(--portal-text-body-muted);
  font-family: inherit;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  cursor: pointer;
  transition:
    background-color var(--portal-dur-fast),
    border-color var(--portal-dur-fast),
    color var(--portal-dur-fast);
}
.rqp-btn--active {
  background: linear-gradient(135deg, rgb(var(--accent-rgb), 0.22), rgb(var(--accent-rgb), 0.1));
  border-color: var(--accent-500);
  color: var(--portal-text-primary);
}
.rqp-btn--dots {
  border: none;
  background: none;
  cursor: default;
  color: var(--portal-text-body-muted);
}
.rqp-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.rqp-info {
  font-size: var(--portal-text-xs);
  color: var(--portal-text-body-muted);
}
@media (hover: hover) {
  .rqp-btn:not(:disabled, .rqp-btn--active, .rqp-btn--dots):hover {
    border-color: var(--portal-border-intense);
    color: var(--portal-text-primary);
  }
}
.rqp-size-select:focus-visible,
.rqp-btn:focus-visible {
  outline: 2px solid rgb(var(--accent-rgb), 0.4);
  outline-offset: 1px;
}
@media (min-width: 768px) {
  .rqp-btn {
    min-width: 36px;
    min-height: 36px;
  }
  .rqp-size-select {
    min-height: 36px;
  }
}
</style>
