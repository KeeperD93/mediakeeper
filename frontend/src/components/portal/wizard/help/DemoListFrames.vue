<template>
  <!-- 1. The lists page: « Nouvelle liste ». -->
  <div class="wzh-frame" :class="shown(0)">
    <DemoTopBar lists-on :initial="initial" />
    <DemoListsPage press-create />
  </div>

  <!-- 2. The « Créer une liste » window: a name, who sees it, « Enregistrer ». -->
  <div class="wzh-frame" :class="shown(1)">
    <DemoTopBar lists-on :initial="initial" />
    <DemoListsPage />
    <div class="wzh-pv-ovl">
      <div class="wzh-pv-dialog wzh-pv-dialog--list">
        <p class="wzh-pv-mh">
          {{ $t('portal.lists.form.create') }}
          <span class="wzh-pv-close"><X :size="14" /></span>
        </p>
        <div class="wzh-pv-lf-b">
          <span class="wzh-pv-lfl">{{ $t('portal.lists.form.name') }}</span>
          <p class="wzh-pv-lfi">{{ $t('portal.wizardHelp.screens.listName') }}</p>
          <span class="wzh-pv-lfl">{{ $t('portal.lists.form.privacyLabel') }}</span>
          <p class="wzh-pv-lfp">
            <span v-for="(p, i) in DEMO_LIST_PRIVACY" :key="p" :class="{ 'is-on': i === 0 }">
              {{ $t(`portal.lists.privacy.${p}`) }}
            </span>
          </p>
          <span class="wzh-pv-lfl">{{ $t('portal.lists.form.contentTypeLabel') }}</span>
          <p class="wzh-pv-lfp">
            <span v-for="(c, i) in DEMO_LIST_CONTENT" :key="c" :class="{ 'is-on': i === 0 }">
              {{ $t(`portal.lists.contentType.${c}`) }}
            </span>
          </p>
        </div>
        <div class="wzh-pv-mf">
          <span class="wzh-pv-lfb">{{ $t('portal.lists.form.cancel') }}</span>
          <span class="wzh-pv-lfb wzh-pv-lfb--pri wzh-prs">
            {{ $t('portal.lists.form.save') }}
            <MousePointer2 class="wzh-cur" :size="22" />
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- 3. A title's page: the « Ajouter à une liste » bookmark. -->
  <div class="wzh-frame" :class="shown(2)">
    <DemoTopBar :initial="initial" />
    <DemoTitleSheet :press="DEMO_PRESS.LIST" />
  </div>
</template>

<script setup>
import { MousePointer2, X } from 'lucide-vue-next'
import DemoListsPage from './DemoListsPage.vue'
import DemoTitleSheet from './DemoTitleSheet.vue'
import DemoTopBar from './DemoTopBar.vue'
import { DEMO_LIST_CONTENT, DEMO_LIST_PRIVACY, DEMO_PRESS } from '@/constants/portalWizardHelp'

const props = defineProps({
  frame: { type: Number, default: 0 },
  initial: { type: String, default: '' },
})

const shown = index => ({ 'is-shown': props.frame === index })
</script>
