<template>
  <section class="pt-debug-card">
    <h3 class="pt-debug-title">{{ $t('portal.admin.debug.zoneSection') }}</h3>
    <p class="pt-debug-sub">{{ $t('portal.admin.debug.zoneHint') }}</p>
    <div class="pt-debug-row">
      <button type="button" class="pt-debug-btn" :disabled="busy" @click="simulate">
        {{
          simulating
            ? $t('portal.admin.debug.zoneSimulating')
            : $t('portal.admin.debug.zoneSimulate')
        }}
      </button>
      <button
        type="button"
        class="pt-debug-btn pt-debug-btn--danger"
        :disabled="busy || !summary?.removed_total"
        @click="apply"
      >
        {{ applying ? $t('portal.admin.debug.zoneApplying') : $t('portal.admin.debug.zoneApply') }}
      </button>
    </div>

    <ul v-if="summary" class="pt-debug-recheck-summary pt-debug-facts">
      <li>{{ $t('portal.admin.debug.zoneZone', { zone: summary.timezone, date: savedAt }) }}</li>
      <li v-if="!summary.removed_total">{{ $t('portal.admin.debug.zoneNothing') }}</li>
      <template v-else>
        <li>
          {{
            $t('portal.admin.debug.zoneTotals', {
              removed: summary.removed_total,
              players: summary.players_affected,
              total: summary.players,
              xp: summary.xp_removed,
            })
          }}
        </li>
        <li>
          {{
            $t('portal.admin.debug.zoneLevels', {
              players: summary.players_losing_level,
              max: summary.max_level_loss,
            })
          }}
        </li>
        <li>{{ $t('portal.admin.debug.zoneDecorations', { n: summary.decorations_removed }) }}</li>
        <li>{{ $t('portal.admin.debug.zoneImported', { n: summary.removed_imported }) }}</li>
      </template>
      <li>{{ $t('portal.admin.debug.zoneCompetitor', summary.competitor_months) }}</li>
      <li>{{ $t('portal.admin.debug.zoneKing', kingMonths) }}</li>
      <li>{{ $t('portal.admin.debug.zoneKept', kept) }}</li>
      <li v-if="summary.players_failed" class="pt-debug-warn">
        {{ $t('portal.admin.debug.zoneFailed', { n: summary.players_failed }) }}
      </li>
    </ul>

    <div v-if="summary?.removals.length" class="pt-debug-ach-list">
      <div v-for="row in summary.removals" :key="row.achievement_id" class="pt-debug-ach-row">
        <div class="pt-debug-ach-meta">
          <span class="pt-debug-ach-name">{{ $t(row.name_key) }}</span>
          <span class="pt-debug-ach-tag">
            {{ $t('portal.admin.debug.zoneRemoval', { direct: row.direct, cascade: row.cascade }) }}
          </span>
        </div>
      </div>
    </div>

    <ul v-if="applied" class="pt-debug-recheck-summary pt-debug-facts">
      <li>
        {{
          $t('portal.admin.debug.zoneApplied', {
            removed: applied.applied.removed,
            players: applied.applied.players,
            xp: applied.applied.xp_removed,
          })
        }}
      </li>
      <li v-if="applied.backup">
        {{ $t('portal.admin.debug.zoneBackup', { name: applied.backup }) }}
      </li>
      <li v-if="applied.applied.failed" class="pt-debug-warn">
        {{ $t('portal.admin.debug.zoneAppliedFailed', { n: applied.applied.failed }) }}
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { resolveScopedError } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { usePortalAdminDebug } from '@/composables/portal/usePortalAdminDebug'
import { TOAST_TYPE } from '@/constants/toast'
import { localizedDateTime } from '@/utils/datetime'

// Trophies and XP of players changed: the parent reloads its user list.
const emit = defineEmits(['changed'])

const { showToast } = useToast()
const { t } = useI18n()
const mkConfirm = useConfirm()
const debugApi = usePortalAdminDebug()

const summary = ref(null)
const applied = ref(null)
const simulating = ref(false)
const applying = ref(false)
const busy = computed(() => simulating.value || applying.value)

const savedAt = computed(() =>
  localizedDateTime(new Date(summary.value.zone_saved_at), {
    dateStyle: 'long',
    timeStyle: 'short',
  }),
)

const kingMonths = computed(() => ({
  trophy: t('portal.achievements.secretKing'),
  ...summary.value.king_months,
}))

const kept = computed(() => {
  const count = entries => entries.reduce((sum, entry) => sum + entry.count, 0)
  return {
    nowhere: count(summary.value.kept_nowhere),
    gifts: count(summary.value.kept_gifts),
  }
})

function showError(err) {
  console.error('[AdminDebugZoneCorrection]', err)
  showToast(
    resolveScopedError(
      'portal.admin.debug.zoneErrors',
      err?.message,
      'portal.admin.debug.errorGeneric',
    ),
    TOAST_TYPE.ERR,
  )
}

async function simulate() {
  simulating.value = true
  applied.value = null
  try {
    summary.value = await debugApi.simulateZoneCorrection()
  } catch (err) {
    summary.value = null
    showError(err)
  } finally {
    simulating.value = false
  }
}

async function apply() {
  const plan = summary.value
  if (!plan?.removed_total) return
  const ok = await mkConfirm({
    title: t('common.confirmTitle.remove'),
    message: t('portal.admin.debug.zoneConfirm', {
      removed: plan.removed_total,
      players: plan.players_affected,
      xp: plan.xp_removed,
    }),
    variant: 'danger',
  })
  if (!ok) return
  applying.value = true
  try {
    applied.value = await debugApi.applyZoneCorrection(plan.timezone, plan.plan)
    summary.value = null
    showToast(
      t('portal.admin.debug.zoneApplied', {
        removed: applied.value.applied.removed,
        players: applied.value.applied.players,
        xp: applied.value.applied.xp_removed,
      }),
      TOAST_TYPE.OK,
    )
    emit('changed')
  } catch (err) {
    showError(err)
  } finally {
    applying.value = false
  }
}
</script>

<!-- Styles live in assets/styles/portal/admin-debug.css, under the .pt-debug root of the page. -->
