<template>
  <div class="ru-tab ru-tab-activity">
    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.tabs.activity') }}</h3>
      <div v-if="!activity" class="ru-loading">{{ $t('common.loading') }}</div>
      <div v-else class="ru-act-grid">
        <article class="ru-act-card ru-act-card--info">
          <div class="ru-act-icon"><Inbox :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.overview.requests') }}
            </span>
            <span class="ru-act-val">{{ activity.requests.total }}</span>
            <span class="ru-act-foot">
              {{
                $t('requestsAdmin.users.drawer.activity.pending', { n: activity.requests.pending })
              }}
              ·
              {{
                $t('requestsAdmin.users.drawer.activity.available', {
                  n: activity.requests.available,
                })
              }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--warn">
          <div class="ru-act-icon"><LifeBuoy :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.overview.tickets') }}
            </span>
            <span class="ru-act-val">{{ activity.tickets.total }}</span>
            <span class="ru-act-foot">
              {{ activity.tickets.open }} {{ $t('requestsAdmin.users.drawer.overview.openSuffix') }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--success">
          <div class="ru-act-icon"><ListMusic :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">{{ $t('requestsAdmin.users.drawer.overview.lists') }}</span>
            <span class="ru-act-val">{{ activity.lists.total }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.activity.listsFoot') }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--accent">
          <div class="ru-act-icon"><Star :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.activity.ratings') }}
            </span>
            <span class="ru-act-val">{{ activity.ratings.total }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.activity.ratingsFoot') }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--accent">
          <div class="ru-act-icon"><TrendingUp :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">{{ $t('requestsAdmin.users.drawer.activity.xp30') }}</span>
            <span class="ru-act-val">+{{ activity.xp.last_30_days }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.activity.xp30Foot') }}
            </span>
          </div>
        </article>
        <article class="ru-act-card ru-act-card--accent">
          <div class="ru-act-icon"><Sparkles :size="22" /></div>
          <div class="ru-act-body">
            <span class="ru-act-label">
              {{ $t('requestsAdmin.users.drawer.activity.xpTotal') }}
            </span>
            <span class="ru-act-val">{{ activity.xp.total }}</span>
            <span class="ru-act-foot">
              {{ $t('requestsAdmin.users.drawer.activity.xpTotalFoot') }}
            </span>
          </div>
        </article>
      </div>
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.activity.requestsList') }}</h3>
      <div v-if="loadingFeeds" class="ru-loading">{{ $t('common.loading') }}</div>
      <p v-else-if="!requests.length" class="ru-help">
        {{ $t('requestsAdmin.users.drawer.activity.noRequests') }}
      </p>
      <ul v-else class="ru-feed-list">
        <li v-for="r in requests" :key="r.id" class="ru-feed-row">
          <span class="ru-feed-date">{{ fmt(r.created_at) }}</span>
          <span class="ru-feed-main" :title="r.title">
            {{ r.title }}
            <span v-if="r.year" class="ru-feed-year">({{ r.year }})</span>
          </span>
          <RuUserBadge :variant="reqVariant(r.status)">
            {{ $t(`requestsAdmin.users.drawer.activity.reqStatus.${r.status}`, r.status) }}
          </RuUserBadge>
        </li>
      </ul>
      <PortalLoadMore
        :show="requestsHasMore"
        :loading="loadingMoreRequests"
        @load="loadMoreRequests"
      />
    </section>

    <section class="ru-tab-section">
      <h3>{{ $t('requestsAdmin.users.drawer.activity.ticketsList') }}</h3>
      <div v-if="loadingFeeds" class="ru-loading">{{ $t('common.loading') }}</div>
      <p v-else-if="!tickets.length" class="ru-help">
        {{ $t('requestsAdmin.users.drawer.activity.noTickets') }}
      </p>
      <ul v-else class="ru-feed-list">
        <li v-for="t in tickets" :key="t.id" class="ru-feed-row">
          <span class="ru-feed-date">{{ fmt(t.created_at) }}</span>
          <span class="ru-feed-main" :title="t.title">{{ t.title }}</span>
          <RuUserBadge :variant="t.status === 'open' ? 'info' : 'muted'">
            {{ $t(`requestsAdmin.users.drawer.activity.ticketStatus.${t.status}`, t.status) }}
          </RuUserBadge>
        </li>
      </ul>
      <PortalLoadMore
        :show="ticketsHasMore"
        :loading="loadingMoreTickets"
        @load="loadMoreTickets"
      />
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Inbox, LifeBuoy, ListMusic, Sparkles, Star, TrendingUp } from 'lucide-vue-next'
import { usePortalAdminUsers } from '@/composables/portal/usePortalAdminUsers'
import RuUserBadge from '../RuUserBadge.vue'
import PortalLoadMore from '@/components/portal/PortalLoadMore.vue'
import { localizedDate } from '@/utils/datetime'
import '@/assets/styles/portal/admin-users-feed.css'

const props = defineProps({
  user: { type: Object, required: true },
  activity: { type: Object, default: null },
})

const api = usePortalAdminUsers()
const FEED_PAGE = 100
const requests = ref([])
const tickets = ref([])
const loadingFeeds = ref(false)
const requestsHasMore = ref(false)
const ticketsHasMore = ref(false)
const loadingMoreRequests = ref(false)
const loadingMoreTickets = ref(false)

async function load() {
  if (!props.user?.id) return
  loadingFeeds.value = true
  try {
    const [rq, tk] = await Promise.all([
      api.fetchUserRequests(props.user.id, { limit: FEED_PAGE, offset: 0 }),
      api.fetchUserTickets(props.user.id, { limit: FEED_PAGE, offset: 0 }),
    ])
    requests.value = rq?.items || []
    tickets.value = tk?.items || []
    requestsHasMore.value = requests.value.length === FEED_PAGE
    ticketsHasMore.value = tickets.value.length === FEED_PAGE
  } finally {
    loadingFeeds.value = false
  }
}

async function loadMoreRequests() {
  if (loadingMoreRequests.value || !requestsHasMore.value) return
  loadingMoreRequests.value = true
  try {
    const res = await api.fetchUserRequests(props.user.id, {
      limit: FEED_PAGE,
      offset: requests.value.length,
    })
    const items = res?.items || []
    requests.value = [...requests.value, ...items]
    requestsHasMore.value = items.length === FEED_PAGE
  } finally {
    loadingMoreRequests.value = false
  }
}

async function loadMoreTickets() {
  if (loadingMoreTickets.value || !ticketsHasMore.value) return
  loadingMoreTickets.value = true
  try {
    const res = await api.fetchUserTickets(props.user.id, {
      limit: FEED_PAGE,
      offset: tickets.value.length,
    })
    const items = res?.items || []
    tickets.value = [...tickets.value, ...items]
    ticketsHasMore.value = items.length === FEED_PAGE
  } finally {
    loadingMoreTickets.value = false
  }
}

watch(() => props.user.id, load)
onMounted(load)

function reqVariant(status) {
  if (status === 'approved' || status === 'available') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'pending') return 'info'
  return 'neutral'
}

function fmt(value) {
  if (!value) return '—'
  try {
    return localizedDate(new Date(value))
  } catch {
    return value
  }
}
</script>
