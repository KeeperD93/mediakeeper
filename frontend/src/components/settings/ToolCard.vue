<template>
  <div class="tc" :class="{ active: cfg.enabled }">
    <!-- Header -->
    <div class="tc-header" @click="open = !open">
      <div class="tc-header-left">
        <img
          v-if="def.icon"
          :src="'/assets/icons/' + def.icon"
          class="tc-icon"
          @error="e => (e.target.style.display = 'none')"
        />
        <KeyRound v-else class="tc-icon-fallback" :size="28" />
        <span class="tc-label">{{ def.label }}</span>
      </div>
      <div class="tc-header-right" @click.stop>
        <span class="tc-status" :class="cfg.enabled ? 'on' : 'off'">
          {{ cfg.enabled ? $t('common.active') : $t('common.inactive') }}
        </span>
        <label class="tc-switch">
          <input
            type="checkbox"
            :checked="cfg.enabled"
            @change="$emit('toggle', $event.target.checked)"
          />
          <div class="tc-switch-track" />
        </label>
      </div>
    </div>

    <!-- Fields -->
    <div v-if="open && def.fields?.length" class="tc-body">
      <div v-for="f in def.fields" :key="f.key" class="tc-field">
        <label class="tc-field-label">{{ f.label }}</label>
        <input
          :type="inputType(f)"
          :value="displayValue(f)"
          :placeholder="fieldPlaceholder(f)"
          class="tc-input"
          @input="onFieldInput(f, $event.target.value)"
          @focus="onFieldFocus(f)"
        />
        <p v-if="f.help" class="tc-field-help">{{ f.help }}</p>
      </div>
      <div class="tc-actions">
        <button class="tc-save-btn" :disabled="saving" @click="save">
          {{ saving ? $t('common.saving') : $t('common.save') }}
        </button>
        <button class="tc-ping-btn" :disabled="pinging" @click="ping">
          {{ pinging ? $t('common.test') + '...' : pingResult || $t('settings.testConnection') }}
        </button>
      </div>
      <p v-if="hasAttributionNote" class="tc-attribution-note">
        {{ attributionNoteText }}
        <router-link :to="{ name: 'portal-credits' }" target="_blank" rel="noopener">
          {{ $t('attribution.settings.linkText') }}
        </router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { useToolCard } from '@/composables/useToolCard'
import { KeyRound } from 'lucide-vue-next'

const props = defineProps({
  toolKey: String,
  def: Object,
  cfg: Object,
  isMedia: Boolean,
})
const emit = defineEmits(['toggle', 'save'])

const {
  open,
  saving,
  pinging,
  pingResult,
  hasAttributionNote,
  attributionNoteText,
  fieldPlaceholder,
  displayValue,
  inputType,
  onFieldFocus,
  onFieldInput,
  save,
  ping,
} = useToolCard(props, emit)
</script>

<style scoped>
.tc {
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: border-color var(--duration-base);
}
.tc.active {
  border-color: var(--accent-500);
}

.tc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.tc.active .tc-header {
  background: rgb(var(--accent-rgb), 0.08);
}
.tc-header:hover {
  background: var(--bg-secondary);
}
.tc.active .tc-header:hover {
  background: rgb(var(--accent-rgb), 0.12);
}

.tc-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tc-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
  flex-shrink: 0;
}
.tc-icon-fallback {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  color: var(--text-muted);
}
.tc-label {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.tc-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tc-status {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.tc-status.on {
  color: var(--color-success);
}
.tc-status.off {
  color: var(--text-muted);
}

.tc-switch {
  position: relative;
  cursor: pointer;
}
.tc-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.tc-switch-track {
  width: 38px;
  height: 20px;
  border-radius: var(--radius-pill);
  background: var(--bg-primary);
  border: 1px solid var(--border);
  position: relative;
  transition: all var(--duration-base);
}
.tc-switch-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: all var(--duration-base);
}
.tc-switch input:checked + .tc-switch-track {
  background: var(--accent-500);
  border-color: var(--accent-500);
}
.tc-switch input:checked + .tc-switch-track::after {
  left: 21px;
}

.tc-body {
  padding: 16px;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tc-field-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: 5px;
}
.tc-field-help {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.4;
}
.tc-input {
  width: 100%;
  padding: 8px 12px;
  border-radius: var(--radius-btn);
  border: 1px solid var(--border);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--text-sm);
  outline: none;
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}
.tc-input:focus {
  border-color: var(--accent-500);
}

.tc-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.tc-save-btn {
  padding: 8px 18px;
  border-radius: var(--radius-btn);
  background: var(--accent-600);
  color: var(--text-primary);
  border: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.tc-save-btn:hover {
  background: var(--accent-700);
}
.tc-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tc-ping-btn {
  padding: 8px 14px;
  border-radius: var(--radius-btn);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.tc-ping-btn:hover {
  border-color: var(--accent-500);
  color: var(--text-primary);
}
.tc-ping-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tc-attribution-note {
  margin: 8px 0 0;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  line-height: 1.45;
}
.tc-attribution-note a {
  color: var(--accent-500);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
