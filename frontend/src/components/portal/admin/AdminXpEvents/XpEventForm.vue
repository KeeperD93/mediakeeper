<template>
  <Teleport to="body">
    <div class="pt-popup-overlay" @click.self="$emit('close')">
      <div class="pt-popup">
        <div class="pt-popup-header">
          <h2>
            {{
              isEdit
                ? $t('portal.admin.xpEvents.editTitle')
                : $t('portal.admin.xpEvents.createTitle')
            }}
          </h2>
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
          <label>{{ $t('portal.admin.xpEvents.name') }}</label>
          <input
            v-model="form.name"
            class="pt-input"
            maxlength="100"
            :placeholder="$t('portal.admin.xpEvents.namePlaceholder')"
          />

          <label>{{ $t('portal.admin.xpEvents.description') }}</label>
          <textarea v-model="form.description" class="pt-input" rows="2" maxlength="500" />

          <div class="pt-row-2">
            <div>
              <label>{{ $t('portal.admin.xpEvents.multiplier') }}</label>
              <input
                v-model.number="form.multiplier"
                type="number"
                step="0.5"
                min="0.5"
                max="20"
                class="pt-input"
              />
            </div>
            <div>
              <label>{{ $t('portal.admin.xpEvents.actionFilter') }}</label>
              <div class="pt-action-filter">
                <label class="pt-action-row pt-action-row--all">
                  <input
                    type="checkbox"
                    :checked="!selectedActions.length"
                    @change="selectedActions = []"
                  />
                  <strong>{{ $t('portal.admin.xpEvents.allActions') }}</strong>
                </label>
                <label v-for="a in availableActions" :key="a" class="pt-action-row">
                  <input
                    :checked="selectedActions.includes(a)"
                    type="checkbox"
                    :value="a"
                    @change="onActionToggle(a, $event.target.checked)"
                  />
                  <span>{{ $t(`portal.admin.xpEvents.actions.${a}`) }}</span>
                  <code class="pt-action-code">{{ a }}</code>
                </label>
              </div>
            </div>
          </div>

          <div class="pt-row-2">
            <div>
              <label>{{ $t('portal.admin.xpEvents.startsAt') }}</label>
              <input v-model="form.starts_at" type="datetime-local" class="pt-input" />
            </div>
            <div>
              <label>{{ $t('portal.admin.xpEvents.endsAt') }}</label>
              <input v-model="form.ends_at" type="datetime-local" class="pt-input" />
            </div>
          </div>

          <label class="pt-checkbox">
            <input v-model="form.enabled" type="checkbox" />
            {{ $t('portal.admin.xpEvents.enabled') }}
          </label>
        </div>
        <div class="pt-popup-footer">
          <button class="pt-btn" @click="$emit('close')">{{ $t('common.cancel') }}</button>
          <button class="pt-btn pt-btn--primary" :disabled="!canSave" @click="$emit('submit')">
            {{ $t('common.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { X } from 'lucide-vue-next'

const form = defineModel('form', { type: Object, required: true })
const selectedActions = defineModel('selectedActions', { type: Array, required: true })
defineProps({
  availableActions: { type: Array, required: true },
  canSave: { type: Boolean, required: true },
  isEdit: { type: Boolean, default: false },
})
defineEmits(['close', 'submit'])

function onActionToggle(action, checked) {
  const next = [...selectedActions.value]
  if (checked) {
    if (!next.includes(action)) next.push(action)
  } else {
    const idx = next.indexOf(action)
    if (idx >= 0) next.splice(idx, 1)
  }
  selectedActions.value = next
}
</script>

<style scoped>
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-size: var(--portal-text-sm);
}
.pt-btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.pt-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pt-action-filter {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-tertiary);
  padding: 0.4rem 0.5rem;
}
.pt-action-row {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.4rem;
  border-radius: var(--portal-radius-xs);
  cursor: pointer;
  font-size: var(--portal-text-sm) !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
}
.pt-action-row:hover {
  background: rgb(var(--accent-rgb), 0.08);
}
.pt-action-row--all {
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.25rem !important;
  padding-bottom: 0.4rem;
}
.pt-action-row input[type='checkbox'] {
  margin: 0;
  cursor: pointer;
  flex-shrink: 0;
}
.pt-action-row span {
  flex: 1;
}
.pt-action-code {
  font-family: var(--portal-font-mono);
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 1px 5px;
  border-radius: 3px;
}

.pt-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgb(0, 0, 0, 0.7);
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
  max-width: 560px;
  display: flex;
  flex-direction: column;
}
.pt-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.pt-popup-header h2 {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-popup-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: var(--portal-text-md);
  cursor: pointer;
}
.pt-popup-body {
  padding: 1rem 1.5rem;
  max-height: 70vh;
  overflow-y: auto;
}
.pt-popup-body label {
  display: block;
  font-size: var(--portal-text-sm);
  color: var(--text-muted);
  margin: 0.75rem 0 0.25rem;
}
.pt-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--portal-text-sm);
}
.pt-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.pt-checkbox {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  cursor: pointer;
  color: var(--text-primary) !important;
  font-size: var(--portal-text-sm) !important;
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
