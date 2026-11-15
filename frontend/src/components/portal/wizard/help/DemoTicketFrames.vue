<template>
  <!-- 1. The « Problèmes » tab: « Signaler un problème ». -->
  <div class="wzh-frame" :class="shown(0)">
    <DemoTopBar :tab="DEMO_TAB.PROBLEMS" :initial="initial" />
    <DemoTicketsPage :tickets="[DEMO_OLD_TICKET]" press-create />
  </div>

  <!-- 2. The report window: title from the library, type, description, « Enregistrer ». -->
  <div class="wzh-frame" :class="shown(1)">
    <DemoTopBar :tab="DEMO_TAB.PROBLEMS" :initial="initial" />
    <DemoTicketsPage :tickets="[DEMO_OLD_TICKET]" />
    <div class="wzh-pv-ovl">
      <div class="wzh-pv-dialog wzh-pv-dialog--ticket">
        <p class="wzh-pv-mh">
          {{ $t('portal.tickets.create') }}
          <X :size="14" />
        </p>
        <div class="wzh-pv-pp-b">
          <p class="wzh-pv-modes">
            <span class="wzh-pv-mode is-on">{{ $t('portal.tickets.picker.modeLibrary') }}</span>
            <span class="wzh-pv-mode">{{ $t('portal.tickets.picker.modeOther') }}</span>
          </p>
          <span class="wzh-pv-lbl">{{ $t('portal.tickets.picker.label') }}</span>
          <p class="wzh-pv-in">
            <span>{{ $t('portal.wizardHelp.screens.movie') }}</span>
            <small>{{ $t('portal.tickets.picker.kind.movie') }}</small>
          </p>
          <span class="wzh-pv-lbl">{{ $t('portal.tickets.issueType') }}</span>
          <p class="wzh-pv-in wzh-pv-in--sel">
            <span>{{ $t('portal.tickets.types.audio') }}</span>
            <ChevronDown :size="14" />
          </p>
          <span class="wzh-pv-lbl">{{ $t('portal.tickets.description') }}</span>
          <p class="wzh-pv-in wzh-pv-in--area">{{ $t('portal.wizardHelp.screens.issue') }}</p>
        </div>
        <div class="wzh-pv-mf">
          <span class="wzh-pv-pbtn wzh-prs">
            {{ $t('common.save') }}
            <MousePointer2 class="wzh-cur" :size="22" />
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- 3. The new ticket tops the list with its status. -->
  <div class="wzh-frame" :class="shown(2)">
    <DemoTopBar :tab="DEMO_TAB.PROBLEMS" :initial="initial" />
    <DemoTicketsPage :tickets="[DEMO_NEW_TICKET, DEMO_OLD_TICKET]" />
  </div>
</template>

<script setup>
import { ChevronDown, MousePointer2, X } from 'lucide-vue-next'
import DemoTicketsPage from './DemoTicketsPage.vue'
import DemoTopBar from './DemoTopBar.vue'
import { DEMO_NEW_TICKET, DEMO_OLD_TICKET, DEMO_TAB } from '@/constants/portalWizardHelp'

const props = defineProps({
  frame: { type: Number, default: 0 },
  initial: { type: String, default: '' },
})

const shown = index => ({ 'is-shown': props.frame === index })
</script>
