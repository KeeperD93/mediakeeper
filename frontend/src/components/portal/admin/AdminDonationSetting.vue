<template>
  <section class="pt-don-section">
    <!-- Toggle persists immediately. Class names are local to this
         component: AdminSettings.vue's ``pt-setting-*`` rules live in a
         parent scoped block and would not bleed through Vue's hashing. -->
    <div class="pt-don-row">
      <div class="pt-don-info">
        <span class="pt-don-title">{{ $t('portal.admin.settings.donation.title') }}</span>
        <span class="pt-don-desc">{{ $t('portal.admin.settings.donation.desc') }}</span>
      </div>
      <MkToggle
        :model-value="enabled"
        :disabled="saving"
        :aria-label="$t('portal.admin.settings.donation.title')"
        @update:model-value="onToggle"
      />
    </div>

    <div v-if="enabled" class="pt-don-config">
      <div class="pt-don-field">
        <label class="pt-don-label" :for="urlId">
          {{ $t('portal.admin.settings.donation.urlLabel') }}
        </label>
        <input
          :id="urlId"
          v-model="url"
          type="url"
          class="pt-don-input"
          :placeholder="$t('portal.admin.settings.donation.urlPlaceholder')"
          maxlength="500"
        />
      </div>

      <div class="pt-don-field">
        <label class="pt-don-label" :for="msgId">
          {{ $t('portal.admin.settings.donation.messageLabel') }}
        </label>
        <textarea
          :id="msgId"
          v-model="message"
          class="pt-don-textarea"
          rows="3"
          maxlength="500"
          :placeholder="$t('portal.admin.settings.donation.messagePlaceholder')"
        />
      </div>

      <div class="pt-don-actions">
        <button type="button" class="pt-don-save" :disabled="saving" @click="onSave">
          <Save :size="14" />
          <span>{{ $t('common.save') }}</span>
        </button>
        <span v-if="savedMessage" class="pt-don-saved">{{ savedMessage }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save } from 'lucide-vue-next'
import MkToggle from '@/components/common/MkToggle.vue'
import { useDonationAdmin } from '@/composables/portal/useDonationAdmin'

const SAVED_MESSAGE_TIMEOUT_MS = 2000

const { t } = useI18n()
const { saving, fetchDonation, saveDonation } = useDonationAdmin()

const urlId = useId()
const msgId = useId()

const enabled = ref(false)
const url = ref('')
const message = ref('')
const savedMessage = ref('')
let savedTimer = null

function apply(cfg) {
  enabled.value = cfg.enabled
  url.value = cfg.url
  message.value = cfg.message
}

function flashSaved() {
  savedMessage.value = t('common.saved')
  if (savedTimer) clearTimeout(savedTimer)
  savedTimer = setTimeout(() => {
    savedMessage.value = ''
  }, SAVED_MESSAGE_TIMEOUT_MS)
}

async function onToggle(next) {
  enabled.value = next
  const res = await saveDonation({ 'donation.enabled': next })
  if (res) {
    apply(res)
    flashSaved()
  }
}

async function onSave() {
  const res = await saveDonation({
    'donation.url': url.value.trim(),
    'donation.message': message.value.trim(),
  })
  if (res) {
    apply(res)
    flashSaved()
  }
}

onMounted(async () => {
  apply(await fetchDonation())
})
</script>

<style scoped>
.pt-don-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.pt-don-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.pt-don-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}
.pt-don-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}
.pt-don-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.35;
}
.pt-don-config {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
.pt-don-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.pt-don-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.pt-don-input,
.pt-don-textarea {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  font-size: var(--text-sm);
  font-family: inherit;
}
.pt-don-textarea {
  resize: vertical;
}
.pt-don-input:focus,
.pt-don-textarea:focus {
  border-color: var(--accent);
  outline: none;
}
.pt-don-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.pt-don-save {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  background: var(--accent);
  color: var(--color-on-accent);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  cursor: pointer;
}
.pt-don-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.pt-don-saved {
  font-size: var(--text-xs);
  color: var(--accent);
}
</style>
