<template>
  <div>
    <h2 class="params-title">{{ $t('settings.title') }}</h2>

    <div v-if="loading" class="params-loading">
      <div v-for="i in 3" :key="i" class="params-skel" />
    </div>

    <template v-else>
      <section v-if="sourceMedia.length" class="params-section">
        <h3 class="params-section-title">{{ $t('settings.sourceMedia') }}</h3>
        <p class="params-section-desc">{{ $t('settings.sourceMediaDesc') }}</p>
        <div class="params-cards">
          <ToolCard
            v-for="[key, def] in sourceMedia"
            :key="key"
            :tool-key="key"
            :def="def"
            :cfg="config[key] || {}"
            :is-media="true"
            @toggle="onToggle(key, $event, true)"
            @save="onSave(key, $event, true)"
          />
        </div>
      </section>
      <section v-if="apis.length" class="params-section">
        <h3 class="params-section-title">{{ $t('settings.externalApis') }}</h3>
        <p class="params-section-desc">{{ $t('settings.externalApisDesc') }}</p>
        <div class="params-cards">
          <ToolCard
            v-for="[key, def] in apis"
            :key="key"
            :tool-key="key"
            :def="def"
            :cfg="config[key] || {}"
            @toggle="onToggle(key, $event, false)"
            @save="onSave(key, $event, false)"
          />
        </div>
      </section>
      <section v-if="tools.length" class="params-section">
        <h3 class="params-section-title">{{ $t('settings.tools') }}</h3>
        <p class="params-section-desc">{{ $t('settings.toolsDesc') }}</p>
        <div class="params-cards">
          <ToolCard
            v-for="[key, def] in tools"
            :key="key"
            :tool-key="key"
            :def="def"
            :cfg="config[key] || {}"
            @toggle="onToggle(key, $event, false)"
            @save="onSave(key, $event, false)"
          />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import ToolCard from '@/components/settings/ToolCard.vue'

const { t } = useI18n()
const { apiGet, apiPost } = useApi()
const { showToast } = useToast()

const loading = ref(true)
const definitions = ref({})
const config = ref({})

const sourceMedia = computed(() =>
  Object.entries(definitions.value).filter(([, d]) => d.type === 'source_media'),
)
const apis = computed(() => Object.entries(definitions.value).filter(([, d]) => d.type === 'api'))
const tools = computed(() => Object.entries(definitions.value).filter(([, d]) => d.type === 'tool'))

async function loadAll() {
  loading.value = true
  try {
    const [def, cfg] = await Promise.all([
      apiGet('/api/settings/tools/definition'),
      apiGet('/api/settings/tools'),
    ])
    if (def) definitions.value = def
    if (cfg) config.value = cfg
  } catch {
    /* silent: config load, UI stays on defaults */
  }
  loading.value = false
}

async function onToggle(key, enabled, isMedia) {
  if (isMedia && enabled) {
    for (const [k, d] of Object.entries(definitions.value)) {
      if (k !== key && d.type === 'source_media' && config.value[k]?.enabled) {
        config.value[k].enabled = false
        await apiPost(`/api/settings/tools/${k}`, { enabled: false })
      }
    }
  }
  if (!config.value[key]) config.value[key] = {}
  config.value[key].enabled = enabled
  await apiPost(`/api/settings/tools/${key}`, { enabled })
  showToast(
    `${definitions.value[key]?.label || key} ${enabled ? t('common.enabled') : t('common.disabled')}`,
    TOAST_TYPE.OK,
    2000,
  )
}

async function onSave(key, payload, isMedia) {
  try {
    const res = await apiPost(`/api/settings/tools/${key}`, { ...payload, enabled: true })
    if (res) {
      await loadAll()
      if (!config.value[key]) config.value[key] = {}
      config.value[key].enabled = true
      if (isMedia) {
        for (const [k, d] of Object.entries(definitions.value)) {
          if (k !== key && d.type === 'source_media')
            config.value[k] = { ...config.value[k], enabled: false }
        }
      }
      showToast(
        t('settings.taskConfigured', { name: definitions.value[key]?.label || key }),
        TOAST_TYPE.OK,
        2000,
      )
    }
  } catch {
    showToast(t('settings.saveError'), TOAST_TYPE.ERR)
  }
}

onMounted(loadAll)
</script>
