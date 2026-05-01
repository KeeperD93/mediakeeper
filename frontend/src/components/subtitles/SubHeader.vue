<template>
  <div class="sub-top-right">
    <!-- Profil actif -->
    <div v-if="profiles.length" class="sub-profile-select">
      <select v-model="selectedProfileId" class="sub-profile-sel" @change="onProfileChange">
        <option v-for="p in profiles" :key="p.id" :value="p.id">
          {{ p.name }}{{ p.is_default ? ' ★' : '' }}
        </option>
      </select>
      <button class="sub-profile-edit-btn" :title="$t('subtitles.profiles')" @click="$emit('edit-profiles')">
        <SlidersHorizontal :size="13" />
      </button>
    </div>

    <!-- Auto-download indicator -->
    <span v-if="defaultProfile && defaultProfile.auto_download" class="sub-auto-badge" :title="$t('subtitles.autoDownloadEnabled')">
      <Zap :size="12" />
      AUTO
    </span>

    <!-- OpenSubtitles quota -->
    <div class="sub-quota" :title="$t('subtitles.downloadsLeft')">
      <template v-if="quota && !quota.error">
        <div class="sub-quota-bar"><div class="sub-quota-fill" :style="{ width: quotaPct + '%', background: quotaColor }" /></div>
        <span class="sub-quota-text">{{ quota.remaining_downloads }}/{{ quota.allowed_downloads }}</span>
      </template>
      <span v-else class="sub-quota-text">—/—</span>
    </div>

    <!-- Settings (si non configure) -->
    <button v-if="!configured" class="sub-settings-btn" @click="$router.push('/settings')">
      <Settings :size="14" />
      {{ $t('subtitles.goToSettings') }}
    </button>
  </div>

  <!-- Not configured banner -->
  <div v-if="!configured" class="sub-banner-warn glass-card">
    <AlertCircle :size="18" />
    <span>{{ $t('subtitles.notConfigured') }}</span>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useSubtitles } from '@/composables/useSubtitles'
import { AlertCircle, Settings, SlidersHorizontal, Zap } from 'lucide-vue-next'

const emit = defineEmits(['edit-profiles', 'audit'])

const { configured, profiles, activeProfileId, defaultProfile, setActiveProfile, quota, quotaPct, quotaColor } = useSubtitles()

const selectedProfileId = ref(activeProfileId.value)

watch(activeProfileId, (v) => { selectedProfileId.value = v })

function onProfileChange() {
  setActiveProfile(selectedProfileId.value)
}
</script>

<style scoped>
.sub-top-right { display: flex; align-items: center; gap: 10px; }

.sub-profile-select { display: flex; align-items: center; gap: 4px; }
.sub-profile-sel {
  padding: 6px 10px; border-radius: var(--radius-btn); font-size: var(--text-2xs);
  background: var(--surface-2); border: .5px solid var(--border-strong);
  color: var(--text-primary); outline: none; font-family: inherit; cursor: pointer;
}
.sub-profile-sel option { background: var(--bg-secondary); color: var(--text-primary); }
.sub-profile-edit-btn {
  width: 28px; height: 28px; border-radius: var(--radius-btn); display: flex; align-items: center; justify-content: center;
  background: var(--surface-2); border: .5px solid var(--border-strong);
  color: var(--text-muted); cursor: pointer;
}
.sub-profile-edit-btn:hover { background: rgba(255,255,255,.08); color: var(--text-primary); }

.sub-settings-btn {
  display: inline-flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: var(--radius-btn);
  font-size: var(--text-2xs); font-weight: var(--font-regular); border: .5px solid rgba(255,255,255,.1);
  background: var(--surface-2); color: var(--text-secondary); cursor: pointer; font-family: inherit;
}
.sub-settings-btn:hover { background: rgba(255,255,255,.08); }

.sub-auto-badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 3px 8px; border-radius: var(--radius-btn);
  font-size: .55rem; font-weight: var(--font-bold); letter-spacing: .5px;
  background: rgba(var(--color-success-rgb),.1); color: var(--color-success); border: .5px solid rgba(var(--color-success-rgb),.15);
}

.sub-quota { display: inline-flex; align-items: center; gap: 6px; }
.sub-quota-bar { width: 48px; height: 4px; border-radius: 2px; background: var(--surface-3); overflow: hidden; }
.sub-quota-fill { height: 100%; border-radius: 2px; transition: width .4s; }
.sub-quota-text { font-size: var(--text-3xs); color: var(--text-muted); white-space: nowrap; }

.sub-banner-warn {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px; margin-bottom: 16px;
  color: var(--color-warning); font-size: var(--text-sm); border-color: rgba(var(--color-warning-rgb),.15);
}
.glass-card { background: var(--surface-1); backdrop-filter: blur(16px); border: .5px solid var(--border-default); border-radius: var(--radius-card); }
</style>
