<template>
  <div class="tab-panel">
    <div class="glass-card tbl-wrap">
      <div class="tbl-header">
        <h2 class="tbl-title">{{ $t('stats.allUsers') }}</h2>
        <div class="tbl-controls">
          <label class="ctrl-toggle" :class="{ active: showHistoricalOnly }">
            <input
              v-model="showHistoricalOnly"
              type="checkbox"
              @change="((usersPage = 1), fetchUsers())"
            />
            <Clock :size="14" />
            {{ $t('stats.showHistorical') }}
          </label>
          <label class="ctrl-toggle" :class="{ active: showHiddenUsers }">
            <input
              v-model="showHiddenUsers"
              type="checkbox"
              @change="((usersPage = 1), fetchUsers())"
            />
            <EyeOff :size="14" />
            {{ $t('stats.showHidden') }}
          </label>
          <div class="tbl-ctrl">
            <span class="ctrl-lbl">{{ $t('common.showPerPage') }}</span>
            <select
              v-model="usersPerPage"
              class="ctrl-sel mk-select-chevron"
              @change="((usersPage = 1), fetchUsers())"
            >
              <option :value="10">10</option>
              <option :value="30">30</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
              <option :value="500">500</option>
            </select>
          </div>
          <input
            v-model="usersSearch"
            class="ctrl-search"
            :placeholder="$t('common.search')"
            @input="debouncedFetchUsers"
          />
        </div>
      </div>
      <div v-if="loadingUsers && !users.users.length" class="tbl-loading">
        <div v-for="n in 5" :key="n" class="skel-tbl-row">
          <div class="skel-line w40" />
          <div class="skel-line w60" />
          <div class="skel-line w30" />
        </div>
      </div>
      <div v-else class="tbl-scroll">
        <table class="dt">
          <colgroup>
            <col class="ucol-w44" />
            <col class="ucol-w15p" />
            <col class="ucol-w24p" />
            <col class="ucol-w16p" />
            <col class="ucol-w9p" />
            <col class="ucol-w10p" />
            <col class="ucol-w9p" />
            <col class="ucol-actions" />
          </colgroup>
          <thead>
            <tr>
              <th></th>
              <th class="sortable" @click="toggleUserSort('name')">
                {{ $t('stats.user') }}
                <span :class="sortArrowClass('name', usersSortBy)">
                  {{ sortArrow('name', usersSortBy, usersSortOrder) }}
                </span>
              </th>
              <th>{{ $t('stats.lastPlay') }}</th>
              <th>{{ $t('stats.lastDevice') }}</th>
              <th class="sortable dt-r" @click="toggleUserSort('plays')">
                {{ $t('stats.plays') }}
                <span :class="sortArrowClass('plays', usersSortBy)">
                  {{ sortArrow('plays', usersSortBy, usersSortOrder) }}
                </span>
              </th>
              <th class="sortable dt-r" @click="toggleUserSort('duration')">
                {{ $t('stats.time') }}
                <span :class="sortArrowClass('duration', usersSortBy)">
                  {{ sortArrow('duration', usersSortBy, usersSortOrder) }}
                </span>
              </th>
              <th class="sortable dt-r" @click="toggleUserSort('last_seen')">
                {{ $t('stats.seen') }}
                <span :class="sortArrowClass('last_seen', usersSortBy)">
                  {{ sortArrow('last_seen', usersSortBy, usersSortOrder) }}
                </span>
              </th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!users.users.length">
              <td colspan="8" class="dt-empty">{{ $t('stats.noUsers') }}</td>
            </tr>
            <tr
              v-for="u in users.users"
              :key="u.user_id"
              :class="{ 'user-hidden-row': u.is_hidden, 'user-historical-row': u.is_historical }"
            >
              <td>
                <MkAvatar
                  :src="null"
                  :name="u.name || '?'"
                  :size="32"
                  class="dt-avatar mk-avatar--ring-subtle"
                />
              </td>
              <td class="dt-name dt-clickable" @click="openUserProfile(u.user_id, u.name, $event)">
                {{ u.name }}
                <span
                  v-if="u.is_historical"
                  class="user-badge user-badge-hist"
                  :title="$t('stats.historicalUser')"
                >
                  {{ $t('stats.historical') }}
                </span>
                <span
                  v-if="u.is_hidden"
                  class="user-badge user-badge-hidden"
                  :title="$t('stats.hiddenUser')"
                >
                  {{ $t('stats.hidden') }}
                </span>
              </td>
              <td class="dt-sec">
                {{
                  u.last_series ? u.last_series + ' — ' + (u.last_play || '') : u.last_play || '—'
                }}
              </td>
              <td class="dt-sec">{{ u.last_device || '—' }}</td>
              <td class="dt-r dt-bold">{{ (u.play_count || 0).toLocaleString() }}</td>
              <td class="dt-r dt-sec">{{ ticksToDuration(u.total_ticks) }}</td>
              <td class="dt-r dt-accent">{{ u.last_seen ? timeAgo(u.last_seen) : '—' }}</td>
              <td class="dt-actions">
                <button
                  v-if="!u.is_hidden"
                  class="dt-act-btn"
                  :title="$t('stats.hideUser')"
                  @click.stop="handleHideUser(u)"
                >
                  <EyeOff :size="14" />
                </button>
                <button
                  v-if="u.is_hidden"
                  class="dt-act-btn dt-act-show"
                  :title="$t('stats.unhideUser')"
                  @click.stop="handleUnhideUser(u)"
                >
                  <Eye :size="14" />
                </button>
                <button
                  class="dt-act-btn dt-act-merge"
                  :title="$t('stats.mergeUser')"
                  @click.stop="openMergeModal(u)"
                >
                  <ArrowLeftRight :size="14" />
                </button>
                <button
                  class="dt-act-btn dt-act-del"
                  :title="$t('stats.deleteUser')"
                  @click.stop="handleDeleteUser(u)"
                >
                  <Trash2 :size="14" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="users.total > usersPerPage" class="tbl-pag">
        <span class="pag-info">
          {{ (users.page - 1) * users.per_page + 1 }}–{{
            Math.min(users.page * users.per_page, users.total)
          }}
          {{ $t('common.of') }} {{ users.total }}
        </span>
        <div class="pag-btns">
          <button
            class="pag-btn"
            :disabled="usersPage <= 1"
            @click="((usersPage = 1), fetchUsers())"
          >
            <ChevronsLeft :size="12" />
          </button>
          <button class="pag-btn" :disabled="usersPage <= 1" @click="(usersPage--, fetchUsers())">
            <ChevronLeft :size="12" />
          </button>
          <span class="pag-cur">{{ usersPage }}</span>
          <button
            class="pag-btn pag-next"
            :disabled="usersPage >= Math.ceil(users.total / usersPerPage)"
            @click="(usersPage++, fetchUsers())"
          >
            <ChevronRight :size="12" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { useApi } from '@/composables/useApi'
