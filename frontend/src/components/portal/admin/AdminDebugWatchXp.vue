<template>
  <section class="pt-debug-card">
    <h3 class="pt-debug-title">{{ $t('portal.admin.debug.watchXpSection') }}</h3>
    <p class="pt-debug-sub">{{ $t('portal.admin.debug.watchXpHint') }}</p>
    <div class="pt-debug-row">
      <button type="button" class="pt-debug-btn" :disabled="busy" @click="simulate">
        {{
          simulating
            ? $t('portal.admin.debug.watchXpSimulating')
            : $t('portal.admin.debug.watchXpSimulate')
        }}
      </button>
      <button
        type="button"
        class="pt-debug-btn pt-debug-btn--danger"
        :disabled="busy || !summary?.players_changed"
        @click="apply"
      >
        {{
          applying
            ? $t('portal.admin.debug.watchXpApplying')
            : $t('portal.admin.debug.watchXpApply')
        }}
      </button>
    </div>

    <ul v-if="summary" class="pt-debug-recheck-summary pt-debug-facts">
      <li v-if="!summary.players_changed">{{ $t('portal.admin.debug.watchXpNothing') }}</li>
      <template v-else>
        <li>
          {{
            $t('portal.admin.debug.watchXpPlayers', {
              players: summary.players_changed,
              total: summary.players,
              before: summary.watch_xp_before,
              after: summary.watch_xp_after,
            })
          }}
        </li>
        <li>
          {{
            $t('portal.admin.debug.watchXpLevels', {
              up: summary.levels_up,
              down: summary.levels_down,
              max: summary.max_level_loss,
            })
          }}
        </li>
        <li>{{ $t('portal.admin.debug.watchXpLost', facts.lost) }}</li>
      </template>
      <li>{{ $t('portal.admin.debug.watchXpSkipped', facts.skipped) }}</li>
      <li>{{ $t('portal.admin.debug.watchXpNamesakes', { namesake: summary.namesakes }) }}</li>
      <li v-if="facts.events">{{ $t('portal.admin.debug.watchXpEvents', facts.events) }}</li>
      <li>
        {{ $t('portal.admin.debug.watchXpMonths', { n: summary.leaders_changed.length }) }}
      </li>
    </ul>

    <div v-if="summary?.rows.length" class="pt-debug-ach-list">
      <div v-for="row in summary.rows" :key="row.user_id" class="pt-debug-ach-row">
        <div class="pt-debug-ach-meta">
          <span class="pt-debug-ach-name">{{ row.name }}</span>
          <span class="pt-debug-ach-tag">
            {{
              $t('portal.admin.debug.watchXpRow', {
                xp: row.xp,
                xpAfter: row.xp_after,
                level: row.level,
                levelAfter: row.level_after,
              })
            }}
          </span>
        </div>
      </div>
    </div>

    <ul v-if="applied" class="pt-debug-recheck-summary pt-debug-facts">
      <li>{{ appliedText }}</li>
    </ul>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { usePortalAdminDebug } from '@/composables/portal/usePortalAdminDebug'
import { resolveScopedError } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { WATCH_XP_LOST, WATCH_XP_SKIP } from '@/constants/watchXpRecalc'

// The XP of players changed: the parent reloads its user list.
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
const appliedText = computed(() => applied.value && resultText(applied.value))

function resultText(result) {
  return result.backup
    ? t('portal.admin.debug.watchXpApplied', {
        players: result.applied.players,
        name: result.backup,
      })
    : t('portal.admin.debug.watchXpNothing')
}

function eventList(events) {
  const shown = events.map(ev =>
    t('portal.admin.debug.watchXpEvent', { name: ev.name, titles: ev.titles, xp: ev.bonus_xp }),
  )
  return shown.length ? shown.join(', ') : '0'
}

const facts = computed(() => {
  const { lost, skipped, events } = summary.value
  const count = (counts, ...codes) => codes.reduce((sum, code) => sum + (counts[code] || 0), 0)
  const covering = events.filter(ev => ev.titles)
  return {
    lost: {
      lost: count(lost, ...Object.values(WATCH_XP_LOST)),
      // Titles watched to the end, none of which pays, are counted with the unfinished ones.
      noEnd: count(lost, WATCH_XP_LOST.NO_END, WATCH_XP_LOST.NOT_DUE),
      stats: count(lost, WATCH_XP_LOST.NO_STATS),
    },
    skipped: {
      // Someone erased at their request has no account any more.
      noAccount: count(skipped, WATCH_XP_SKIP.NO_ACCOUNT, WATCH_XP_SKIP.ERASED),
      notEarning: count(skipped, WATCH_XP_SKIP.NOT_EARNING),
      excluded: count(skipped, WATCH_XP_SKIP.EXCLUDED),
      cooldown: count(skipped, WATCH_XP_SKIP.COOLDOWN),
      parallel: count(skipped, WATCH_XP_SKIP.PARALLEL),
      beforeLedger: count(skipped, WATCH_XP_SKIP.BEFORE_LEDGER),
    },
    events: covering.length && {
      events: eventList(covering.filter(ev => ev.enabled)),
      ignored: eventList(covering.filter(ev => !ev.enabled)),
    },
  }
})

async function simulate() {
  simulating.value = true
  applied.value = null
  try {
    summary.value = await debugApi.simulateWatchXp()
  } catch (err) {
    summary.value = null
    console.error('[AdminDebugWatchXp]', err)
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  } finally {
    simulating.value = false
  }
}

async function apply() {
  const plan = summary.value
  if (!plan?.players_changed) return
  const ok = await mkConfirm({
    title: t('common.confirmTitle.action'),
    message: t('portal.admin.debug.watchXpConfirm', { players: plan.players_changed }),
    variant: 'danger',
  })
  if (!ok) return
  applying.value = true
  try {
    applied.value = await debugApi.applyWatchXp(plan.as_of, plan.plan)
    summary.value = null
    showToast(resultText(applied.value), TOAST_TYPE.OK)
    emit('changed')
  } catch (err) {
    console.error('[AdminDebugWatchXp]', err)
    showToast(
      resolveScopedError(
        'portal.admin.debug.watchXpErrors',
        err?.message,
        'portal.admin.debug.errorGeneric',
      ),
      TOAST_TYPE.ERR,
    )
  } finally {
    applying.value = false
  }
}
</script>

<!-- Styles live in assets/styles/portal/admin-debug.css, under the .pt-debug root of the page. -->
