<template>
  <Teleport to="body">
    <transition name="atl-fade">
      <div
        v-if="open"
        class="atl-overlay mk-modal-sheet"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('requestsAdmin.users.drawerEmby.title')"
        @click.self="close"
      >
        <div class="atl-panel mk-modal-sheet-panel ru-import-panel" tabindex="-1">
          <div class="atl-header">
            <h2 class="atl-title">{{ $t('requestsAdmin.users.drawerEmby.title') }}</h2>
            <button class="atl-close" type="button" :aria-label="$t('common.close')" @click="close">
              <X :size="14" />
            </button>
          </div>
          <p class="ru-import-sub">{{ $t('requestsAdmin.users.drawerEmby.subtitle') }}</p>

          <div class="atl-body">
            <div v-if="loading" class="ru-loading">{{ $t('common.loading') }}</div>
            <p v-else-if="!candidates.length" class="atl-empty">
              {{ $t('requestsAdmin.users.drawerEmby.empty') }}
            </p>
            <template v-else>
              <div class="ru-import-toolbar">
                <button type="button" class="ru-pill" @click="toggleAll">
                  {{
                    allChecked
                      ? $t('common.unselectAll')
                      : $t('requestsAdmin.users.drawerEmby.selectAll')
                  }}
                </button>
                <span class="ru-import-counter">
                  {{
                    $t('requestsAdmin.users.drawerEmby.selected', {
                      count: selected.length,
                      total: candidates.length,
                    })
                  }}
                </span>
              </div>
              <ul class="ru-import-list">
                <li v-for="u in candidates" :key="u.emby_user_id" class="ru-import-row">
                  <label>
                    <input
                      type="checkbox"
                      :checked="selected.includes(u.emby_user_id)"
                      @change="toggle(u.emby_user_id)"
                    />
                    <MkAvatar :src="u.avatar_url" :name="u.username" :size="32" />
                    <div class="ru-import-info">
                      <span class="ru-import-name">{{ u.username }}</span>
                      <span class="ru-import-meta">
                        <RuUserBadge v-if="u.is_administrator" variant="premium">
                          {{ $t('requestsAdmin.users.drawerEmby.adminBadge') }}
                        </RuUserBadge>
                        <RuUserBadge v-if="u.is_disabled" variant="muted">
                          {{ $t('requestsAdmin.users.drawerEmby.disabledBadge') }}
                        </RuUserBadge>
                        <span v-if="u.last_login_date">
                          {{ $t('requestsAdmin.users.labels.lastLogin') }}:
                          {{ fmt(u.last_login_date) }}
                        </span>
                      </span>
                    </div>
                  </label>
                </li>
              </ul>
            </template>
          </div>

          <footer class="ru-import-footer">
            <button type="button" class="ru-btn ru-btn--ghost" @click="close">
              {{ $t('common.cancel') }}
            </button>
            <button
              type="button"
              class="ru-btn ru-btn--primary"
              :disabled="busy || !selected.length"
              @click="submit"
            >
              {{ $t('requestsAdmin.users.drawerEmby.import', { count: selected.length }) }}
            </button>
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import MkAvatar from '@/components/common/MkAvatar.vue'
import RuUserBadge from './RuUserBadge.vue'
import '@/assets/styles/portal/admin-users-modals.css'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'imported'])

const { t } = useI18n()
const { showToast } = useToast()
const api = usePortalAdminUsers()

const candidates = ref([])
const loading = ref(false)
const busy = ref(false)
const selected = ref([])

const allChecked = computed(
  () => candidates.value.length > 0 && selected.value.length === candidates.value.length,
)

watch(
  () => props.open,
  async v => {
    if (!v) return
    loading.value = true
    selected.value = []
    try {
      const res = await api.fetchEmbyUnimported()
      candidates.value = res?.items || []
    } finally {
      loading.value = false
    }
  },
)

function toggle(id) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(id)
}

function toggleAll() {
  if (allChecked.value) selected.value = []
  else selected.value = candidates.value.map(u => u.emby_user_id)
}

async function submit() {
  if (!selected.value.length) return
  busy.value = true
  try {
    const res = await api.importEmbySelected(selected.value)
    if (res?.error) {
      showToast(t('requestsAdmin.users.toasts.importError'), TOAST_TYPE.ERR)
      return
    }
    emit('imported', res)
  } finally {
    busy.value = false
  }
}

function close() {
  if (busy.value) return
  emit('close')
}

function fmt(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}
</script>
