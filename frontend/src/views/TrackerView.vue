<template>
  <div class="tk-page">
    <div class="tk-tabs" role="tablist" :aria-label="t('feedback.tracker.title')">
      <button
        id="tk-tab-pending"
        type="button"
        role="tab"
        aria-controls="tk-panel"
        :aria-selected="tab === 'pending'"
        :tabindex="tab === 'pending' ? 0 : -1"
        class="tk-tab"
        :class="{ 'tk-tab--on': tab === 'pending' }"
        @click="switchTab('pending')"
      >
        {{ t('feedback.tracker.tabPending') }}
        <span v-if="tab === 'pending' && reports.length" class="tk-badge">
          {{ reports.length }}
        </span>
      </button>
      <button
        id="tk-tab-rejected"
        type="button"
        role="tab"
        aria-controls="tk-panel"
        :aria-selected="tab === 'rejected'"
        :tabindex="tab === 'rejected' ? 0 : -1"
        class="tk-tab"
        :class="{ 'tk-tab--on': tab === 'rejected' }"
        @click="switchTab('rejected')"
      >
        {{ t('feedback.tracker.tabRejected') }}
      </button>
    </div>

    <div id="tk-panel" role="tabpanel" :aria-labelledby="`tk-tab-${tab}`">
      <p v-if="loading" class="tk-empty">{{ t('common.loading') }}</p>
      <p v-else-if="!reports.length" class="tk-empty">
        {{ tab === 'pending' ? t('feedback.tracker.empty') : t('feedback.tracker.emptyRejected') }}
      </p>

      <ul v-else class="tk-list">
        <li v-for="r in reports" :key="r.id" class="tk-card">
          <div class="tk-head">
            <span class="tk-type" :class="`tk-type--${r.type}`">
              {{ t(`feedback.modal.type_${r.type}`) }}
            </span>
            <h2 class="tk-title">{{ r.title }}</h2>
            <time class="tk-date">{{ formatDate(r.created_at) }}</time>
          </div>

          <p class="tk-meta">{{ metaLine(r) }}</p>
          <p v-if="locationLabel(r)" class="tk-loc">{{ locationLabel(r) }}</p>

          <!-- Read view -->
          <template v-if="editingId !== r.id">
            <p class="tk-desc">{{ r.description }}</p>
            <p v-if="r.reproduction" class="tk-repro">
              <strong>{{ t('feedback.tracker.reproduction') }} :</strong>
              {{ r.reproduction }}
            </p>
            <ul v-if="r.tags && r.tags.length" class="tk-taglist">
              <li v-for="tag in r.tags" :key="tag" class="tk-tag">{{ tagLabel(tag) }}</li>
            </ul>

            <div v-if="tab === 'pending'" class="tk-actions">
              <button type="button" class="tk-btn" :disabled="isBusy(r.id)" @click="startEdit(r)">
                {{ t('feedback.tracker.edit') }}
              </button>
              <button
                type="button"
                class="tk-btn tk-btn--go"
                :disabled="isBusy(r.id)"
                @click="validate(r)"
              >
                {{ t('feedback.tracker.validate') }}
              </button>
              <button
                type="button"
                class="tk-btn tk-btn--no"
                :disabled="isBusy(r.id)"
                @click="reject(r)"
              >
                {{ t('feedback.tracker.reject') }}
              </button>
            </div>
          </template>

          <!-- Edit view -->
          <form v-else class="tk-edit" @submit.prevent="save">
            <div class="tk-types">
              <button
                v-for="ty in FEEDBACK_TYPES"
                :key="ty"
                type="button"
                class="tk-chip"
                :class="{ 'tk-chip--on': form.type === ty }"
                :aria-pressed="form.type === ty"
                @click="form.type = ty"
              >
                {{ t(`feedback.modal.type_${ty}`) }}
              </button>
            </div>

            <label class="tk-field">
              <span>{{ t('feedback.modal.titleField') }}</span>
              <input
                v-model="form.title"
                type="text"
                :maxlength="FEEDBACK_MAX.title"
                class="tk-input"
              />
            </label>

            <label class="tk-field">
              <span>{{ t('feedback.modal.descField') }}</span>
              <textarea
                v-model="form.description"
                :maxlength="FEEDBACK_MAX.description"
                rows="4"
                class="tk-input"
              />
            </label>

            <label class="tk-field">
              <span>{{ t('feedback.modal.reproField') }}</span>
              <textarea
                v-model="form.reproduction"
                :maxlength="FEEDBACK_MAX.reproduction"
                rows="2"
                class="tk-input"
              />
            </label>

            <label class="tk-field">
              <span>{{ t('feedback.modal.resolution') }}</span>
              <input
                v-model="form.resolution"
                type="text"
                :maxlength="FEEDBACK_MAX.resolution"
                class="tk-input"
                :placeholder="t('feedback.modal.resolutionPlaceholder')"
              />
            </label>

            <fieldset class="tk-field tk-field--group">
              <legend>{{ t('feedback.modal.platform') }}</legend>
              <div class="tk-chips">
                <button
                  v-for="p in FEEDBACK_PLATFORMS"
                  :key="p"
                  type="button"
                  class="tk-chip"
                  :class="{ 'tk-chip--on': form.platforms.includes(p) }"
                  :aria-pressed="form.platforms.includes(p)"
                  @click="togglePlatform(p)"
                >
                  {{ t(`feedback.modal.platform_${p}`) }}
                </button>
              </div>
            </fieldset>

            <fieldset class="tk-field tk-field--group">
              <legend>{{ t('feedback.modal.tags') }}</legend>
              <div class="tk-chips">
                <button
                  v-for="tag in FEEDBACK_TAGS"
                  :key="tag"
                  type="button"
                  class="tk-chip"
                  :class="{ 'tk-chip--on': form.tags.includes(tag) }"
                  :aria-pressed="form.tags.includes(tag)"
                  @click="toggleTag(tag)"
                >
                  {{ t(`feedback.tags.${tag}`) }}
                </button>
              </div>
            </fieldset>

            <div class="tk-actions">
              <button
                type="button"
                class="tk-btn"
                :disabled="isBusy(editingId)"
                @click="cancelEdit"
              >
                {{ t('feedback.tracker.cancel') }}
              </button>
              <button
                type="submit"
                class="tk-btn tk-btn--go"
                :disabled="!canSave || isBusy(editingId)"
              >
                {{ t('feedback.tracker.save') }}
              </button>
            </div>
          </form>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  FEEDBACK_TYPES,
  FEEDBACK_PLATFORMS,
  FEEDBACK_TAGS,
  FEEDBACK_MAX,
} from '@/constants/feedback'
import { localizedDateTime } from '@/utils/datetime'
import { useFeedbackModeration } from '@/composables/useFeedbackModeration'

