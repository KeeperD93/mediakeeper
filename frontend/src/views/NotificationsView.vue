<template>
  <div class="cinema-notif mk-page-root">
    <div class="nf-content">
      <!-- ═══ TAB: Agents ═══ -->
      <div v-show="activeTab==='agents'" class="tab-panel">
        <div class="nf-kpis">
          <div class="nf-kpi glass-kpi">
            <span class="kpi-val" :class="discord.enabled ? 'nf-kpi-on' : 'nf-kpi-off'">{{ discord.enabled ? 'ON' : 'OFF' }}</span>
            <span class="kpi-label">{{ $t('notifications.kpiDiscord') }}</span>
          </div>
          <div class="nf-kpi glass-kpi">
            <span class="kpi-val nf-kpi-info">{{ discord.webhooks.length }}</span>
            <span class="kpi-label">{{ $t('notifications.kpiWebhooks') }}</span>
          </div>
          <div class="nf-kpi glass-kpi">
            <span class="kpi-val nf-kpi-on">{{ hStats.sent }}</span>
            <span class="kpi-label">{{ $t('notifications.kpiSent') }}</span>
          </div>
          <div class="nf-kpi glass-kpi">
            <span class="kpi-val nf-kpi-off">{{ hStats.failed }}</span>
            <span class="kpi-label">{{ $t('notifications.kpiFailed') }}</span>
          </div>
        </div>

        <div class="nf-agent-bar">
          <button v-for="a in agents" :key="a.id" class="nf-agent-btn" :class="{active:agent===a.id}" @click="agent=a.id">
            <component :is="a.icon" class="nf-agent-icon" />{{ a.label }}
          </button>
        </div>

        <template v-if="agent==='discord'">
          <div class="nf-section">
            <div class="nf-row">
              <label class="nf-switch nf-switch-row"><input v-model="discord.enabled" type="checkbox" @change="saveDiscord"/><div class="sw-track"/><span class="nf-switch-label">{{ $t('notifications.discord.enable') }}</span></label>
              <label class="nf-small-label">{{ $t('notifications.discord.delaySec') }} <input v-model.number="discord.delay" type="number" min="0" max="300" class="nf-input-sm"/></label>
            </div>
          </div>

          <div class="nf-section">
            <div class="nf-section-hdr"><h3 class="nf-section-title">{{ $t('notifications.discord.webhooks') }}</h3><button class="nf-add-btn" @click="addWebhook">{{ $t('notifications.discord.addWebhook') }}</button></div>
            <MkEmptyState v-if="!discord.webhooks.length" size="sm" :title="$t('notifications.discord.noWebhooks')" />
            <div v-for="(wh,idx) in discord.webhooks" :key="wh.id" class="nf-wh">
              <div class="nf-wh-head" :class="{disabled:!wh.enabled}" @click="wh._open=!wh._open">
                <IconDiscord class="nf-wh-ico nf-wh-ico-discord" />
                <span class="nf-wh-name">{{ wh.name||$t('notifications.discord.unnamed') }}</span>
                <span class="nf-health-dot" :class="whHealth(wh)" :title="whHealthTip(wh)"/>
                <span class="nf-wh-status" :class="wh.enabled?'on':'off'">{{ wh.enabled?$t('common.active'):$t('common.off') }}</span>
                <ChevronDown class="nf-chevron" :class="{open:wh._open}" />
              </div>
              <div v-if="wh._open" class="nf-wh-body">
                <div class="nf-wh-top">
                  <div class="nf-field nf-field-flex"><label class="nf-label">{{ $t('notifications.discord.webhookNameLabel') }}</label><input v-model="wh.name" type="text" class="nf-input nf-input-bold" :placeholder="$t('notifications.discord.webhookNamePlaceholder')"/></div>
                  <div class="nf-wh-ctrls">
                    <label class="nf-switch"><input v-model="wh.enabled" type="checkbox" @change="saveDiscord"/><div class="sw-track"/></label>
                    <button class="nf-del-btn" @click="discord.webhooks.splice(idx,1); saveDiscord()">{{ $t('common.delete') }}</button>
                  </div>
                </div>
                <div class="nf-field"><label class="nf-label">{{ $t('notifications.discord.urlLabel') }}</label><input v-model="wh.url" type="text" class="nf-input" :placeholder="wh.url_configured && !wh.url ? 'Deja configuree - saisir une nouvelle URL pour remplacer' : 'https://discord.com/api/webhooks/...'" /></div>
                <div class="nf-field">
                  <label class="nf-label">{{ $t('notifications.discord.eventsLabel') }}</label>
                  <div class="nf-events"><label v-for="ev in eventList" :key="ev.key" class="nf-ev-chk"><input v-model="wh.events[ev.key]" type="checkbox"/><span>{{ ev.label }}</span></label></div>
                </div>
                <div class="nf-test-row">
                  <span class="nf-test-label">{{ $t('notifications.discord.testLabelShort') }}</span>
                  <button v-for="tt in testTypes" :key="tt.id" class="nf-test-btn" :disabled="testing===idx+tt.id" @click="testWh(idx, tt.id)">{{ testing===idx+tt.id?'...':tt.label }}</button>
                </div>
              </div>
            </div>
          </div>

          <button class="nf-save-btn" :disabled="saving" @click="saveDiscord">{{ saving?$t('common.saving'):$t('notifications.discord.saveDiscord') }}</button>
        </template>
        <template v-else><MkEmptyState size="sm" :title="$t('notifications.discord.comingSoon', { agent })" /></template>
      </div>

      <!-- ═══ TAB: Templates ═══ -->
      <div v-show="activeTab==='templates'" class="tab-panel">
        <NotifTemplatesTab
          :webhooks="discord.webhooks"
          :tpl-groups="TPL_GROUPS"
          :testing="testing"
          :saving="saving"
          :get-active-tpl-vars="getActiveTplVars"
          :default-tpl="defaultTpl"
          :default-color="defaultColor"
          :render-preview="renderPreview"
          @test="testWh"
          @save="saveDiscord"
        />
      </div>

      <!-- ═══ TAB: Rules & DND ═══ -->
      <div v-show="activeTab==='rules'" class="tab-panel">
        <div class="nf-rules-grid">
          <div class="nf-section">
            <h3 class="nf-section-title"><Moon :size="14" /> {{ $t('notifications.discord.dndTitle') }}</h3>
            <p class="nf-desc">{{ $t('notifications.discord.dndDesc') }}</p>
            <label class="nf-toggle nf-toggle-spaced"><input v-model="rules.dnd_enabled" type="checkbox"/><span>{{ $t('notifications.discord.dndEnable') }}</span></label>
            <div v-if="rules.dnd_enabled" class="nf-dnd-times">
              <div class="nf-field"><label class="nf-label">{{ $t('notifications.discord.dndFrom') }}</label><input v-model="rules.dnd_start" type="time" class="nf-input nf-input-w130"/></div>
              <span class="nf-dnd-arrow">→</span>
              <div class="nf-field"><label class="nf-label">{{ $t('notifications.discord.dndTo') }}</label><input v-model="rules.dnd_end" type="time" class="nf-input nf-input-w130"/></div>
            </div>
          </div>
          <div class="nf-section">
            <h3 class="nf-section-title"><Filter :size="14" /> {{ $t('notifications.discord.filtersTitle') }}</h3>
            <p class="nf-desc">{{ $t('notifications.discord.filtersDesc') }}</p>
            <div class="nf-field">
              <label class="nf-label">{{ $t('notifications.discord.minResolution') }}</label>
              <select v-model="rules.min_resolution" class="nf-select nf-select-w150">
                <option value="">{{ $t('notifications.discord.historyAll') }}</option><option value="720p">720p+</option><option value="1080p">1080p+</option><option value="4K">4K</option>
              </select>
            </div>
            <div class="nf-field">
              <label class="nf-label">{{ $t('notifications.discord.libraries') }}</label>
              <input v-model="libraryFilterText" type="text" class="nf-input" :placeholder="$t('notifications.discord.librariesPlaceholder')"/>
            </div>
            <div class="nf-field">
              <label class="nf-label">{{ $t('notifications.discord.excludedGenres') }}</label>
              <input v-model="genreFilterText" type="text" class="nf-input" :placeholder="$t('notifications.discord.genresPlaceholder')"/>
            </div>
          </div>
        </div>
        <button class="nf-save-btn nf-save-btn-spaced" @click="saveRules">{{ $t('notifications.discord.saveRules') }}</button>
      </div>

      <!-- ═══ TAB: History ═══ -->
      <div v-show="activeTab==='history'" class="tab-panel">
        <div class="nf-hist-bar">
          <select v-model="histFilter" class="nf-select nf-select-w140">
            <option value="">{{ $t('notifications.discord.historyAll') }}</option><option value="sent">{{ $t('notifications.discord.historySent') }}</option><option value="failed">{{ $t('notifications.discord.historyFailed') }}</option><option value="grouped">{{ $t('notifications.discord.historyGrouped') }}</option>
          </select>
          <button class="nf-btn-sm nf-btn-danger" @click="clearHistory">{{ $t('notifications.discord.clearHistory') }}</button>
        </div>
        <MkEmptyState v-if="!filteredHistory.length" size="sm" :title="$t('notifications.discord.noHistory')" />
        <div v-else class="nf-hist-list">
          <div v-for="h in filteredHistory" :key="h.id" class="nf-hist-row">
            <div v-if="h.status !== 'sent'" class="nf-hist-status" :class="'st-'+h.status">
              <X v-if="h.status === TASK_STATUS.FAILED" class="ic" />
              <Clock3 v-else class="ic" />
            </div>
            <div class="nf-hist-info">
              <div class="nf-hist-title">{{ h.title||h.event_type }}</div>
              <div class="nf-hist-sub">{{ h.webhook_name||h.channel }} · {{ h.event_type }}</div>
            </div>
            <div class="nf-hist-meta">
              <span class="nf-hist-date">{{ fmtDate(h.sent_at) }}</span>
              <span v-if="h.error" class="nf-hist-err" :title="h.error">{{ $t('notifications.discord.historyError') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ TAB: Configuration ═══ -->
      <div v-show="activeTab==='config'" class="tab-panel">
        <div class="nf-section">
          <h3 class="nf-section-title">{{ $t('notifications.discord.imageHostLabel') }}</h3>
          <div class="nf-field">
            <label class="nf-label">{{ $t('notifications.discord.imageHostLabel') }}</label>
            <select v-model="discord.image_host" class="nf-select nf-select-w200"><option value="imgur">Imgur</option></select>
          </div>
        </div>
        <div class="nf-section">
          <h3 class="nf-section-title">{{ $t('notifications.discord.imgurTitle') }}</h3>
          <p class="nf-desc">{{ $t('notifications.discord.imgurDesc') }}</p>
          <div class="nf-field"><label class="nf-label">{{ $t('notifications.discord.imgurClientId') }}</label><input v-model="imgur.client_id" type="text" class="nf-input" placeholder="Client ID"/></div>
          <div class="nf-field"><label class="nf-label">{{ $t('notifications.discord.imgurClientSecret') }}</label><input :type="imgurSecretInputType" :value="displayImgurSecret" class="nf-input" placeholder="Client Secret" @focus="onImgurSecretFocus" @input="onImgurSecretInput($event.target.value)"/></div>
          <button class="nf-save-sm" @click="saveImgurMasked">{{ $t('notifications.discord.saveImgur') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotifs } from '@/composables/useNotifs'
import { useNotifTemplates } from '@/composables/useNotifTemplates'
import { useTabSync } from '@/composables/useTabSync'
import NotifTemplatesTab from '@/components/notifications/NotifTemplatesTab.vue'
import { ChevronDown, Clock3, Filter, Mail, Moon, Send, X } from 'lucide-vue-next'
import { TASK_STATUS } from '@/constants/scheduler'
import IconDiscord from '@/components/icons/IconDiscord.vue'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import '@/assets/styles/notifications-view.css'

const { t } = useI18n()

const activeTab = useTabSync(['agents', 'templates', 'rules', 'history', 'config'], 'agents')
const agent = ref('discord')
const imgurSecretEditing = ref(false)

const {
  saving, testing, histFilter, history, hStats,
  discord, imgur, rules,
  libraryFilterText, genreFilterText, filteredHistory,
  whHealth, whHealthTip,
  addWebhook, testWh, saveDiscord, saveImgur, saveRules, clearHistory,
  fmtDate,
} = useNotifs()

const { TPL_GROUPS, testTypes, getActiveTplVars, defaultTpl, defaultColor, renderPreview, loadMeta } = useNotifTemplates()

const imgurSecretMask = computed(() => '*'.repeat(Math.max(1, Number(imgur.client_secret_length) || 0)))
const displayImgurSecret = computed(() => {
  if (imgurSecretEditing.value || !imgur.client_secret_configured) return imgur.client_secret || ''
  return imgurSecretMask.value
})
const imgurSecretInputType = computed(() => (
  imgur.client_secret_configured && !imgurSecretEditing.value ? 'text' : 'password'
))

function onImgurSecretFocus() {
  if (imgur.client_secret_configured && !imgurSecretEditing.value) {
    imgurSecretEditing.value = true
    imgur.client_secret = ''
  }
}

function onImgurSecretInput(value) {
  imgurSecretEditing.value = true
  imgur.client_secret = value
}

async function saveImgurMasked() {
  await saveImgur()
  imgurSecretEditing.value = false
}

onMounted(loadMeta)

const agents = [
  { id:'discord',  label:'Discord',  icon: IconDiscord },
  { id:'telegram', label:'Telegram', icon: Send },
  { id:'email',    label:'Email',    icon: Mail },
]
const eventList = computed(() => [
  {key:'added',label:t('notifications.events.added')},{key:'offline',label:t('notifications.events.offline')},{key:'duplicate',label:t('notifications.events.duplicate')},
  {key:'new_request',label:t('notifications.events.new_request')},{key:'request_approved',label:t('notifications.events.request_approved')},{key:'request_available',label:t('notifications.events.request_available')},
  {key:'partially_available',label:t('notifications.events.partially_available')},{key:'request_rejected',label:t('notifications.events.request_rejected')},
  {key:'new_issue',label:t('notifications.events.new_issue')},{key:'issue_comment',label:t('notifications.events.issue_comment')},{key:'issue_resolved',label:t('notifications.events.issue_resolved')},{key:'emby_alerts',label:t('notifications.events.emby_alerts')},
])
</script>
