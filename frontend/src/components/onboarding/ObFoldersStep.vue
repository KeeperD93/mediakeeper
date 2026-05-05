<template>
  <div class="ob-panel">
    <div class="ob-step-header">
      <div class="ob-step-icon ob-step-icon-folders">
        <Folder :size="22" :stroke-width="1.8" class="ob-step-icon-folder-ic" />
      </div>
      <div>
        <h2 class="ob-panel-title">{{ $t('onboarding.foldersTitle') }}</h2>
        <p class="ob-panel-desc">{{ $t('onboarding.foldersDesc') }}</p>
      </div>
    </div>

    <div class="ob-folders-list">
      <div v-for="(folder, i) in folders" :key="folder._id" class="ob-folder-card">
        <div class="ob-folder-card-top">
          <input
            v-model="folder.label"
            class="ob-input ob-folder-name-input"
            :placeholder="$t('onboarding.folderNamePlaceholder')"
          />
          <button
            class="ob-folder-remove"
            :title="$t('onboarding.folderRemove')"
            @click="$emit('remove-folder', i)"
          >
            <X :size="13" />
          </button>
        </div>
        <div class="ob-folder-path-row">
          <input
            v-model="folder.path"
            class="ob-input ob-mono ob-folder-path-input"
            readonly
            :placeholder="$t('onboarding.folderSelectPath')"
            @click="$emit('open-browser', folder._id)"
          />
          <button
            class="ob-folder-browse-btn"
            :title="$t('onboarding.folderSelectPath')"
            @click="$emit('open-browser', folder._id)"
          >
            <Folder :size="14" :stroke-width="1.8" />
          </button>
        </div>
        <div v-if="browseOpen === folder._id" class="ob-browse-panel">
          <div class="ob-browse-bc">
            <span class="ob-browse-crumb" @click="$emit('browse-to', '/')">/</span>
            <template v-for="(seg, si) in crumbs" :key="si">
              <span class="ob-browse-sep">/</span>
              <span
                class="ob-browse-crumb"
                @click="$emit('browse-to', '/' + crumbs.slice(0, si + 1).join('/'))"
              >
                {{ seg }}
              </span>
            </template>
          </div>
          <div class="ob-browse-list">
            <div v-if="browseLoading" class="ob-browse-empty"><span class="ob-spin" /></div>
            <div v-else-if="!browseDirs.length" class="ob-browse-empty">
              {{ $t('onboarding.noSubfolders') }}
            </div>
            <div
              v-for="d in browseDirs"
              :key="d.path"
              class="ob-browse-item"
              @click="$emit('browse-to', d.path)"
            >
              <Folder :size="13" :stroke-width="1.8" />
              <span class="ob-browse-name">{{ d.name }}</span>
              <button class="ob-browse-select" @click.stop="$emit('select-browse-path', i, d.path)">
                {{ $t('onboarding.folderSelect') }}
              </button>
            </div>
          </div>
          <div v-if="browsePath !== '/'" class="ob-browse-current">
            <button
              class="ob-browse-use-current"
              @click="$emit('select-browse-path', i, browsePath)"
            >
              <Check :size="11" :stroke-width="2.5" />
              {{ $t('onboarding.folderUseCurrent') }} {{ browsePath }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <button class="ob-add-folder-btn" @click="$emit('add-folder')">
      <Plus :size="13" />
      {{ $t('onboarding.folderAdd') }}
    </button>

    <p class="ob-folders-hint">{{ $t('onboarding.foldersHint') }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Check, Folder, Plus, X } from 'lucide-vue-next'

const props = defineProps({
  folders: { type: Array, required: true },
  browsePath: { type: String, default: '/' },
  browseDirs: { type: Array, default: () => [] },
  browseLoading: { type: Boolean, default: false },
  browseOpen: { type: [String, Number, null], default: null },
})

defineEmits(['add-folder', 'remove-folder', 'open-browser', 'browse-to', 'select-browse-path'])

const crumbs = computed(() => props.browsePath.replace(/^\/+/, '').split('/').filter(Boolean))
</script>

<style scoped>
.ob-step-icon-folders {
  background: rgb(245, 158, 11, 0.1);
}
.ob-step-icon-folder-ic {
  color: #f59e0b;
}
</style>
