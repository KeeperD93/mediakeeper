<template>
  <div class="pt-parties">
    <div class="pt-parties-header">
      <h2>{{ $t('portal.parties.title') }}</h2>
      <button class="pt-btn pt-btn--primary" @click="showCreate = true">
        <i class="icon-plus" />
        {{ $t('portal.parties.create') }}
      </button>
    </div>

    <div class="pt-parties-grid">
      <div v-for="p in parties" :key="p.id" class="pt-party-card">
        <div class="pt-party-date">
          {{
            localizedDate(new Date(p.scheduled_at), {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            })
          }}
          <br />
          {{ localizedTime(new Date(p.scheduled_at), { hour: '2-digit', minute: '2-digit' }) }}
        </div>
        <div class="pt-party-info">
          <h3>{{ p.title }}</h3>
          <span class="pt-party-meta">
            {{ p.participant_count }}/{{ p.max_participants }}
            {{ $t('portal.parties.participants') }}
          </span>
        </div>
        <button class="pt-btn pt-btn--secondary" @click="join(p.id)">
          {{ $t('portal.parties.join') }}
        </button>
      </div>
      <div v-if="!parties.length" class="pt-empty">{{ $t('portal.parties.none') }}</div>
    </div>

    <Teleport v-if="showCreate" to="body">
      <div class="pt-popup-overlay" @click.self="showCreate = false">
        <div class="pt-popup pt-popup--md">
          <div class="pt-popup-header">
            <h2>{{ $t('portal.parties.create') }}</h2>
            <button
              class="pt-popup-close"
              type="button"
              :aria-label="$t('common.close')"
              @click="showCreate = false"
            >
              <X :size="14" />
            </button>
          </div>
          <div class="pt-popup-body">
            <label>{{ $t('portal.parties.partyTitle') }}</label>
            <input v-model="form.title" class="pt-input" maxlength="300" />
            <label>{{ $t('portal.parties.date') }}</label>
            <input v-model="form.scheduled_at" type="datetime-local" class="pt-input" />
            <label>{{ $t('portal.parties.maxParticipants') }}</label>
            <input
              v-model.number="form.max_participants"
              type="number"
              min="2"
              max="100"
              class="pt-input"
            />
          </div>
          <div class="pt-popup-footer">
            <button class="pt-btn pt-btn--primary" :disabled="!form.title.trim()" @click="submit">
              {{ $t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { usePortalEvents } from '@/composables/portal/usePortalEvents'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { localizedDate, localizedTime } from '@/utils/datetime'

const { parties, fetchParties, createParty, joinParty } = usePortalEvents()
const { showToast } = useToast()
const { t } = useI18n()
const showCreate = ref(false)
const form = reactive({ title: '', scheduled_at: '', max_participants: 20 })

async function submit() {
  await createParty({ ...form, scheduled_at: new Date(form.scheduled_at).toISOString() })
  showCreate.value = false
  showToast(t('common.success'), TOAST_TYPE.OK)
  await fetchParties()
}

async function join(id) {
  const res = await joinParty(id)
  if (res?.success) showToast(t('common.success'), TOAST_TYPE.OK)
  await fetchParties()
}

onMounted(() => fetchParties())
</script>

<style scoped>
.pt-parties {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
}
.pt-parties-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}
.pt-parties-header h2 {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-parties-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}
.pt-party-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
}
.pt-party-date {
  text-align: center;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  color: var(--portal-accent);
  min-width: 60px;
}
.pt-party-info {
  flex: 1;
}
.pt-party-info h3 {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-party-meta {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}
.pt-btn {
  padding: 0.45rem 1rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--portal-font-medium);
  cursor: pointer;
  font-size: var(--portal-text-xs);
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.pt-btn--primary {
  background: var(--portal-accent);
  color: var(--portal-text-primary);
}
.pt-btn--secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}
.pt-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem 0;
  grid-column: 1/-1;
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
  display: flex;
  flex-direction: column;
}
.pt-popup--md {
  max-width: 450px;
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
}
.pt-popup-body label {
  display: block;
  font-size: var(--portal-text-xs);
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
  font-size: var(--portal-text-sm);
}
.pt-popup-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
  text-align: right;
}
</style>
