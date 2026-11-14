<template>
  <div class="wzh-pv-det">
    <div class="wzh-pv-art wzh-pv-art--det" />
    <div class="wzh-pv-det-c">
      <span class="wzh-pv-dposter wzh-pv-tint-blue">
        <PremiumRibbon v-if="requested" :label="requestedLabel" :bg="RIBBON.color" />
      </span>
      <div>
        <p class="wzh-pv-dt">{{ $t('portal.wizardHelp.screens.movie') }}</p>
        <p class="wzh-pv-facts">
          <span>{{ DEMO_DATA.year }}</span>
          <span>• {{ $t('portal.wizardHelp.screens.runtime') }}</span>
          <span class="wzh-pv-cert">{{ DEMO_DATA.certification }}</span>
          <span>• {{ $t('portal.wizardHelp.screens.language') }}</span>
        </p>
        <p class="wzh-pv-genres">
          <span class="wzh-pv-genre">{{ $t('portal.genres.aventure') }}</span>
          <span class="wzh-pv-genre">{{ $t('portal.genres.mystere') }}</span>
        </p>
        <div v-if="!requested" class="wzh-pv-acts">
          <span
            class="wzh-pv-vbtn wzh-pv-vbtn--req"
            :class="{ 'wzh-prs': press === DEMO_PRESS.REQUEST }"
          >
            <Plus :size="18" />
            {{ $t('portal.detail.request') }}
            <MousePointer2 v-if="press === DEMO_PRESS.REQUEST" class="wzh-cur" :size="22" />
          </span>
          <span class="wzh-pv-vbtn wzh-pv-vbtn--ghost">
            <Video :size="16" />
            {{ $t('portal.detail.watchTrailer') }}
          </span>
          <span
            class="wzh-pv-vbtn wzh-pv-vbtn--ghost wzh-pv-vbtn--icon"
            :class="{ 'wzh-prs': press === DEMO_PRESS.LIST }"
          >
            <span v-if="press === DEMO_PRESS.LIST" class="wzh-pv-tip">
              {{ $t('portal.detail.addToList') }}
            </span>
            <Bookmark :size="18" />
            <MousePointer2 v-if="press === DEMO_PRESS.LIST" class="wzh-cur" :size="22" />
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// A title's page, reduced, under the top bar: the request button and the bookmark.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bookmark, MousePointer2, Plus, Video } from 'lucide-vue-next'
import PremiumRibbon from '@/components/portal/PremiumRibbon.vue'
import { POSTER_STATUS, POSTER_STATUS_RIBBON } from '@/constants/portal'
import { DEMO_DATA, DEMO_PRESS } from '@/constants/portalWizardHelp'
import '@/assets/styles/portal/poster-card-ribbons.css'

defineProps({
  press: { type: String, default: DEMO_PRESS.NONE },
  // Once requested: the poster wears the ribbon and the buttons are gone.
  requested: { type: Boolean, default: false },
})

// Same ribbon as the real title page shows for a pending request.
const RIBBON = POSTER_STATUS_RIBBON[POSTER_STATUS.PENDING]
const { t } = useI18n()
const requestedLabel = computed(() => t(RIBBON.labelKey).toUpperCase())
</script>
