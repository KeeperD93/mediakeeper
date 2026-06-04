<template>
  <div class="ru-tab ru-tab-trophies">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.tabs.trophies') }}</h3>
      <div class="ru-act-grid">
        <article class="ru-act-card ru-act-card--accent">
          <div class="ru-act-icon"><Award :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">{{ $t('requestsAdmin.users.labels.level') }}</span>
            <span class="ru-act-val">{{ user.level }}</span>
            <span class="ru-act-foot">{{ user.xp }} XP</span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--success">
          <div class="ru-act-icon"><Trophy :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.trophies.unlocked') }}
            </span>
            <span class="ru-act-val">{{ trophies?.unlocked_count ?? 0 }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.trophies.unlockedFoot') }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--warn">
          <div class="ru-act-icon"><Target :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.trophies.inProgress') }}
            </span>
            <span class="ru-act-val">{{ trophies?.in_progress_count ?? 0 }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.trophies.inProgressFoot') }}
            </span>
          </div>
        </article>
      </div>
    </section>

    <section v-if="trophies?.unlocked?.length" class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.trophies.unlocked') }}</h3>
      <ul class="ru-trophy-grid">
        <li
          v-for="trophy in trophies.unlocked"
          :key="trophy.id"
          class="ru-trophy ru-trophy--unlocked"
        >
          <RuTrophyIcon :icon="trophy.icon" />
          <span class="ru-trophy-name">{{ trophyName(trophy) }}</span>
          <div class="ru-trophy-meta">
            <span
              v-if="trophy.rarity"
              class="ru-trophy-rarity"
              :class="`ru-trophy-rarity--${trophy.rarity}`"
            >
              {{ $t(`portal.profile.rarity.${trophy.rarity}`) }}
            </span>
            <span v-if="trophy.xp_reward" class="ru-trophy-xp">+{{ trophy.xp_reward }} XP</span>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="trophies?.in_progress?.length" class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.trophies.inProgress') }}</h3>
      <ul class="ru-trophy-grid">
        <li
          v-for="trophy in trophies.in_progress"
          :key="trophy.id"
          class="ru-trophy ru-trophy--progress"
        >
          <RuTrophyIcon :icon="trophy.icon" :muted="true" />
          <span class="ru-trophy-name">{{ trophyName(trophy) }}</span>
          <span class="ru-trophy-progress">{{ trophy.progress }} / {{ trophy.threshold }}</span>
        </li>
      </ul>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.trophies.xpHistory') }}</h3>
      <div v-if="loadingXp" class="ru-loading">{{ $t('common.loading') }}</div>
      <p v-else-if="!xp.length" class="ru-help">
        {{ $t('requestsAdmin.users.drawer.trophies.xpHistoryEmpty') }}
      </p>
      <ol v-else class="ru-feed-list">
        <li v-for="entry in xp" :key="entry.id" class="ru-feed-row">
          <span class="ru-feed-date">{{ fmt(entry.created_at) }}</span>
          <span class="ru-feed-main">{{ formatXpAction(entry) }}</span>
          <span class="ru-feed-tail">+{{ entry.xp }} XP</span>
        </li>
      </ol>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Award, Target, Trophy } from 'lucide-vue-next'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import RuTrophyIcon from '../RuTrophyIcon.vue'
import { localizedDateTime } from '@/utils/datetime'
import '@/assets/styles/portal/admin-users-feed.css'

const props = defineProps({
  user: { type: Object, required: true },
  activity: { type: Object, default: null },
})

const { t, te } = useI18n()
const api = usePortalAdminUsers()

const trophies = ref(null)
const xp = ref([])
const loadingXp = ref(false)

async function load() {
  if (!props.user?.id) return
  loadingXp.value = true
  try {
    const [tr, xh] = await Promise.all([
      api.fetchTrophies(props.user.id),
      api.fetchXpHistory(props.user.id, { limit: 200 }),
    ])
    trophies.value = tr || null
    xp.value = xh?.items || []
  } finally {
    loadingXp.value = false
  }
}

watch(() => props.user.id, load)
onMounted(load)

function trophyName(tr) {
  const key = tr.name_key
  if (!key) return ''
  return te(key) ? t(key) : key
}

const ACH_REF_RE = /^ach:(.+)$/

const achievementById = computed(() => {
  const map = new Map()
  const list = trophies.value
  if (!list) return map
  for (const t of [...(list.unlocked || []), ...(list.in_progress || [])]) {
    if (t?.id) map.set(t.id, t)
  }
  return map
})

function formatXpAction(entry) {
  if (entry?.action === 'achievement_unlocked') {
    const m = ACH_REF_RE.exec(entry.reference || '')
    const trophy = m ? achievementById.value.get(m[1]) : null
    if (trophy) {
      return t('requestsAdmin.users.drawer.xpAction.achievementNamed', {
        name: trophyName(trophy),
      })
    }
  }
  return t(`requestsAdmin.users.drawer.xpAction.${entry.action}`, entry.action)
}

function fmt(value) {
  if (!value) return '—'
  try {
    return localizedDateTime(new Date(value))
  } catch {
    return value
  }
}
</script>
