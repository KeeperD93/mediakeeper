<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="show" class="sub-modal-overlay mk-modal-sheet" @click.self="$emit('close')">
        <div class="sub-modal glass-card mk-modal-sheet-panel">
          <h3 class="sub-modal-title">{{ $t('subtitles.profiles') }}</h3>

          <!-- Profile list -->
          <div class="sub-prof-list">
            <div
              v-for="p in profiles"
              :key="p.id"
              class="sub-prof-row"
              :class="{ active: editId === p.id }"
            >
              <div class="sub-prof-info" @click="startEdit(p)">
                <span class="sub-prof-name">{{ p.name }}</span>
                <span v-if="p.is_default" class="sub-prof-default">
                  ★ {{ $t('subtitles.defaultProfile') }}
                </span>
                <span class="sub-prof-langs">
                  {{ (p.languages || []).map(l => l.toUpperCase()).join(', ') }}
                </span>
              </div>
              <div class="sub-prof-actions">
                <button
                  v-if="!p.is_default"
                  class="sub-prof-btn"
                  :title="$t('subtitles.setAsDefault')"
                  @click="makeDefault(p.id)"
                >
                  ★
                </button>
                <button
                  class="sub-prof-btn sub-prof-del"
                  :title="$t('subtitles.deleteProfile')"
                  @click="removeProfile(p.id)"
                >
                  <X :size="12" />
                </button>
              </div>
            </div>
          </div>

          <!-- Edit / Create form -->
          <div class="sub-prof-form">
            <h4 class="sub-prof-form-title">
              {{ editId ? $t('subtitles.editProfile') : $t('subtitles.createProfile') }}
            </h4>

            <div class="sub-prof-field">
              <label>{{ $t('subtitles.profileName') }}</label>
              <input v-model="form.name" class="sub-prof-input" />
            </div>

            <div class="sub-prof-field">
              <label>{{ $t('subtitles.languages') }}</label>
              <div class="sub-prof-checks">
                <label v-for="lang in availableLangs" :key="lang.code">
                  <input v-model="form.languages" type="checkbox" :value="lang.code" />
                  {{ lang.label }}
                </label>
              </div>
            </div>

            <div class="sub-prof-toggles">
              <label>
                <input v-model="form.include_hi" type="checkbox" />
                {{ $t('subtitles.includeHI') }}
              </label>
              <label>
                <input v-model="form.include_forced" type="checkbox" />
                {{ $t('subtitles.includeForced') }}
              </label>
              <label>
                <input v-model="form.exclude_ai" type="checkbox" />
                {{ $t('subtitles.excludeAI') }}
              </label>
              <label>
                <input v-model="form.exclude_machine" type="checkbox" />
                {{ $t('subtitles.excludeMachine') }}
              </label>
              <label>
                <input v-model="form.prefer_trusted" type="checkbox" />
                {{ $t('subtitles.preferTrusted') }}
              </label>
              <label>
                <input v-model="form.prefer_hash_match" type="checkbox" />
                {{ $t('subtitles.preferHash') }}
              </label>
            </div>

            <div class="sub-prof-field">
              <label>{{ $t('subtitles.minScore') }}: {{ form.min_score }}</label>
              <input
                v-model.number="form.min_score"
                type="range"
                min="1"
                max="5"
                step="0.5"
                class="sub-prof-range"
              />
            </div>

            <div class="sub-prof-form-actions">
              <button v-if="editId" class="sub-modal-cancel" @click="resetForm">
                {{ $t('common.cancel') }}
              </button>
              <button
                class="sub-modal-save"
                :disabled="!form.name.trim() || !form.languages.length"
                @click="saveProfile"
              >
                {{ editId ? $t('common.save') : $t('subtitles.createProfile') }}
              </button>
            </div>
          </div>

          <div class="sub-prof-close">
            <button class="sub-modal-cancel" @click="$emit('close')">
              {{ $t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useSubtitles } from '@/composables/useSubtitles'
import { X } from 'lucide-vue-next'

defineProps({ show: { type: Boolean, default: true } })
defineEmits(['close'])
const { t } = useI18n()
const { showToast } = useToast()
const {
  profiles,
  defaultLanguages,
  createProfile,
  updateProfile,
  deleteProfile,
  setDefaultProfile,
} = useSubtitles()

const availableLangs = [
  { code: 'fre', label: 'Français' },
  { code: 'eng', label: 'English' },
  { code: 'spa', label: 'Español' },
  { code: 'ger', label: 'Deutsch' },
  { code: 'ita', label: 'Italiano' },
  { code: 'por', label: 'Português' },
  { code: 'nld', label: 'Nederlands' },
  { code: 'rus', label: 'Русский' },
  { code: 'jpn', label: '日本語' },
  { code: 'kor', label: '한국어' },
  { code: 'chi', label: '中文' },
  { code: 'ara', label: 'العربية' },
  { code: 'pol', label: 'Polski' },
  { code: 'tur', label: 'Türkçe' },
  { code: 'swe', label: 'Svenska' },
  { code: 'dan', label: 'Dansk' },
  { code: 'nor', label: 'Norsk' },
  { code: 'fin', label: 'Suomi' },
  { code: 'ces', label: 'Čeština' },
  { code: 'ron', label: 'Română' },
  { code: 'hun', label: 'Magyar' },
  { code: 'ell', label: 'Ελληνικά' },
  { code: 'heb', label: 'עברית' },
  { code: 'tha', label: 'ไทย' },
  { code: 'vie', label: 'Tiếng Việt' },
  { code: 'ind', label: 'Bahasa Indonesia' },
  { code: 'ukr', label: 'Українська' },
  { code: 'hin', label: 'हिन्दी' },
]

const editId = ref(null)
const form = reactive({
  name: '',
  languages: [...defaultLanguages.value],
  include_hi: false,
  include_forced: true,
  exclude_ai: true,
  exclude_machine: true,
  prefer_trusted: true,
  prefer_hash_match: true,
  min_score: 3.0,
})

function resetForm() {
  editId.value = null
  form.name = ''
  form.languages = [...defaultLanguages.value]
  form.include_hi = false
  form.include_forced = true
  form.exclude_ai = true
  form.exclude_machine = true
  form.prefer_trusted = true
  form.prefer_hash_match = true
  form.min_score = 3.0
}

function startEdit(p) {
  editId.value = p.id
  form.name = p.name
  form.languages = [...(p.languages || [])]
  form.include_hi = p.include_hi
  form.include_forced = p.include_forced
  form.exclude_ai = p.exclude_ai
  form.exclude_machine = p.exclude_machine
  form.prefer_trusted = p.prefer_trusted
  form.prefer_hash_match = p.prefer_hash_match
  form.min_score = p.min_score
}

async function saveProfile() {
  const data = { ...form }
  if (editId.value) {
    await updateProfile(editId.value, data)
    showToast(t('subtitles.profileSaved'), TOAST_TYPE.OK)
  } else {
    await createProfile(data)
    showToast(t('subtitles.profileSaved'), TOAST_TYPE.OK)
  }
  resetForm()
}

async function removeProfile(id) {
  await deleteProfile(id)
  showToast(t('subtitles.profileDeleted'), TOAST_TYPE.OK)
  if (editId.value === id) resetForm()
}

async function makeDefault(id) {
  await setDefaultProfile(id)
}
</script>

<style scoped>
.sub-modal-overlay {
  z-index: 1000;
}
@media (min-width: 768px) {
  .sub-modal {
    width: 520px;
    padding: 22px;
  }
}
.sub-modal-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 14px;
}

