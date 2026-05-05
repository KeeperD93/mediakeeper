<template>
  <MkEmptyState
    v-if="!webhooks.length"
    size="sm"
    :title="$t('notifications.discord.noWebhookFirst')"
  />
  <template v-else>
    <!-- Webhook selector -->
    <div class="nf-tpl-wh-bar">
      <button
        v-for="(wh, idx) in webhooks"
        :key="wh.id"
        class="nf-tpl-wh-btn"
        :class="{ active: activeTplWh === idx }"
        @click="activeTplWh = idx"
      >
        <IconDiscord :size="12" class="nf-ic-discord" />
        {{ wh.name || 'Webhook ' + (idx + 1) }}
      </button>
    </div>

    <div v-if="webhooks[activeTplWh]" class="nf-tpl-layout">
      <!-- Sidebar groupes -->
      <div class="nf-tpl-sidebar">
        <div
          v-for="grp in tplGroups"
          :key="grp.id"
          class="nf-tpl-grp"
          :class="{ active: activeTplGroup === grp.id }"
          @click="((activeTplGroup = grp.id), (activeTplKey = grp.templates[0].key))"
        >
          <span class="nf-tpl-grp-icon" :style="{ color: grp.color }">{{ grp.icon }}</span>
          <span class="nf-tpl-grp-label">{{ grp.label }}</span>
          <span class="nf-tpl-grp-count">{{ grp.templates.length }}</span>
        </div>
      </div>

      <!-- Edit zone -->
      <div class="nf-tpl-main">
        <template v-for="grp in tplGroups" :key="grp.id">
          <div v-if="activeTplGroup === grp.id" class="nf-tpl-group-content">
            <div v-if="grp.templates.length > 1" class="nf-tpl-subtabs">
              <button
                v-for="tf in grp.templates"
                :key="tf.key"
                class="nf-tpl-subtab"
                :class="{ active: activeTplKey === tf.key }"
                @click="activeTplKey = tf.key"
              >
                {{ tf.label }}
              </button>
            </div>

            <template v-for="tf in grp.templates" :key="tf.key">
              <div v-if="activeTplKey === tf.key || grp.templates.length === 1">
                <!-- Toolbar : variables -->
                <div class="nf-tpl-toolbar">
                  <div class="nf-tpl-vars-row">
                    <span class="nf-tpl-vars-title">
                      {{ $t('notifications.discord.varsLabel') }}
                    </span>
                    <button
                      v-for="v in getActiveTplVars(activeTplKey)"
                      :key="v.key"
                      class="nf-tpl-var-chip"
                      :title="v.desc"
                      @click="insertVar(tf.key, '<' + v.key + '>')"
                    >
                      &lt;{{ v.key }}&gt;
                    </button>
                    <span v-if="!getActiveTplVars(activeTplKey).length" class="nf-tpl-vars-loading">
                      {{ $t('common.loading') }}
                    </span>
                  </div>
                </div>

                <!-- Side-by-side editor + preview -->
                <div class="nf-tpl-split">
                  <!-- Left: editor -->
                  <div class="nf-tpl-edit-col">
                    <div class="nf-tpl-edit-header">
                      <label class="nf-label">{{ $t('notifications.discord.tplLabel') }}</label>
                      <button
                        class="nf-tpl-reset-btn"
                        @click="resetTpl(webhooks[activeTplWh], tf.key)"
                      >
                        <RotateCcw :size="10" />
                        {{ $t('notifications.discord.resetDefault') }}
                      </button>
                    </div>
                    <textarea
                      :id="'tpl-' + tf.key + '-' + activeTplWh"
                      :value="webhooks[activeTplWh].templates[tf.key] || defaultTpl(tf.key)"
                      class="nf-textarea nf-textarea-tall"
                      @input="webhooks[activeTplWh].templates[tf.key] = $event.target.value"
                    />
                    <p class="nf-tpl-hint">{{ $t('notifications.discord.tplHint') }}</p>

                    <div class="nf-tpl-settings">
                      <div class="nf-tpl-setting-row">
                        <label class="nf-label nf-label-min80">
                          {{ $t('notifications.discord.varColor') }}
                        </label>
                        <input
                          type="color"
                          :value="
                            getTplSetting(webhooks[activeTplWh], tf.key, 'color') ||
                            defaultColor(tf.key)
                          "
                          class="nf-color-input"
                          @input="
                            setTplSetting(
                              webhooks[activeTplWh],
                              tf.key,
                              'color',
                              $event.target.value,
                            )
                          "
                        />
                        <span class="nf-setting-val">
                          {{
                            getTplSetting(webhooks[activeTplWh], tf.key, 'color') ||
                            defaultColor(tf.key)
                          }}
                        </span>
                      </div>
                      <div class="nf-tpl-setting-row">
                        <label class="nf-label nf-label-min80">
                          {{ $t('notifications.discord.varImageStyle') }}
                        </label>
                        <select
                          :value="
                            getTplSetting(webhooks[activeTplWh], tf.key, 'image_style') || 'image'
                          "
                          class="nf-select nf-select-sm"
                          @change="
                            setTplSetting(
                              webhooks[activeTplWh],
                              tf.key,
                              'image_style',
                              $event.target.value,
                            )
                          "
                        >
                          <option value="image">
                            {{ $t('notifications.discord.imageStyleFull') }}
                          </option>
                          <option value="thumbnail">
                            {{ $t('notifications.discord.imageStyleThumb') }}
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <!-- Right : preview -->
                  <div class="nf-tpl-preview-col">
                    <div class="nf-preview-label">
                      {{ $t('notifications.discord.previewLabel') }}
                    </div>
                    <div class="nf-discord-mock">
                      <div class="nf-discord-username">
                        <div class="nf-discord-avatar">M</div>
                        <span class="nf-discord-uname">MediaKeeper</span>
                        <span class="nf-discord-bot-tag">APP</span>
                      </div>
                      <template
                        v-for="(pv, pvk) in [
                          renderPreview(
                            webhooks[activeTplWh].templates[tf.key] || defaultTpl(tf.key),
                            tf.key,
                            getTplSetting(webhooks[activeTplWh], tf.key, 'image_style') || 'image',
                          ),
                        ]"
                        :key="pvk"
                      >
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <div v-if="pv.content" class="nf-discord-content" v-html="pv.content"></div>
                        <div class="nf-discord-embed-wrap">
                          <div
                            class="nf-discord-embed-bar"
                            :style="{
                              background:
                                getTplSetting(webhooks[activeTplWh], tf.key, 'color') ||
                                defaultColor(tf.key),
                            }"
                          ></div>
                          <!-- eslint-disable-next-line vue/no-v-html -->
                          <div class="nf-discord-embed-body" v-html="pv.embed"></div>
                        </div>
                      </template>
                      <div class="nf-discord-ts">
                        MediaKeeper · {{ $t('notifications.discord.today') }}
                      </div>
                    </div>
                    <button
                      v-if="tf.testId"
                      class="nf-test-btn nf-test-btn-full"
                      :disabled="testing === 'tpl' + tf.testId"
                      @click="$emit('test', activeTplWh, tf.testId)"
                    >
                      <Zap :size="13" />
                      {{
                        testing === 'tpl' + tf.testId
                          ? $t('notifications.discord.testSending')
                          : $t('notifications.discord.testFull')
                      }}
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>
    </div>

    <button class="nf-save-btn nf-save-btn-spaced" :disabled="saving" @click="$emit('save')">
      {{ $t('notifications.discord.saveTemplates') }}
    </button>
  </template>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { RotateCcw, Zap } from 'lucide-vue-next'
