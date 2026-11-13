<template>
  <div class="ob-panel ob-panel-done">
    <div class="ob-done-visual">
      <div class="ob-done-ring ob-done-ring-1" />
      <div class="ob-done-ring ob-done-ring-2" />
      <div class="ob-done-ring ob-done-ring-3" />
      <img
        src="/assets/icons/mk-logo-128.png"
        class="ob-done-logo"
        alt=""
        onerror="this.style.display = 'none'"
      />
    </div>
    <h2 class="ob-done-title">{{ $t('onboarding.doneTitle') }}</h2>
    <p class="ob-done-desc">{{ $t('onboarding.doneDesc') }}</p>
    <div class="ob-done-summary">
      <div class="ob-done-item" :class="{ ok: zoneSaved, skip: !zoneSaved }">
        <Clock :size="16" />
        <span>{{ $t('settings.timezoneTitle') }}</span>
        <span class="ob-done-badge">
          {{ zoneSaved ? $t('onboarding.configured') : $t('onboarding.skipped') }}
        </span>
      </div>
      <div
        class="ob-done-item"
        :class="{
          ok: emby.url && (emby.api_key || emby._configured),
          skip: !emby.url,
        }"
      >
        <img src="/assets/icons/emby.svg" width="16" height="16" />
        <span>Emby</span>
        <span class="ob-done-badge">
          {{
            emby.url && (emby.api_key || emby._configured)
              ? $t('onboarding.configured')
              : $t('onboarding.skipped')
          }}
        </span>
      </div>
      <div
        class="ob-done-item"
        :class="{
          ok: tmdb.api_key || tmdb._configured,
          skip: !(tmdb.api_key || tmdb._configured),
        }"
      >
        <img src="/assets/icons/tmdb.svg" width="16" height="16" />
        <span>TMDB</span>
        <span class="ob-done-badge">
          {{
            tmdb.api_key || tmdb._configured
              ? $t('onboarding.configured')
              : $t('onboarding.skipped')
          }}
        </span>
      </div>
      <div
        class="ob-done-item"
        :class="{
          ok: openSubs.api_key || openSubs._configured,
          skip: !(openSubs.api_key || openSubs._configured),
        }"
      >
        <Captions :size="16" />
        <span>OpenSubtitles</span>
        <span class="ob-done-badge">
          {{
            openSubs.api_key || openSubs._configured
              ? $t('onboarding.configured')
              : $t('onboarding.skipped')
          }}
        </span>
      </div>
      <div class="ob-done-item" :class="{ ok: hasFolders, skip: !hasFolders }">
        <Folder :size="16" />
        <span>{{ $t('onboarding.foldersTitle') }}</span>
        <span class="ob-done-badge">
          {{
            hasFolders
              ? folders.filter(f => f.path).length + ' ' + $t('onboarding.foldersConfigured')
              : $t('onboarding.skipped')
          }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Captions, Clock, Folder } from 'lucide-vue-next'

defineProps({
  zoneSaved: { type: Boolean, required: true },
  emby: { type: Object, required: true },
  tmdb: { type: Object, required: true },
  openSubs: { type: Object, required: true },
  folders: { type: Array, required: true },
  hasFolders: { type: Boolean, required: true },
})
</script>
