<template>
  <Teleport to="body">
    <transition name="sub-fade">
      <div v-if="detail" class="so-overlay hc-issue-overlay" @click.self="$emit('close')">
        <div class="so-modal so-solid">
          <div class="so-header">
            <img
              :src="`/api/emby/image/${detail.item_id}?type=Primary`"
              class="so-poster"
              alt=""
              @error="$event.target.style.display = 'none'"
            />
            <div class="so-header-info">
              <h2 class="so-title">{{ detail.title }}</h2>
              <span class="so-count">
                {{ detail.issueCount }} {{ $t('healthCheck.issues_count') }}
              </span>
              <span v-if="detail.library" class="so-count so-count-sep">
                · {{ detail.library }}
              </span>
            </div>
            <button class="so-close" @click="$emit('close')">
              <X :size="16" />
            </button>
          </div>

          <div class="so-episodes">
            <template v-if="detail.seasons && detail.seasons.length">
              <template v-for="s in detail.seasons" :key="s.num">
                <div class="so-season-header" @click="s.open = !s.open">
                  <ChevronDown
                    :class="{ 'so-chev-open': s.open }"
                    class="so-season-chev"
                    :size="14"
                    :stroke-width="2.5"
                  />
                  <span class="so-season-label">{{ $t('healthCheck.season') }} {{ s.num }}</span>
                  <div class="so-ep-pills">
                    <span
                      v-for="tg in s.allTags"
                      :key="tg.type"
                      class="hc-issue-tag"
                      :class="'hc-it-' + tg.severity"
                      :data-tooltip="tagTooltip(tg)"
                    >
                      {{ tagText(tg) }}
                    </span>
                  </div>
                </div>
                <template v-if="s.open">
                  <div v-for="ep in s.episodes" :key="ep.id" class="so-ep-row so-ep-indent">
                    <span class="so-ep-tag">
                      E{{ String(ep.episode_num || '?').padStart(2, '0') }}
                    </span>
                    <span class="so-ep-name">{{ ep.item_name }}</span>
                    <div class="so-ep-pills">
                      <span
                        v-for="(iss, idx) in ep.issues"
                        :key="idx"
                        class="hc-issue-tag"
                        :class="'hc-it-' + iss.severity"
                        :data-tooltip="tagTooltip(iss)"
                      >
                        {{ tagText(iss) }}
                      </span>
                    </div>
                  </div>
                </template>
              </template>
            </template>
            <template v-else>
              <div class="hc-movie-tags">
                <span
                  v-for="(iss, idx) in detail.allIssues || []"
                  :key="idx"
                  class="hc-issue-tag"
                  :class="'hc-it-' + iss.severity"
                  :data-tooltip="tagTooltip(iss)"
                >
                  {{ tagText(iss) }}
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { ChevronDown, X } from 'lucide-vue-next'

const props = defineProps({ item: { type: Object, default: null } })
defineEmits(['close'])

const { t } = useI18n()
const { apiGet } = useApi()

const SEV_RANK = { critical: 3, warning: 2, info: 1, ok: 0 }
const detail = ref(null)

function tagText(iss) {
  return iss.detail || t('healthCheck.issues.' + iss.type)
}
function tagTooltip(iss) {
  return t('healthCheck.issues.' + iss.type)
}

async function build(item) {
  if (!item) {
    detail.value = null
    return
  }
  const kind = item.is_series ? 'series' : 'movie'
  const key = encodeURIComponent(item.is_series ? item.item_id || item.title : item.item_id)
  let rows = []
  try {
    const d = await apiGet(`/api/healthcheck/poster/${kind}/${key}`)
    rows = d?.items || []
  } catch {
    /* silent: poster detail fetch, overlay stays empty */
  }

  if (item.is_series) {
    const seasonMap = new Map()
    for (const ep of rows) {
      const num = ep.season_num || 1
      if (!seasonMap.has(num)) seasonMap.set(num, { num, open: false, episodes: [], allTags: [] })
      seasonMap.get(num).episodes.push(ep)
    }
    for (const s of seasonMap.values()) {
      const tagSet = new Map()
      for (const ep of s.episodes) {
        for (const iss of ep.issues || []) {
          if (
            !tagSet.has(iss.type) ||
            (SEV_RANK[iss.severity] || 0) > (SEV_RANK[tagSet.get(iss.type).severity] || 0)
          ) {
            tagSet.set(iss.type, iss)
          }
        }
      }
      s.allTags = [...tagSet.values()]
      s.episodes.sort((a, b) => (a.episode_num || 0) - (b.episode_num || 0))
    }
    const seasons = [...seasonMap.values()].sort((a, b) => a.num - b.num)
    detail.value = { ...item, seasons, episodes: rows }
  } else {
    const allIssues = rows.flatMap(r => r.issues || [])
    detail.value = { ...item, allIssues }
  }
}

