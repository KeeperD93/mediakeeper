<template>
  <div class="pt-debug">
    <p class="pt-debug-hint">{{ $t('portal.admin.debug.hint') }}</p>

    <!-- ─── Recheck all achievements ───────────────────────────── -->
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
          {{ recheckLoading
            ? $t('portal.admin.debug.recheckRunning')
            : $t('portal.admin.debug.recheckApply') }}
        </button>
      </div>
      <p v-if="recheckResult" class="pt-debug-recheck-summary">
        {{ $t('portal.admin.debug.recheckResult', {
          users: recheckResult.users_processed,
          updated: recheckResult.users_with_new_unlocks,
          unlocks: recheckResult.total_new_unlocks,
        }) }}
      </p>
    </section>

    <!-- ─── Reset achievement for all ───────────────────────────── -->
    <section class="pt-debug-card">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.resetForAllSection') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.resetForAllHint') }}</p>
      <div class="pt-debug-row">
        <select v-model="resetAchievementId" class="pt-debug-select">
          <option value="" disabled>—</option>
          <option v-for="ach in achievements" :key="ach.id" :value="ach.id">
            {{ ach.secret ? '???' : t(ach.name_key) }} · {{ ach.id }}
          </option>
        </select>
        <button
          type="button"
          class="pt-debug-btn pt-debug-btn--danger"
          :disabled="!resetAchievementId || resetLoading"
          @click="resetAchievementForAll"
        >
          {{ resetLoading
            ? $t('portal.admin.debug.resetForAllRunning')
            : $t('portal.admin.debug.resetForAllApply') }}
        </button>
      </div>
      <p v-if="resetResult" class="pt-debug-recheck-summary">
        {{ $t('portal.admin.debug.resetForAllResult', {
          ach: resetResult.achievement_id,
          ua: resetResult.user_achievements_removed,
          xp: resetResult.xp_ledger_removed,
          profiles: resetResult.profiles_rebuilt,
        }) }}
      </p>
    </section>

    <!-- ─── User picker ─────────────────────────────────────────── -->
    <section class="pt-debug-card">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.userPicker') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.userPickerHint') }}</p>
      <select v-model.number="selectedUserId" class="pt-debug-select">
        <option :value="null" disabled>—</option>
        <option v-for="u in users" :key="u.user_id" :value="u.user_id">
          {{ u.display_name }}<span v-if="u.role === 'admin'"> · admin</span>
          · L{{ u.level }} · {{ u.xp.toLocaleString() }} XP
        </option>
      </select>
      <p v-if="!selectedUserId" class="pt-debug-warn">
        {{ $t('portal.admin.debug.noUserSelected') }}
      </p>
    </section>

    <!-- ─── XP grant ────────────────────────────────────────────── -->
    <section class="pt-debug-card" :class="{ 'pt-debug-card--disabled': !selectedUserId }">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.xpSection') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.xpHint') }}</p>
      <div class="pt-debug-row">
        <input
          v-model.number="xpAmount"
          type="number"
          class="pt-debug-input"
          :placeholder="$t('portal.admin.debug.xpAmount')"
          :disabled="!selectedUserId"
        />
        <input
          v-model="xpNote"
          type="text"
          class="pt-debug-input"
          :placeholder="$t('portal.admin.debug.xpNote')"
          maxlength="120"
          :disabled="!selectedUserId"
        />
        <button
          type="button"
          class="pt-debug-btn pt-debug-btn--primary"
          :disabled="!selectedUserId || !xpAmount"
          @click="applyXp"
        >{{ $t('portal.admin.debug.xpApply') }}</button>
      </div>
    </section>

    <!-- ─── Level ────────────────────────────────────────────────── -->
    <section class="pt-debug-card" :class="{ 'pt-debug-card--disabled': !selectedUserId }">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.levelSection') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.levelHint') }}</p>
      <div class="pt-debug-row">
        <input
          v-model.number="levelTarget"
          type="number"
          class="pt-debug-input"
          min="0"
          max="50"
          :placeholder="$t('portal.admin.debug.levelTarget')"
          :disabled="!selectedUserId"
        />
        <button
          type="button"
          class="pt-debug-btn pt-debug-btn--primary"
          :disabled="!selectedUserId || levelTarget == null"
          @click="applyLevel"
        >{{ $t('portal.admin.debug.levelApply') }}</button>
      </div>
    </section>

    <!-- ─── Achievements ─────────────────────────────────────────── -->
    <section class="pt-debug-card" :class="{ 'pt-debug-card--disabled': !selectedUserId }">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.achievementSection') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.achievementHint') }}</p>

      <div class="pt-debug-ach-filter">
        <input
          v-model="achQuery"
          type="text"
          class="pt-debug-input"
          :placeholder="$t('portal.admin.debug.achievementSearch')"
        />
        <select v-model="achCategory" class="pt-debug-select pt-debug-select--inline">
          <option value="">{{ $t('portal.admin.debug.categoryAll') }}</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>

      <div class="pt-debug-ach-list">
        <div
          v-for="ach in filteredAchievements"
          :key="ach.id"
          class="pt-debug-ach-row"
        >
          <div class="pt-debug-ach-meta">
            <span class="pt-debug-ach-name">
              {{ ach.secret ? '???' : $t(ach.name_key) }}
            </span>
            <span class="pt-debug-ach-tag">{{ ach.category }} · T{{ ach.tier }}</span>
          </div>
          <div class="pt-debug-ach-actions">
            <button
              type="button"
              class="pt-debug-btn pt-debug-btn--small"
              :disabled="!selectedUserId"
              @click="unlockAch(ach)"
            >{{ $t('portal.admin.debug.achievementUnlock') }}</button>
            <button
              type="button"
              class="pt-debug-btn pt-debug-btn--small pt-debug-btn--danger"
              :disabled="!selectedUserId"
              @click="lockAch(ach)"
            >{{ $t('portal.admin.debug.achievementLock') }}</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'

