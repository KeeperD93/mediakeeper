<template>
  <Teleport to="body">
    <transition name="ru-drawer">
      <div v-if="open" class="ru-drawer-backdrop">
        <aside
          class="ru-drawer"
          role="dialog"
          aria-modal="true"
          :aria-label="user?.display_name || ''"
        >
          <header class="ru-drawer-header">
            <div class="ru-drawer-nav">
              <button
                class="ru-drawer-nav-btn"
                :disabled="!hasPrev"
                :aria-label="$t('requestsAdmin.users.drawer.nav.prev')"
                :title="$t('requestsAdmin.users.drawer.nav.prev')"
                @click="$emit('navigate', 'prev')"
              >
                <ChevronLeft :size="18" />
              </button>
              <span v-if="orderedIds.length" class="ru-drawer-nav-pos">
                {{
                  $t('requestsAdmin.users.drawer.nav.position', {
                    current: currentIndex + 1,
                    total: orderedIds.length,
                  })
                }}
              </span>
              <button
                class="ru-drawer-nav-btn"
                :disabled="!hasNext"
                :aria-label="$t('requestsAdmin.users.drawer.nav.next')"
                :title="$t('requestsAdmin.users.drawer.nav.next')"
                @click="$emit('navigate', 'next')"
              >
                <ChevronRight :size="18" />
              </button>
            </div>
            <button
              class="ru-drawer-close"
              :aria-label="$t('common.close')"
              @click="$emit('close')"
            >
              <X :size="18" />
            </button>
            <div v-if="user" class="ru-drawer-identity">
              <MkAvatar :src="user.avatar_url" :name="user.display_name" :size="56" />
              <div class="ru-drawer-id-text">
                <h2>{{ user.display_name }}</h2>
                <div class="ru-drawer-sub">
                  @{{ user.username }}
                  <RuUserBadge :variant="user.source === 'emby' ? 'info' : 'success'">
                    {{
                      user.source === 'emby'
                        ? 'Emby'
                        : $t('requestsAdmin.users.filters.source.local')
                    }}
                  </RuUserBadge>
                  <RuUserBadge :variant="user.account_active ? 'success' : 'muted'">
                    {{
                      user.account_active
                        ? $t('requestsAdmin.users.labels.active')
                        : $t('requestsAdmin.users.labels.inactive')
                    }}
                  </RuUserBadge>
                  <RuUserBadge
                    v-if="user.source === 'emby' && user.emby_is_disabled"
                    variant="danger"
                  >
                    {{ $t('requestsAdmin.users.labels.embyDisabled') }}
                  </RuUserBadge>
                  <RuUserBadge v-if="user.deleted_at" variant="danger">
                    {{ $t('requestsAdmin.users.labels.deletedShort') }}
                  </RuUserBadge>
                </div>
              </div>
            </div>
          </header>

          <div class="ru-drawer-tabs-wrap">
            <select
              class="ru-drawer-tabs-select"
              :value="activeTab"
              @change="activeTab = $event.target.value"
            >
              <option v-for="t in tabs" :key="t" :value="t">
                {{ $t(`requestsAdmin.users.drawer.tabs.${t}`) }}
              </option>
            </select>
            <nav class="ru-drawer-tabs" role="tablist">
              <button
                v-for="t in tabs"
                :key="t"
                role="tab"
                class="ru-drawer-tab"
                :class="{ 'is-active': activeTab === t }"
                :aria-selected="activeTab === t"
                @click="activeTab = t"
              >
                {{ $t(`requestsAdmin.users.drawer.tabs.${t}`) }}
              </button>
            </nav>
          </div>

          <div class="ru-drawer-body">
            <div v-if="loading && !user" class="ru-loading">{{ $t('common.loading') }}</div>
            <div v-else-if="!user" class="ru-empty">
              <p>{{ $t('requestsAdmin.users.drawer.loadError') }}</p>
            </div>
            <template v-else>
              <RuTabIdentity v-if="activeTab === 'identity'" :user="user" @changed="onChanged" />
              <RuTabAccess
                v-else-if="activeTab === 'access'"
                :user="user"
                :presets="presets"
                @changed="onChanged"
              />
              <RuTabSecurity
                v-else-if="activeTab === 'security'"
                :user="user"
                @changed="onChanged"
              />
              <RuTabActivity
                v-else-if="activeTab === 'activity'"
                :user="user"
                :activity="activity"
              />
              <RuTabTrophies
                v-else-if="activeTab === 'trophies'"
                :user="user"
                :activity="activity"
              />
              <RuTabNotes v-else-if="activeTab === 'notes'" :user="user" @changed="onChanged" />
              <RuTabAudit v-else-if="activeTab === 'audit'" :user="user" />
            </template>
          </div>
        </aside>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, X } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'
import RuUserBadge from './RuUserBadge.vue'
import RuTabIdentity from './tabs/RuTabIdentity.vue'
import RuTabAccess from './tabs/RuTabAccess.vue'
import RuTabSecurity from './tabs/RuTabSecurity.vue'
import RuTabActivity from './tabs/RuTabActivity.vue'
import RuTabTrophies from './tabs/RuTabTrophies.vue'
import RuTabNotes from './tabs/RuTabNotes.vue'
import RuTabAudit from './tabs/RuTabAudit.vue'

import { DRAWER_TABS } from '@/constants/portalAdminUsers'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'

import '@/assets/styles/portal/admin-users-drawer.css'
import '@/assets/styles/portal/admin-users-forms.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  profileId: { type: Number, default: null },
  orderedIds: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'changed', 'navigate'])

const currentIndex = computed(() => props.orderedIds.indexOf(props.profileId))
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(
  () => currentIndex.value >= 0 && currentIndex.value < props.orderedIds.length - 1,
)

const tabs = DRAWER_TABS
const activeTab = ref('identity')
const user = ref(null)
const activity = ref(null)
const presets = ref(null)
const loading = ref(false)

const api = usePortalAdminUsers()

async function load() {
  if (!props.profileId) {
    user.value = null
    activity.value = null
    return
  }
  loading.value = true
  try {
    const [u, a, p] = await Promise.all([
      api.fetchUser(props.profileId),
      api.fetchActivity(props.profileId),
      presets.value ? Promise.resolve(presets.value) : api.fetchPresets(),
    ])
    user.value = u || null
    activity.value = a || null
    if (!presets.value) presets.value = p
  } finally {
    loading.value = false
  }
}

async function onChanged() {
  await load()
  emit('changed')
}

watch(() => props.profileId, load, { immediate: false })
watch(
  () => props.open,
  v => {
    if (v) {
      activeTab.value = 'identity'
      load()
    }
  },
)
</script>