watch(() => props.item, build, { immediate: true })
</script>

<style scoped>
.so-overlay {
  position: fixed;
  inset: 0;
  z-index: 9990;
  background: rgb(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}
.so-modal {
  width: 680px;
  max-width: 95vw;
  max-height: 85vh;
  overflow-y: auto;
  padding: 0;
  border-radius: 16px;
}
.so-solid {
  background: var(--bg-secondary);
  border: 1px solid var(--border-strong);
  border-radius: 14px;
}
.so-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
}
.so-poster {
  width: 48px;
  height: 72px;
  border-radius: var(--radius-btn);
  object-fit: cover;
  flex-shrink: 0;
}
.so-header-info {
  flex: 1;
  min-width: 0;
}
.so-title {
  font-size: var(--text-md);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
}
.so-count {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.so-count-sep {
  margin-left: 8px;
}
.so-close {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-btn);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.so-close:hover {
  background: rgb(244, 63, 94, 0.1);
  color: #fb7185;
}
.so-episodes {
  padding: 8px 12px;
}
.so-season-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 0.5px solid var(--border-default);
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
  color: var(--text-primary);
  transition: background var(--duration-fast);
}
.so-season-header:hover {
  background: rgb(255, 255, 255, 0.03);
}
.so-season-label {
  flex-shrink: 0;
}
.so-season-chev {
  transition: transform var(--duration-base);
  flex-shrink: 0;
  color: var(--text-muted);
}
.so-chev-open {
  transform: rotate(180deg);
}
.so-ep-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-input);
  transition: background var(--duration-fast);
  border-bottom: 0.5px solid rgb(255, 255, 255, 0.03);
}
.so-ep-row:last-child {
  border-bottom: none;
}
.so-ep-indent {
  padding-left: 28px;
}
.so-ep-tag {
  font-size: var(--text-3xs);
  font-weight: var(--font-bold);
  font-family: 'Space Mono', monospace;
  color: var(--accent-300);
  min-width: 34px;
}
.so-ep-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.so-ep-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex-shrink: 0;
}
.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity var(--duration-base);
}
.sub-fade-enter-from,
.sub-fade-leave-to {
  opacity: 0;
}

.hc-movie-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 16px 20px;
}
.hc-issue-tag {
  font-size: var(--text-3xs);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  font-weight: var(--font-bold);
  position: relative;
  cursor: help;
}
.hc-issue-tag[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  padding: 5px 9px;
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  color: #fff;
  background: rgb(15, 15, 25, 0.96);
  border: 1px solid rgb(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition:
    opacity var(--duration-fast) ease,
    transform var(--duration-fast) ease;
  z-index: 20;
  box-shadow: 0 6px 20px rgb(0, 0, 0, 0.5);
}
.hc-issue-tag[data-tooltip]::before {
  content: '';
  position: absolute;
  bottom: calc(100% + 1px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  border: 5px solid transparent;
  border-top-color: rgb(15, 15, 25, 0.96);
  pointer-events: none;
  opacity: 0;
  transition:
    opacity var(--duration-fast) ease,
    transform var(--duration-fast) ease;
  z-index: 20;
}
.hc-issue-tag[data-tooltip]:hover::after,
.hc-issue-tag[data-tooltip]:hover::before {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
.hc-it-critical {
  background: rgb(244, 63, 94, 0.12);
  color: #fb7185;
  border: 1px solid rgb(244, 63, 94, 0.15);
}
.hc-it-warning {
  background: rgb(var(--color-warning-rgb), 0.12);
  color: var(--color-warning);
  border: 1px solid rgb(var(--color-warning-rgb), 0.15);
}
.hc-it-info {
  background: rgb(var(--color-info-rgb), 0.12);
  color: var(--color-info);
  border: 1px solid rgb(var(--color-info-rgb), 0.15);
}
</style>
