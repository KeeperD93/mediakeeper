<template>
  <div class="pt-debug">
    <p class="pt-debug-hint">{{ $t('portal.admin.debug.hint') }}</p>

    <AdminDebugBulkTools :achievements="achievements" @changed="loadUsers" />

    <!-- ─── User picker ─────────────────────────────────────────── -->
    <section class="pt-debug-card">
      <h3 class="pt-debug-title">{{ $t('portal.admin.debug.userPicker') }}</h3>
      <p class="pt-debug-sub">{{ $t('portal.admin.debug.userPickerHint') }}</p>
      <select v-model.number="selectedUserId" class="pt-debug-select mk-select-chevron">
        <option :value="null" disabled>—</option>
        <option v-for="u in users" :key="u.user_id" :value="u.user_id">
          {{ userLabel(u) }}
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
        >
          {{ $t('portal.admin.debug.xpApply') }}
        </button>
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
        >
          {{ $t('portal.admin.debug.levelApply') }}
        </button>
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
        <select
          v-model="achCategory"
          class="pt-debug-select mk-select-chevron pt-debug-select--inline"
        >
          <option value="">{{ $t('portal.admin.debug.categoryAll') }}</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>

      <div class="pt-debug-ach-list">
        <div v-for="ach in filteredAchievements" :key="ach.id" class="pt-debug-ach-row">
          <div class="pt-debug-ach-meta">
            <span class="pt-debug-ach-name">
              {{ $t(ach.name_key) }}
            </span>
            <span class="pt-debug-ach-tag">{{ ach.category }} · T{{ ach.tier }}</span>
          </div>
          <div class="pt-debug-ach-actions">
            <button
              type="button"
              class="pt-debug-btn pt-debug-btn--small"
              :disabled="!selectedUserId"
              @click="unlockAch(ach)"
            >
              {{ $t('portal.admin.debug.achievementUnlock') }}
            </button>
            <button
              type="button"
              class="pt-debug-btn pt-debug-btn--small pt-debug-btn--danger"
              :disabled="!selectedUserId"
              @click="lockAch(ach)"
            >
              {{ $t('portal.admin.debug.achievementLock') }}
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminDebugBulkTools from '@/components/portal/admin/AdminDebugBulkTools.vue'
import { useToast } from '@/composables/useToast'
import { usePortalAdminDebug } from '@/composables/portal/usePortalAdminDebug'
import { USER_ROLE } from '@/constants/auth'
import { TOAST_TYPE } from '@/constants/toast'
import { getLocale } from '@/i18n'

import '@/assets/styles/portal/admin-debug.css'

const { showToast } = useToast()
const { t } = useI18n()
const debugApi = usePortalAdminDebug()

const users = ref([])
const achievements = ref([])
const selectedUserId = ref(null)
const xpAmount = ref(null)
const xpNote = ref('')
const levelTarget = ref(null)
const achQuery = ref('')
const achCategory = ref('')

const categories = computed(() => {
  const set = new Set(achievements.value.map(a => a.category).filter(Boolean))
  return Array.from(set).sort()
})

const filteredAchievements = computed(() => {
  const q = achQuery.value.trim().toLowerCase()
  return achievements.value.filter(a => {
    if (achCategory.value && a.category !== achCategory.value) return false
    if (!q) return true
    const name = a.secret ? '???' : t(a.name_key).toLowerCase()
    return name.includes(q) || a.id.toLowerCase().includes(q)
  })
})

function userLabel(u) {
  return [
    u.display_name,
    u.role === USER_ROLE.ADMIN && t('common.administrator'),
    t('portal.admin.debug.level', { n: u.level }),
    t('portal.admin.debug.xp', { n: u.xp.toLocaleString(getLocale()) }),
  ]
    .filter(Boolean)
    .join(' · ')
}

async function loadUsers() {
  try {
    users.value = await debugApi.listUsers()
  } catch (err) {
    console.error('[AdminDebug.loadUsers]', err)
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

async function loadAchievements() {
  try {
    achievements.value = await debugApi.listAchievements()
  } catch (err) {
    console.error('[AdminDebug.loadAchievements]', err)
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

function syncSelectedFromResponse(body) {
  const user = users.value.find(u => u.user_id === selectedUserId.value)
  if (user && body?.xp != null) {
    user.xp = body.xp
    user.level = body.level
  }
}

async function applyXp() {
  if (!selectedUserId.value || !xpAmount.value) return
  try {
    const body = await debugApi.grantXp(selectedUserId.value, xpAmount.value, xpNote.value || null)
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
    const body = await debugApi.setLevel(selectedUserId.value, levelTarget.value)
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
    await debugApi.unlockAchievement(selectedUserId.value, ach.id)
    showToast(t('portal.admin.debug.achievementUnlocked'), TOAST_TYPE.OK)
  } catch {
    showToast(t('portal.admin.debug.errorGeneric'), TOAST_TYPE.ERR)
  }
}

async function lockAch(ach) {
  if (!selectedUserId.value) return
  try {
    await debugApi.lockAchievement(selectedUserId.value, ach.id)
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
