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
            <col class="ucol-w32" />
            <col class="ucol-w44" />
            <col class="ucol-w15p" />
            <col class="ucol-w24p" />
            <col class="ucol-w16p" />
            <col class="ucol-w9p" />
            <col class="ucol-w10p" />
            <col class="ucol-w9p" />
          </colgroup>
          <thead>
            <tr>
              <th class="dt-c">
                <input
                  type="checkbox"
                  class="dt-chk"
                  :checked="allSelected"
                  :indeterminate.prop="partiallySelected"
                  :aria-label="$t('common.selectAll')"
                  @change="toggleSelectAll"
                />
              </th>
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
            </tr>
          </thead>
          <tbody>
            <tr v-if="!users.users.length">
              <td colspan="8" class="dt-empty">{{ $t('stats.noUsers') }}</td>
            </tr>
            <tr
              v-for="u in users.users"
              :key="u.user_id"
              :class="{
                'user-hidden-row': u.is_hidden,
                'user-historical-row': u.is_historical,
                'user-row-selected': selected.has(u.user_id),
              }"
            >
              <td class="dt-c">
                <input
                  type="checkbox"
                  class="dt-chk"
                  :checked="selected.has(u.user_id)"
                  :aria-label="$t('common.select')"
                  @change="toggleSelect(u.user_id)"
                  @click.stop
                />
              </td>
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

    <!-- Bulk actions overlay — appears when at least one user is selected.
         Slides up from the bottom, centred. Same pattern as Gmail / GitHub. -->
    <Teleport to="body">
      <Transition name="bulk-slide">
        <div v-if="selected.size > 0" class="bulk-bar" role="region" aria-live="polite">
          <span class="bulk-count">
            {{ $tc('stats.bulkSelected', selected.size, { n: selected.size }) }}
          </span>
          <div class="bulk-actions">
            <MkButton
              variant="ghost"
              icon="eye-off"
              :disabled="!visibleSelected.length"
              @click="bulkHide"
            >
              {{ $t('stats.bulkHide') }}
            </MkButton>
            <MkButton
              variant="ghost"
              icon="eye"
              :disabled="!hiddenSelected.length"
              @click="bulkUnhide"
            >
              {{ $t('stats.bulkUnhide') }}
            </MkButton>
            <MkButton
              variant="primary"
              icon="shuffle"
              :disabled="selected.size !== 1"
              :title="selected.size === 1 ? '' : $t('stats.bulkMergeHint')"
              @click="bulkMerge"
            >
              {{ $t('stats.bulkMerge') }}
            </MkButton>
            <MkButton variant="danger" icon="trash-2" @click="bulkDelete">
              {{ $t('common.delete') }}
            </MkButton>
            <MkButton variant="link" @click="clearSelection">
              {{ $t('stats.bulkClear') }}
            </MkButton>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { useApi } from '@/composables/useApi'
import MkAvatar from '@/components/common/MkAvatar.vue'
import MkButton from '@/components/common/MkButton.vue'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useStatsUI } from '@/composables/useStatsUI'
import { sortArrow, sortArrowClass } from '@/components/stats/statsTableUtils'
import { ChevronLeft, ChevronRight, ChevronsLeft, Clock, EyeOff } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'
import '@/assets/styles/stats-tables.css'

const mkConfirm = useConfirm()

const { t, tc } = useI18n()
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

// Selection state — reactive Set so .add() / .delete() / .clear()
// automatically trigger re-renders (ref(new Set()) does not track method
// calls, only reassignments).
const selected = reactive(new Set())

const selectedUsers = computed(() =>
  users.value.users.filter(u => selected.has(u.user_id)),
)
const visibleSelected = computed(() => selectedUsers.value.filter(u => !u.is_hidden))
const hiddenSelected = computed(() => selectedUsers.value.filter(u => u.is_hidden))
const allSelected = computed(
  () => users.value.users.length > 0 && selected.size === users.value.users.length,
)
const partiallySelected = computed(() => selected.size > 0 && !allSelected.value)

function toggleSelect(userId) {
  if (selected.has(userId)) selected.delete(userId)
  else selected.add(userId)
}

function toggleSelectAll() {
  if (allSelected.value) {
    selected.clear()
  } else {
    users.value.users.forEach(u => selected.add(u.user_id))
  }
}

function clearSelection() {
  selected.clear()
}

async function bulkHide() {
  const targets = visibleSelected.value.slice()
  for (const u of targets) {
    await apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/hide`)
  }
  showToast(tc('stats.bulkUsersHidden', targets.length, { n: targets.length }), TOAST_TYPE.OK)
  clearSelection()
  fetchUsers()
}

async function bulkUnhide() {
  const targets = hiddenSelected.value.slice()
  for (const u of targets) {
    await apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/unhide`)
  }
  showToast(tc('stats.bulkUsersUnhidden', targets.length, { n: targets.length }), TOAST_TYPE.OK)
  clearSelection()
  fetchUsers()
}

function bulkMerge() {
  if (selected.value.size !== 1) return
  const u = selectedUsers.value[0]
  if (u) openMergeModal(u)
}

async function bulkDelete() {
  const targets = selectedUsers.value.slice()
  const ok = await mkConfirm({
    title: t('common.confirmTitle.deleteUser'),
    message: tc('stats.bulkDeleteConfirm', targets.length, { n: targets.length }),
    variant: 'danger',
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  for (const u of targets) {
    await apiDelete(`/api/stats/users/${encodeURIComponent(u.user_id)}`)
  }
  showToast(tc('stats.bulkUsersDeleted', targets.length, { n: targets.length }), TOAST_TYPE.OK)
  clearSelection()
  fetchUsers()
}

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
.ucol-w32 {
  width: 32px;
}
.ucol-w44 {
  width: 44px;
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

.dt-chk {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-500);
  cursor: pointer;
}

.user-row-selected {
  background: rgb(var(--accent-rgb), 0.06);
}

/* ─── Bulk actions overlay ─── */
.bulk-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 20px;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  box-shadow: var(--shadow-modal);
  backdrop-filter: blur(16px);
}
.bulk-count {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
}
.bulk-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bulk-slide-enter-active,
.bulk-slide-leave-active {
  transition:
    transform var(--duration-base) var(--ease-out),
    opacity var(--duration-base) var(--ease-out);
}
.bulk-slide-enter-from,
.bulk-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

@media (prefers-reduced-motion: reduce) {
  .bulk-slide-enter-active,
  .bulk-slide-leave-active {
    transition: opacity var(--duration-fast);
  }
  .bulk-slide-enter-from,
  .bulk-slide-leave-to {
    transform: translateX(-50%);
  }
}

@media (max-width: 767px) {
  .bulk-bar {
    bottom: 12px;
    padding: 10px 12px;
    gap: 10px;
    max-width: calc(100vw - 24px);
    flex-wrap: wrap;
    justify-content: center;
  }
  .bulk-actions {
    gap: 6px;
  }
}
</style>
