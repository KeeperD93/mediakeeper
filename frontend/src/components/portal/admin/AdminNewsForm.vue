<template>
  <Teleport to="body">
    <div class="pt-popup-overlay" @click.self="$emit('close')">
      <div class="pt-popup pt-popup--md">
        <div class="pt-popup-header">
          <h2>{{ formTitle }}</h2>
          <button
            class="pt-popup-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="$emit('close')"
          >
            <X :size="14" />
          </button>
        </div>
        <div class="pt-popup-body">
          <label>{{ $t('portal.news.titleLabel') }}</label>
          <input v-model="form.title" class="pt-input" maxlength="300" />
          <label>{{ $t('portal.news.content') }}</label>
          <textarea v-model="form.content" class="pt-input" rows="5" maxlength="10000" />
          <label>{{ $t('portal.news.typeLabel') }}</label>
          <select v-model="form.type" class="pt-input">
            <option v-for="type in types" :key="type" :value="type">
              {{ $t(`portal.news.types.${type}`) }}
            </option>
          </select>
          <label>{{ $t('portal.admin.news.startAtLabel') }}</label>
          <input v-model="form.start_at" type="datetime-local" class="pt-input" />
          <label>{{ $t('portal.admin.news.endAtLabel') }}</label>
          <input v-model="form.end_at" type="datetime-local" class="pt-input" />
        </div>
        <div class="pt-popup-footer">
          <button class="pt-btn pt-btn--primary" :disabled="!form.title.trim()" @click="onSubmit">
            {{ submitLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'

const props = defineProps({
  initial: { type: Object, default: null },
  editingId: { type: [Number, null], default: null },
})
const emit = defineEmits(['close', 'submit'])

const { t } = useI18n()

const types = ['announcement', 'additions', 'maintenance', 'event', 'other']
const form = reactive({
  title: '',
  content: '',
  type: 'announcement',
  start_at: '',
  end_at: '',
})

const formTitle = computed(() =>
  props.editingId ? t('portal.admin.news.editMode') : t('portal.admin.createNews'),
)
const submitLabel = computed(() =>
  props.editingId ? t('portal.admin.news.editSave') : t('common.save'),
)

function toLocalInput(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function toIso(value) {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

function hydrate(source) {
  form.title = source?.title || ''
  form.content = source?.content || ''
  form.type = source?.type || 'announcement'
  form.start_at = toLocalInput(source?.start_at)
  form.end_at = toLocalInput(source?.end_at)
}

watch(() => props.initial, hydrate, { immediate: true })

function onSubmit() {
  emit('submit', {
    title: form.title,
    content: form.content,
    type: form.type,
    start_at: toIso(form.start_at),
    end_at: toIso(form.end_at),
  })
}
</script>

<style scoped>
.pt-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: var(--overlay-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.pt-popup {
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  width: 100%;
  display: flex;
  flex-direction: column;
}
.pt-popup--md {
  max-width: 500px;
}
.pt-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-popup-header h2 {
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}
.pt-popup-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: var(--text-md);
  cursor: pointer;
}
.pt-popup-body {
  padding: 1rem 1.5rem;
}
.pt-popup-body label {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0.75rem 0 0.25rem;
}
.pt-input {
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--text-sm);
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  text-align: right;
}
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--font-medium);
  cursor: pointer;
  font-size: var(--text-sm);
}
.pt-btn--primary {
  background: var(--accent);
  color: var(--text-primary);
}
</style>