const { t } = useI18n()
const {
  tab,
  reports,
  loading,
  editingId,
  form,
  canSave,
  isBusy,
  load,
  switchTab,
  startEdit,
  cancelEdit,
  togglePlatform,
  toggleTag,
  save,
  validate,
  reject,
} = useFeedbackModeration()

function reporterLabel(r) {
  if (r.anonymous || !r.reporter_name) return t('feedback.tracker.anonymous')
  return t('feedback.tracker.by', { name: r.reporter_name })
}

function locationLabel(r) {
  return [r.zone, r.module, r.tab].filter(Boolean).join(' · ')
}

function platformLabel(p) {
  if (p === 'both') return t('feedback.tracker.platformBoth')
  return t(`feedback.modal.platform_${p}`)
}

function metaLine(r) {
  const parts = [reporterLabel(r)]
  if (r.platform) parts.push(platformLabel(r.platform))
  if (r.resolution) parts.push(r.resolution)
  return parts.join(' · ')
}

function tagLabel(tag) {
  const key = `feedback.tags.${tag}`
  const label = t(key)
  return label === key ? tag : label
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return localizedDateTime(d, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(load)
</script>

<style scoped>
.tk-page {
  padding: 1.25rem;
  max-width: 60rem;
  margin: 0 auto;
}

.tk-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}
.tk-tab {
  padding: 0.5rem 1rem;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 0.875rem;
  cursor: pointer;
}
.tk-tab--on {
  color: var(--text-primary);
  border-color: var(--accent-500);
  background: var(--bg-tertiary);
}
.tk-badge {
  margin-left: 0.4rem;
  padding: 0.05rem 0.4rem;
  border-radius: var(--radius-pill);
  background: var(--accent-500);
  color: var(--color-on-accent);
  font-size: 0.75rem;
}

.tk-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 3rem 1rem;
}

.tk-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  list-style: none;
  padding: 0;
  margin: 0;
}
.tk-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--bg-secondary);
  padding: 1rem;
}

.tk-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.tk-type {
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  font-weight: 600;
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.tk-type--bug {
  color: var(--color-error);
  border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
}
.tk-type--suggestion {
  color: var(--accent-500);
  border-color: color-mix(in srgb, var(--accent-500) 40%, transparent);
}
.tk-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1 1 12rem;
}
.tk-date {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.tk-meta,
.tk-loc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0.5rem 0 0;
}
.tk-desc {
  color: var(--text-primary);
  margin: 0.75rem 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.tk-repro {
  color: var(--text-secondary);
  margin: 0.5rem 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.tk-taglist {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
}
.tk-tag {
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  font-size: 0.72rem;
  color: var(--text-muted);
}

.tk-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}
.tk-btn {
  padding: 0.45rem 0.9rem;
  min-height: 44px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
  cursor: pointer;
}
.tk-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tk-btn--go {
  background: var(--accent-500);
  border-color: var(--accent-500);
  color: var(--color-on-accent);
}
.tk-btn--no {
  color: var(--color-error);
  border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
}

.tk-tab:focus-visible,
.tk-btn:focus-visible,
.tk-chip:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 1px;
}

.tk-edit {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}
.tk-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
.tk-field > span,
.tk-field legend {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.tk-input {
  padding: 0.5rem 0.6rem;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  font: inherit;
  width: 100%;
}
.tk-input:focus-visible {
  outline: var(--focus-ring);
  outline-offset: 1px;
}

.tk-types,
.tk-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.tk-chip {
  padding: 0.35rem 0.7rem;
  min-height: 44px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
}
.tk-chip--on {
  color: var(--color-on-accent);
  background: var(--accent-500);
  border-color: var(--accent-500);
}
</style>
