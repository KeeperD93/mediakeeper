<template>
  <div class="wzh-pv-page">
    <div class="wzh-pv-head">
      <div>
        <p class="wzh-pv-h1 wzh-pv-h1--page">{{ $t('portal.tickets.title') }}</p>
        <p class="wzh-pv-sub wzh-pv-sub--head">{{ $t('portal.tickets.subtitle') }}</p>
      </div>
      <span class="wzh-pv-cta" :class="{ 'wzh-prs': pressCreate }">
        <Plus :size="16" :stroke-width="2.5" />
        {{ $t('portal.tickets.create') }}
        <MousePointer2 v-if="pressCreate" class="wzh-cur" :size="22" />
      </span>
    </div>
    <p class="wzh-pv-fpills">
      <span
        v-for="status in FILTERS"
        :key="status"
        class="wzh-pv-fpill"
        :class="{ 'is-on': !status }"
      >
        {{ $t(`portal.tickets.status.${status || 'all'}`) }}
      </span>
    </p>
    <div v-for="ticket in tickets" :key="ticket.id" class="wzh-pv-tcd">
      <span class="wzh-pv-tcd-v" :class="`wzh-pv-tint-${ticket.tint}`" />
      <div>
        <p class="wzh-pv-tcd-m">
          <span class="wzh-pv-tcd-id">#{{ ticket.id }}</span>
          <span class="wzh-pv-tp wzh-pv-tp--issue">
            {{ $t(`portal.tickets.types.${ticket.type}`) }}
          </span>
          <span class="wzh-pv-tp" :class="`wzh-pv-tp--${ticket.status}`">
            {{ $t(`portal.tickets.status.${ticket.status}`) }}
          </span>
        </p>
        <p class="wzh-pv-tcd-t">{{ $t(ticket.titleKey) }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// The « Problèmes » page, reduced: title, report button, status filters, tickets.
import { MousePointer2, Plus } from 'lucide-vue-next'
import { TICKET_STATUS } from '@/constants/tickets'

defineProps({
  tickets: { type: Array, default: () => [] },
  pressCreate: { type: Boolean, default: false },
})

// « Tous » (no status) first, as on the real page.
const FILTERS = ['', ...Object.values(TICKET_STATUS)]
</script>