import MkAvatar from '@/components/common/MkAvatar.vue'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useStatsUI } from '@/composables/useStatsUI'
import { sortArrow, sortArrowClass } from '@/components/stats/statsTableUtils'
import {
  ArrowLeftRight,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  Clock,
  Eye,
  EyeOff,
  Trash2,
} from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'
import '@/assets/styles/stats-tables.css'

const mkConfirm = useConfirm()

const { t } = useI18n()
const { users, loadingUsers, loadUsers, ticksToDuration, timeAgo } = useStats()
const { apiPost, apiDelete } = useApi()
const { showToast } = useToast()
const { openUserProfile, openMergeModal, registerUsersRefresh } = useStatsUI()

const usersPage = ref(1)
const usersPerPage = ref(30)
const usersSearch = ref('')
const usersSortBy = ref('last_seen')
const usersSortOrder = ref('desc')
const showHiddenUsers = ref(false)
const showHistoricalOnly = ref(false)
let usersDb = null

function fetchUsers() {
  loadUsers({
    page: usersPage.value,
    per_page: usersPerPage.value,
    sort_by: usersSortBy.value,
    sort_order: usersSortOrder.value,
    search: usersSearch.value,
    show_hidden: showHiddenUsers.value,
    historical_only: showHistoricalOnly.value,
  })
}

async function handleHideUser(u) {
  await apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/hide`)
  showToast(t('stats.userHidden', { name: u.name }), TOAST_TYPE.OK)
  fetchUsers()
}
async function handleUnhideUser(u) {
  await apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/unhide`)
  showToast(t('stats.userUnhidden', { name: u.name }), TOAST_TYPE.OK)
  fetchUsers()
}
async function handleDeleteUser(u) {
  const ok = await mkConfirm({
    title: t('common.confirmTitle.deleteUser'),
    message: t('stats.confirmDeleteUser', { name: u.name }),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  await apiDelete(`/api/stats/users/${encodeURIComponent(u.user_id)}`)
  showToast(t('stats.userDeleted', { name: u.name }), TOAST_TYPE.OK)
  fetchUsers()
}

function debouncedFetchUsers() {
  clearTimeout(usersDb)
  usersDb = setTimeout(() => {
    usersPage.value = 1
    fetchUsers()
  }, 300)
}
function toggleUserSort(c) {
  if (usersSortBy.value === c)
    usersSortOrder.value = usersSortOrder.value === 'desc' ? 'asc' : 'desc'
  else {
    usersSortBy.value = c
    usersSortOrder.value = 'desc'
  }
  usersPage.value = 1
  fetchUsers()
}

registerUsersRefresh(fetchUsers)
onMounted(() => {
  if (!users.value.users.length) fetchUsers()
})
</script>

<style scoped>
.ucol-w44 {
  width: 44px;
}
/* Actions column: must fit 3 buttons (~22px each + 4px gap = ~74px actual)
   without flex-end pushing them onto the previous column, which caused a
   visual mismatch between header (empty th) and body (td flex). */
.ucol-actions {
  width: 100px;
}
.ucol-w9p {
  width: 9%;
}
.ucol-w10p {
  width: 10%;
}
.ucol-w15p {
  width: 15%;
}
.ucol-w16p {
  width: 16%;
}
.ucol-w24p {
  width: 24%;
}
</style>