.sub-prof-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}
.sub-prof-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: var(--radius-btn);
  background: rgb(255, 255, 255, 0.02);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.sub-prof-row:hover {
  background: var(--surface-2);
}
.sub-prof-row.active {
  border: 0.5px solid rgb(var(--accent-rgb), 0.3);
  background: rgb(var(--accent-rgb), 0.06);
}
.sub-prof-info {
  flex: 1;
  min-width: 0;
}
.sub-prof-name {
  font-size: var(--text-sm);
  font-weight: var(--font-regular);
  color: var(--text-primary);
}
.sub-prof-default {
  font-size: var(--text-3xs);
  color: var(--color-warning);
  margin-left: 6px;
}
.sub-prof-langs {
  display: block;
  font-size: var(--text-3xs);
  color: var(--text-muted);
  margin-top: 2px;
}
.sub-prof-actions {
  display: flex;
  gap: 4px;
}
.sub-prof-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-2xs);
}
.sub-prof-btn:hover {
  background: var(--surface-3);
  color: var(--text-primary);
}
.sub-prof-del:hover {
  background: rgb(244, 63, 94, 0.1);
  color: #f43f5e;
}

.sub-prof-form {
  border-top: 0.5px solid var(--border-default);
  padding-top: 14px;
}
.sub-prof-form-title {
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
  color: var(--text-muted);
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.sub-prof-field {
  margin-bottom: 10px;
}
.sub-prof-field label {
  display: block;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-bottom: 4px;
}
.sub-prof-input {
  width: 100%;
  padding: 7px 10px;
  border-radius: var(--radius-btn);
  font-size: var(--text-sm);
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}
.sub-prof-input:focus {
  border-color: rgb(var(--accent-rgb), 0.4);
}
.sub-prof-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.sub-prof-checks label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  cursor: pointer;
}
.sub-prof-toggles {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.sub-prof-toggles label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  cursor: pointer;
}
.sub-prof-range {
  width: 100%;
  accent-color: var(--accent-500);
}

.sub-prof-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
.sub-prof-close {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  border-top: 0.5px solid var(--border-default);
  padding-top: 12px;
}

.sub-modal-cancel,
.sub-modal-save {
  padding: 7px 16px;
  border-radius: var(--radius-btn);
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.sub-modal-cancel {
  background: var(--surface-2);
  color: var(--text-secondary);
}
.sub-modal-save {
  background: var(--accent-500);
  color: #fff;
}
.sub-modal-save:hover:not(:disabled) {
  opacity: 0.9;
}
.sub-modal-save:disabled {
  opacity: 0.4;
  cursor: default;
}

.glass-card {
  background: var(--surface-1);
  backdrop-filter: blur(16px);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity var(--duration-base);
}
.sub-fade-enter-from,
.sub-fade-leave-to {
  opacity: 0;
}
</style>