import '@/assets/styles/portal/admin-debug.css'

const { apiGet, apiPost } = useApi()
const { showToast } = useToast()
const { t } = useI18n()

const users = ref([])
const achievements = ref([])
const selectedUserId = ref(null)
const xpAmount = ref(null)
const xpNote = ref('')
const levelTarget = ref(null)
const achQuery = ref('')
const achCategory = ref('')
const recheckLoading = ref(false)
const recheckResult = ref(null)
const resetAchievementId = ref('')
const resetLoading = ref(false)
const resetResult = ref(null)

const categories = computed(() => {
  const set = new Set(achievements.value.map((a) => a.category).filter(Boolean))
  return Array.from(set).sort()
})

const filteredAchievements = computed(() => {
  const q = achQuery.value.trim().toLowerCase()
  return achievements.value.filter((a) => {
    if (achCategory.value && a.category !== achCategory.value) return false
    if (!q) return true
    const name = a.secret ? '???' : t(a.name_key).toLowerCase()
    return name.includes(q) || a.id.toLowerCase().includes(q)
  })
})

async function loadUsers() {
  const res = await apiGet('/api/portal/admin/debug/users')
  users.value = res?.items || []
}

async function loadAchievements() {
  const res = await apiGet('/api/portal/admin/debug/achievements')
  achievements.value = res?.items || []
}

function syncSelectedFromResponse(body) {
  const user = users.value.find((u) => u.user_id === selectedUserId.value)
  if (user && body?.xp != null) {
    user.xp = body.xp
    user.level = body.level
  }
}

async function applyXp() {
  if (!selectedUserId.value || !xpAmount.value) return
  try {
    const body = await apiPost('/api/portal/admin/debug/grant-xp', {
      user_id: selectedUserId.value,
      amount: xpAmount.value,
      note: xpNote.value || null,
    })
    syncSelectedFromResponse(body)
    showToast(
      t('portal.admin.debug.xpApplied', { amount: xpAmount.value, total: body?.xp ?? 0 }),
      TOAST_TYPE.OK,
    )
    xpAmount.value = null
    xpNote.value = ''
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

async function applyLevel() {
  if (!selectedUserId.value || levelTarget.value == null) return
  try {
    const body = await apiPost('/api/portal/admin/debug/set-level', {
      user_id: selectedUserId.value,
      level: levelTarget.value,
    })
    syncSelectedFromResponse(body)
    showToast(
      t('portal.admin.debug.levelApplied', { level: body?.level ?? levelTarget.value }),
      TOAST_TYPE.OK,
    )
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

async function unlockAch(ach) {
  if (!selectedUserId.value) return
  try {
    await apiPost('/api/portal/admin/debug/unlock-achievement', {
      user_id: selectedUserId.value,
      achievement_id: ach.id,
    })
    showToast(t('portal.admin.debug.achievementUnlocked'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

async function resetAchievementForAll() {
  if (!resetAchievementId.value) return
  if (!confirm(t('portal.admin.debug.resetForAllConfirm', { ach: resetAchievementId.value }))) return
  resetLoading.value = true
  try {
    const res = await apiPost('/api/portal/admin/debug/reset-achievement-for-all', {
      achievement_id: resetAchievementId.value,
    })
    resetResult.value = res
    showToast(
      t('portal.admin.debug.resetForAllDone', {
        ach: res?.achievement_id,
        ua: res?.user_achievements_removed ?? 0,
      }),
      TOAST_TYPE.OK,
    )
    await loadUsers()
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  } finally {
    resetLoading.value = false
  }
}

async function recheckAllAchievements() {
  recheckLoading.value = true
  try {
    const res = await apiPost('/api/portal/admin/debug/recheck-all-achievements', {})
    recheckResult.value = res
    showToast(
      t('portal.admin.debug.recheckDone', {
        unlocks: res?.total_new_unlocks ?? 0,
      }),
      TOAST_TYPE.OK,
    )
    await loadUsers()
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  } finally {
    recheckLoading.value = false
  }
}

async function lockAch(ach) {
  if (!selectedUserId.value) return
  try {
    await apiPost('/api/portal/admin/debug/lock-achievement', {
      user_id: selectedUserId.value,
      achievement_id: ach.id,
    })
    showToast(t('portal.admin.debug.achievementLocked'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

onMounted(() => {
  loadUsers()
  loadAchievements()
})
</script>

<!-- Styles externalised to assets/styles/portal/admin-debug.css; the
     extracted CSS keeps a unique class prefix to simulate Vue scoped CSS. -->
