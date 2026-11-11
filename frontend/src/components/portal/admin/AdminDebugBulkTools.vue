<template>
  <!-- Recheck all achievements -->
  <section class="pt-debug-card">
    <h3 class="pt-debug-title">{{ $t('portal.admin.debug.recheckSection') }}</h3>
    <p class="pt-debug-sub">{{ $t('portal.admin.debug.recheckHint') }}</p>
    <div class="pt-debug-row">
      <button
        type="button"
        class="pt-debug-btn pt-debug-btn--primary"
        :disabled="recheckLoading"
        @click="recheckAllAchievements"
      >
        {{
          recheckLoading
            ? $t('portal.admin.debug.recheckRunning')
            : $t('portal.admin.debug.recheckApply')
        }}
      </button>
    </div>
    <p v-if="recheckResult" class="pt-debug-recheck-summary">
      {{
        $t('portal.admin.debug.recheckResult', {
          users: recheckResult.users_processed,
          updated: recheckResult.users_with_new_unlocks,
          unlocks: recheckResult.total_new_unlocks,
        })
      }}
    </p>
  </section>

  <!-- Reset achievement for all -->
  <section class="pt-debug-card">
    <h3 class="pt-debug-title">{{ $t('portal.admin.debug.resetForAllSection') }}</h3>
    <p class="pt-debug-sub">{{ $t('portal.admin.debug.resetForAllHint') }}</p>
    <div class="pt-debug-row">
      <select v-model="resetAchievementId" class="pt-debug-select mk-select-chevron">
        <option value="" disabled>—</option>
        <option v-for="ach in achievements" :key="ach.id" :value="ach.id">
          {{ t(ach.name_key) }} · {{ ach.id }}
        </option>
      </select>
      <button
        type="button"
        class="pt-debug-btn pt-debug-btn--danger"
        :disabled="!resetAchievementId || resetLoading"
        @click="resetAchievementForAll"
      >
        {{
          resetLoading
            ? $t('portal.admin.debug.resetForAllRunning')
            : $t('portal.admin.debug.resetForAllApply')
        }}
      </button>
    </div>
    <p v-if="resetResult" class="pt-debug-recheck-summary">
      {{
        $t('portal.admin.debug.resetForAllResult', {
          ach: resetResult.achievement_id,
          ua: resetResult.user_achievements_removed,
          xp: resetResult.xp_ledger_removed,
          profiles: resetResult.profiles_rebuilt,
        })
      }}
    </p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { usePortalAdminDebug } from '@/composables/portal/usePortalAdminDebug'
import { TOAST_TYPE } from '@/constants/toast'

defineProps({
  achievements: { type: Array, required: true },
})
// The trophies and XP of players changed: the parent reloads its user list.
const emit = defineEmits(['changed'])

const { showToast } = useToast()
const { t } = useI18n()
const mkConfirm = useConfirm()
const debugApi = usePortalAdminDebug()

const recheckLoading = ref(false)
const recheckResult = ref(null)
const resetAchievementId = ref('')
const resetLoading = ref(false)
const resetResult = ref(null)

async function resetAchievementForAll() {
  if (!resetAchievementId.value) return
  const ok = await mkConfirm({
    title: t('common.confirmTitle.reset'),
    message: t('portal.admin.debug.resetForAllConfirm', { ach: resetAchievementId.value }),
    variant: 'danger',
  })
  if (!ok) return
  resetLoading.value = true
  try {
    const res = await debugApi.resetAchievementForAll(resetAchievementId.value)
    resetResult.value = res
    showToast(
      t('portal.admin.debug.resetForAllDone', {
        ach: res?.achievement_id,
        ua: res?.user_achievements_removed ?? 0,
      }),
      TOAST_TYPE.OK,
    )
    emit('changed')
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  } finally {
    resetLoading.value = false
  }
}

async function recheckAllAchievements() {
  recheckLoading.value = true
  try {
    const res = await debugApi.recheckAllAchievements()
    recheckResult.value = res
    showToast(
      t('portal.admin.debug.recheckDone', {
        unlocks: res?.total_new_unlocks ?? 0,
      }),
      TOAST_TYPE.OK,
    )
    emit('changed')
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  } finally {
    recheckLoading.value = false
  }
}
</script>

<!-- Styles live in assets/styles/portal/admin-debug.css, under the .pt-debug root of the page. -->
