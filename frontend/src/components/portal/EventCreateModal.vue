<template>
  <Teleport to="body">
    <div class="pt-evc-overlay">
      <div class="pt-evc">
        <header class="pt-evc-head">
          <h2>{{ $t('portal.mkEvents.create.title') }}</h2>
          <button class="pt-evc-x" :aria-label="$t('common.close')" @click="$emit('close')">
            <X :size="20" :stroke-width="2.5" />
          </button>
        </header>

        <div class="pt-evc-body">
          <!-- Kind -->
          <div class="pt-evc-field">
            <label class="pt-evc-label">{{ $t('portal.mkEvents.create.kind') }}</label>
            <div class="pt-evc-toggle">
              <button
                type="button"
                :class="[
                  'pt-evc-toggle-btn',
                  { 'pt-evc-toggle-btn--active': kind === EVENT_KIND.PRIVATE },
                ]"
                @click="kind = EVENT_KIND.PRIVATE"
              >
                🔒 {{ $t('portal.mkEvents.create.private') }}
              </button>
              <button
                type="button"
                :class="[
                  'pt-evc-toggle-btn',
                  { 'pt-evc-toggle-btn--active': kind === EVENT_KIND.PUBLIC },
                ]"
                @click="kind = EVENT_KIND.PUBLIC"
              >
                🌍 {{ $t('portal.mkEvents.create.public') }}
              </button>
            </div>
          </div>

          <div class="pt-evc-field">
            <label class="pt-evc-label">{{ $t('portal.mkEvents.create.titleField') }}</label>
            <input
              v-model="title"
              type="text"
              maxlength="200"
              class="pt-evc-input"
              :placeholder="$t('portal.mkEvents.create.titlePlaceholder')"
            />
          </div>

          <!-- Media search + selected list -->
          <div class="pt-evc-field">
            <label class="pt-evc-label">
              {{ $t('portal.mkEvents.create.media') }}
              <span v-if="selectedMedia.length > 1" class="pt-evc-marathon">
                {{ $t('portal.mkEvents.create.marathonHint', { n: selectedMedia.length }) }}
              </span>
            </label>
            <div class="pt-evc-search">
              <input
                v-model="mediaQuery"
                type="text"
                :placeholder="$t('portal.mkEvents.create.mediaPlaceholder')"
                class="pt-evc-input"
                @input="onMediaInput"
              />
              <div v-if="mediaResults.length" class="pt-evc-search-results">
                <button
                  v-for="r in mediaResults.slice(0, 8)"
                  :key="`${r.media_type}-${r.tmdb_id || r.id}`"
                  type="button"
                  class="pt-evc-result"
                  @click="addMedia(r)"
                >
                  <img
                    v-if="r.poster_url"
                    :src="r.poster_url"
                    :alt="r.title"
                    class="pt-evc-result-poster"
                  />
                  <div class="pt-evc-result-info">
                    <div class="pt-evc-result-title">{{ r.title }}</div>
                    <div class="pt-evc-result-meta">
                      {{ isTv(r) ? $t('portal.card.series') : $t('portal.card.movie') }}
                      <span v-if="r.year">· {{ r.year }}</span>
                    </div>
                  </div>
                </button>
              </div>
            </div>
            <div v-if="selectedMedia.length" class="pt-evc-selected">
              <div
                v-for="(m, i) in selectedMedia"
                :key="`${m.media_type}-${m.tmdb_id}`"
                class="pt-evc-chip"
                draggable="true"
                @dragstart="onDragStart(i, $event)"
                @dragover.prevent
                @drop="onDrop(i)"
              >
                <span class="pt-evc-chip-num">{{ i + 1 }}</span>
                <img v-if="m.poster_url" :src="m.poster_url" class="pt-evc-chip-poster" />
                <span class="pt-evc-chip-title">{{ m.title }}</span>
                <button type="button" class="pt-evc-chip-x" @click="removeMedia(i)">×</button>
              </div>
            </div>
          </div>

          <!-- Datetime -->
          <div class="pt-evc-row">
            <div class="pt-evc-field">
              <label class="pt-evc-label">{{ $t('portal.mkEvents.create.date') }}</label>
              <input v-model="date" type="date" class="pt-evc-input" :min="todayISO" />
            </div>
            <div class="pt-evc-field">
              <label class="pt-evc-label">{{ $t('portal.mkEvents.create.time') }}</label>
              <input v-model="time" type="time" class="pt-evc-input" />
            </div>
          </div>

          <!-- Invitees (private only) -->
          <div v-if="kind === EVENT_KIND.PRIVATE" class="pt-evc-field">
            <label class="pt-evc-label">{{ $t('portal.mkEvents.create.invitees') }}</label>
            <div class="pt-evc-search">
              <input
                v-model="userQuery"
                type="text"
                :placeholder="$t('portal.mkEvents.create.inviteesPlaceholder')"
                class="pt-evc-input"
                @input="onUserInput"
              />
              <div v-if="userResults.length" class="pt-evc-search-results">
                <button
                  v-for="u in userResults"
                  :key="u.id"
                  type="button"
                  class="pt-evc-result"
                  @click="addUser(u)"
                >
                  <MkAvatar
                    :src="u.avatar_url"
                    :name="u.display_name || ''"
                    :size="24"
                    :tier="u.tier || 'bronze'"
                  />
                  <span>{{ u.display_name }}</span>
                </button>
              </div>
            </div>
            <div v-if="selectedUsers.length" class="pt-evc-users">
              <div v-for="u in selectedUsers" :key="u.id" class="pt-evc-user-chip">
                <MkAvatar
                  :src="u.avatar_url"
                  :name="u.display_name || ''"
                  :size="18"
                  :tier="u.tier || 'bronze'"
                />
                {{ u.display_name }}
                <button type="button" class="pt-evc-chip-x" @click="removeUser(u.id)">×</button>
              </div>
            </div>
          </div>

          <!-- Capacity (public only — private rooms size themselves to the invitees) -->
          <div v-if="kind === EVENT_KIND.PUBLIC" class="pt-evc-field">
            <label class="pt-evc-label">
              {{ $t('portal.mkEvents.create.capacity') }}
            </label>
            <div class="pt-evc-capacity-row">
              <button
                v-for="opt in capacityOptions"
                :key="`cap-${opt}`"
                type="button"
                :class="[
                  'pt-evc-capacity-chip',
                  { 'pt-evc-capacity-chip--active': maxParticipants === opt },
                ]"
                @click="maxParticipants = opt"
              >
                {{ opt }}
              </button>
            </div>
            <p class="pt-evc-hint">
              {{ $t('portal.mkEvents.create.capacityHint') }}
            </p>
          </div>

          <!-- Comment -->
          <div class="pt-evc-field">
            <label class="pt-evc-label">{{ $t('portal.mkEvents.create.comment') }}</label>
            <textarea
              v-model="comment"
              rows="3"
              maxlength="2000"
              :placeholder="$t('portal.mkEvents.create.commentPlaceholder')"
              class="pt-evc-input pt-evc-textarea"
            ></textarea>
          </div>

          <div v-if="error" class="pt-evc-error">{{ error }}</div>
        </div>

        <footer class="pt-evc-footer">
          <button class="pt-evc-btn pt-evc-btn--ghost" @click="$emit('close')">
            {{ $t('common.cancel') }}
          </button>
          <button
            class="pt-evc-btn pt-evc-btn--primary"
            :disabled="!canSubmit || submitting"
            @click="submit"
          >
            {{ submitting ? $t('common.loading') : $t('portal.mkEvents.create.submit') }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { useEventCreateModal } from './useEventCreateModal.js'
import { EVENT_KIND } from '@/constants/events'
import { isTv } from '@/constants/media'
import MkAvatar from '@/components/common/MkAvatar.vue'
import { X } from 'lucide-vue-next'

import '@/assets/styles/portal/event-create-modal.css'

const emit = defineEmits(['close', 'created'])

const {
  kind,
  title,
  date,
  time,
  comment,
  mediaQuery,
  mediaResults,
  selectedMedia,
  userQuery,
  userResults,
  selectedUsers,
  error,
  submitting,
  todayISO,
  canSubmit,
  onMediaInput,
  addMedia,
  removeMedia,
  onDragStart,
  onDrop,
  onUserInput,
  addUser,
  removeUser,
  submit,
  maxParticipants,
  capacityOptions,
} = useEventCreateModal(emit)
</script>
