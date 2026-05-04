<template>
  <div class="mm-config-body">
    <p class="mm-rt-desc">
      {{ $t('mediaManager.releaseTagsDesc') }}
    </p>

    <div class="mm-rt-meta">
      <span>{{ $t('mediaManager.releaseTagsCount', { n: draftTags.length }) }}</span>
      <button class="mm-btn-sm" :disabled="resetting" @click="confirmReset">
        <RotateCcw :size="12" />
        {{ $t('mediaManager.releaseTagsResetBtn') }}
      </button>
    </div>

    <div class="mm-rt-list">
      <div v-for="(tag, i) in draftTags" :key="tag + i" class="mm-rt-row">
        <span
          class="mm-rt-tag"
          :class="{ 'mm-rt-tag-default': isDefault(tag) }"
          :title="
            isDefault(tag)
              ? $t('mediaManager.releaseTagsBuiltIn')
              : $t('mediaManager.releaseTagsCustom')
          "
        >
          {{ tag }}
        </span>
        <button class="mm-btn-sm mm-rt-remove" :title="$t('common.delete')" @click="removeTag(i)">
          ✕
        </button>
      </div>
      <div v-if="!draftTags.length" class="mm-state mm-rt-empty">
        <span class="mm-rt-empty-text">{{ $t('mediaManager.releaseTagsEmpty') }}</span>
      </div>
    </div>

    <hr class="mm-rt-divider" />

    <div class="mm-label">{{ $t('mediaManager.releaseTagsAdd') }}</div>
    <div class="mm-rt-add-grid">
      <input
        v-model="newTag"
        class="mm-folder-input mm-rt-input"
        :placeholder="$t('mediaManager.releaseTagsPlaceholder')"
        maxlength="64"
        @keydown.enter.prevent="addTag"
      />
      <button class="mm-btn-sm mm-btn-success" :disabled="!canAdd" @click="addTag">+</button>
    </div>

    <div class="mm-config-footer mm-rt-footer">
      <button class="mm-btn-sm" :disabled="!isDirty" @click="cancelChanges">
        {{ $t('common.cancel') }}
      </button>
      <button
        class="mm-btn-sm mm-btn-success"
        :class="{ 'mm-btn-saved': justSaved }"
        :disabled="!isDirty || saving"
        @click="save"
      >
        <Check />
        {{ justSaved ? $t('common.saved') + ' ✓' : $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaManager } from '@/composables/useMediaManager'
import { Check, RotateCcw } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'

const mkConfirm = useConfirm()

const { t } = useI18n()
const {
  releaseTags,
  releaseTagsDefaults,
  releaseTagsLoaded,
  loadReleaseTags,
  saveReleaseTags,
  resetReleaseTags,
} = useMediaManager()

const draftTags = ref([...releaseTags.value])
const newTag = ref('')
const saving = ref(false)
const resetting = ref(false)
const justSaved = ref(false)

watch(releaseTags, v => {
  if (!isDirty.value) draftTags.value = [...v]
})

const defaultsSet = computed(
  () => new Set((releaseTagsDefaults.value || []).map(t => t.toLowerCase())),
)
function isDefault(tag) {
  return defaultsSet.value.has(tag.toLowerCase())
}

const normalized = computed(() => draftTags.value.map(t => t.trim()).filter(Boolean))
const isDirty = computed(() => {
  const a = normalized.value
  const b = (releaseTags.value || []).map(t => t.trim()).filter(Boolean)
  if (a.length !== b.length) return true
  return a.some((t, i) => t !== b[i])
})
const canAdd = computed(() => {
  const v = newTag.value.trim()
  if (!v || v.length > 64) return false
  return !draftTags.value.some(x => x.toLowerCase() === v.toLowerCase())
})

function addTag() {
  if (!canAdd.value) return
  draftTags.value.push(newTag.value.trim())
  newTag.value = ''
}
function removeTag(i) {
  draftTags.value.splice(i, 1)
}
function cancelChanges() {
  draftTags.value = [...(releaseTags.value || [])]
}

async function save() {
  saving.value = true
  const ok = await saveReleaseTags(normalized.value)
  saving.value = false
  if (ok) {
    justSaved.value = true
    setTimeout(() => {
      justSaved.value = false
    }, 1800)
  }
}

async function confirmReset() {
  const confirmed = await mkConfirm({
    title: t('common.confirmTitle.reset'),
    message: t('mediaManager.releaseTagsResetConfirm'),
    variant: 'warn',
  })
  if (!confirmed) return
  resetting.value = true
  const ok = await resetReleaseTags()
  resetting.value = false
  if (ok) draftTags.value = [...releaseTags.value]
}

onMounted(() => {
  if (!releaseTagsLoaded.value) loadReleaseTags()
})
</script>

<style scoped>
.mm-rt-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 0.6rem;
}
.mm-rt-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.mm-rt-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  max-height: 280px;
  overflow-y: auto;
  padding: 0.35rem;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.mm-rt-row {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
}
.mm-rt-tag {
  font-family: monospace;
  font-size: var(--text-2xs);
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
  background: rgb(var(--accent-rgb), 0.12);
  color: var(--accent-300);
  border: 1px solid rgb(var(--accent-rgb), 0.2);
  cursor: default;
}
.mm-rt-tag-default {
  background: var(--surface-2);
  color: var(--text-secondary);
  border-color: var(--border-strong);
}
.mm-rt-remove {
  padding: 0 0.35rem;
  min-height: 22px;
  color: var(--mm-red);
  background: transparent;
  border: none;
}
.mm-rt-empty {
  padding: 0.5rem;
}
.mm-rt-empty-text {
  font-size: var(--text-xs);
}
.mm-rt-divider {
  border-color: var(--border);
  margin: 0.6rem 0;
}
.mm-rt-add-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.4rem;
  margin-top: 0.4rem;
}
.mm-rt-input {
  margin-top: 0;
  font-family: monospace;
}
.mm-rt-footer {
  display: flex;
  gap: 0.4rem;
  justify-content: flex-end;
}
@media (hover: hover) {
  .mm-rt-remove:hover {
    background: rgb(var(--color-error-rgb), 0.1);
  }
}
</style>