import IconDiscord from '@/components/icons/IconDiscord.vue'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

// NOTE: this component intentionally mutates sub-fields of the `webhooks`
// Array prop. The corresponding ESLint rule (vue/no-mutating-props) is
// disabled at config level (see eslint.config.js) — documented trade-off.
const props = defineProps({
  webhooks: { type: Array, required: true },
  tplGroups: { type: Array, required: true },
  testing: { type: String, default: null },
  saving: { type: Boolean, default: false },
  getActiveTplVars: { type: Function, required: true },
  defaultTpl: { type: Function, required: true },
  defaultColor: { type: Function, required: true },
  renderPreview: { type: Function, required: true },
})

defineEmits(['test', 'save'])

const activeTplWh = ref(0)
const activeTplGroup = ref('media')
const activeTplKey = ref('added_movie')

function insertVar(tplKey, variable) {
  const wh = props.webhooks[activeTplWh.value]
  if (!wh) return
  const el = document.getElementById('tpl-' + tplKey + '-' + activeTplWh.value)
  if (el) {
    const start = el.selectionStart
    const end = el.selectionEnd
    const val = wh.templates[tplKey] || ''
    wh.templates[tplKey] = val.slice(0, start) + variable + val.slice(end)
    nextTick(() => {
      el.focus()
      el.setSelectionRange(start + variable.length, start + variable.length)
    })
  } else {
    wh.templates[tplKey] = (wh.templates[tplKey] || '') + variable
  }
}

function resetTpl(wh, key) {
  if (!wh) return
  wh.templates[key] = props.defaultTpl(key)
  if (wh.settings && wh.settings[key]) delete wh.settings[key]
}

function getTplSetting(wh, tplKey, setting) {
  if (!wh || !wh.settings) return null
  return (wh.settings[tplKey] || {})[setting] || null
}

function setTplSetting(wh, tplKey, setting, value) {
  if (!wh) return
  if (!wh.settings) wh.settings = {}
  if (!wh.settings[tplKey]) wh.settings[tplKey] = {}
  wh.settings[tplKey][setting] = value
}
</script>
