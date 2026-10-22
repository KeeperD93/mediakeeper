<template>
  <div>
    <div class="excl-add">
      <select v-model="exclMode" class="excl-sel mk-select-chevron">
        <option :value="STATS_EXCLUSION_MODE.EXACT">{{ $t('stats.exact') }}</option>
        <option :value="STATS_EXCLUSION_MODE.CONTAINS">{{ $t('stats.contains') }}</option>
      </select>
      <input
        v-model="exclValue"
        class="excl-input"
        :placeholder="$t('stats.titlePlaceholder')"
        @keydown.enter="addExclusion"
      />
      <MkButton variant="icon" icon="plus" :aria-label="$t('common.add')" @click="addExclusion" />
    </div>
    <div v-if="exclusionsFailed && !exclusions.length" class="excl-empty">
      {{ $t('stats.exclusionsLoadError') }}
      <MkButton variant="link" size="sm" class="mk-touch-mobile" @click="loadExclusions">
        {{ $t('stats.retry') }}
      </MkButton>
    </div>
    <div v-else-if="!exclusions.length" class="excl-empty">{{ $t('stats.noExclusions') }}</div>
    <div v-for="(exc, i) in exclusions" :key="i" class="excl-item">
      <span class="excl-badge">
        {{ exc.mode === STATS_EXCLUSION_MODE.EXACT ? $t('stats.exact') : $t('stats.contains') }}
      </span>
      <span class="excl-val">{{ exc.value }}</span>
      <MkButton
        variant="icon"
        icon="x"
        size="sm"
        :aria-label="$t('common.remove')"
        @click="removeExclusion(i)"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import MkButton from '@/components/common/MkButton.vue'
import { useStatsExclusions } from '@/composables/useStatsExclusions'
import { STATS_EXCLUSION_MODE } from '@/constants/stats'

const {
  exclusions,
  exclusionsFailed,
  exclMode,
  exclValue,
  loadExclusions,
  addExclusion,
  removeExclusion,
} = useStatsExclusions()

onMounted(loadExclusions)
</script>

<style scoped>
.excl-add {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
/* Background and border of the admin reference menus (Notifications). */
.excl-sel {
  height: 32px;
  /* Fits its longest option, 90px at least: no font cuts a label. */
  width: auto;
  min-width: 90px;
  padding-block: 0;
  padding-left: var(--space-3);
  border: var(--border-width) solid var(--border);
  border-radius: var(--radius-btn);
  background-color: var(--bg-tertiary);
  font-size: var(--text-2xs);
  font-family: inherit;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  box-sizing: border-box;
}
.excl-sel option {
  background: var(--mk-chrome-bg);
  color: var(--text-primary);
}
.excl-input {
  flex: 1;
  min-width: 0;
  background: var(--bg-tertiary);
  border: var(--border-width) solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2-5);
  font-size: var(--text-2xs);
  color: var(--text-primary);
  outline: none;
}
.excl-input:focus {
  border-color: var(--accent-500);
}
.excl-sel:focus-visible,
.excl-input:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* iOS zooms into a field under 16px it focuses: 16px there only. */
@supports (-webkit-touch-callout: none) {
  .excl-sel,
  .excl-input {
    font-size: var(--text-md);
  }
}
.excl-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  padding: var(--space-1) 0;
}
.excl-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}
.excl-badge {
  /* 0.58rem / 4px sit below the smallest text + radius tokens
     (--text-3xs 0.62rem, --radius-sm floor); deliberately fixed for this
     micro mode-badge, kept raw per the rule of 3 — not an oversight. */
  font-size: 0.58rem;
  padding: var(--space-half) var(--space-2);
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-muted);
  flex-shrink: 0;
}
.excl-val {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* Touch targets ≥ 44px on mobile for the exclusion controls. */
@media (max-width: 767px) {
  .excl-sel,
  .excl-input {
    min-height: var(--touch-target);
  }
}
@media (hover: hover) {
  .excl-item:hover {
    background: var(--surface-1);
  }
}
</style>
