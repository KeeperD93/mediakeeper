<template>
  <div class="doub-card">
    <div class="doub-poster">
      <img
        v-if="item.poster"
        :src="item.poster"
        class="doub-poster-img"
        @error="e => (e.target.style.display = 'none')"
      />
      <div v-else class="doub-poster-ph"><Film class="w-8 h-8" :stroke-width="1.5" /></div>
      <span v-if="item.year" class="doub-year">{{ item.year }}</span>
    </div>
    <div class="doub-info">
      <div class="doub-info-header">
        <div>
          <h3 class="doub-title">{{ item.title }}</h3>
          <p class="doub-versions">
            {{ item.sources.length }} {{ $t('duplicates.versions') }} · {{ reclaimableFor(item) }}
            {{ $t('duplicates.reclaimable') }}
          </p>
        </div>
        <div class="doub-info-btns">
          <button
            v-if="bestSource(item)"
            class="doub-suggest-btn"
            :title="$t('duplicates.keepBest')"
            @click="emit('keep', item, bestSource(item))"
          >
            <Zap class="ic-sm" />
            {{ $t('duplicates.keepBestBtn') }}
          </button>
          <button
            class="doub-compare-btn"
            :class="{ active: isCompareOpen }"
            @click="emit('toggle-compare', item.id)"
          >
            <Files class="ic-sm" />
            {{ $t('duplicates.compare') }}
          </button>
          <button class="doub-ignore-btn" @click="emit('ignore', item)">
            <EyeOff class="ic-sm" />
            {{ $t('duplicates.ignore') }}
          </button>
        </div>
      </div>

      <!-- Compare panel -->
      <div v-if="isCompareOpen" class="doub-compare">
        <table class="cmp-table">
          <thead>
            <tr>
              <th>{{ $t('duplicates.file') }}</th>
              <th>{{ $t('duplicates.resolution') }}</th>
              <th>{{ $t('duplicates.codec') }}</th>
              <th>{{ $t('duplicates.size') }}</th>
              <th>{{ $t('duplicates.score') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(src, si) in item.sources"
              :key="si"
              :class="{ 'cmp-best': isBest(item, src) }"
            >
              <td class="cmp-file" :title="src.name">{{ src.name }}</td>
              <td>{{ src.resolution }}</td>
              <td>{{ src.codec }}</td>
              <td>{{ src.size_label }}</td>
              <td>
                <span class="cmp-score" :style="{ color: scoreColor(srcScore(src)) }">
                  {{ srcScore(src) }}
                </span>
              </td>
              <td class="cmp-actions">
                <button class="doub-keep-btn" @click="emit('keep', item, src)">
                  {{ $t('duplicates.keep') }}
                </button>
                <button class="doub-delete-btn" @click="emit('delete', item, src)">
                  {{ $t('duplicates.delete') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Sources (default view) -->
      <div v-else class="doub-sources">
        <div
          v-for="(src, si) in item.sources"
          :key="si"
          class="doub-source"
          :class="{ 'doub-source-best': isBest(item, src) }"
        >
          <div class="doub-source-info">
            <p class="doub-filename" :title="src.name">{{ src.name }}</p>
            <div class="doub-tags">
              <span class="doub-tag">{{ src.resolution || 'N/A' }}</span>
              <span class="doub-tag">{{ src.codec || 'N/A' }}</span>
              <span class="doub-tag">{{ src.size_label || '0 Mo' }}</span>
              <span v-if="isBest(item, src)" class="doub-tag doub-tag-best">
                ★ {{ $t('duplicates.best') }}
              </span>
            </div>
          </div>
          <div class="doub-source-acts">
            <button class="doub-keep-btn" @click="emit('keep', item, src)">
              {{ $t('duplicates.keep') }}
            </button>
            <button class="doub-delete-btn" @click="emit('delete', item, src)">
              {{ $t('duplicates.deleteFile') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { EyeOff, Files, Film, Zap } from 'lucide-vue-next'
import { bestSource, isBest, reclaimableFor, scoreColor, srcScore } from '@/utils/duplicates'

defineProps({
  item: { type: Object, required: true },
  isCompareOpen: { type: Boolean, default: false },
})
const emit = defineEmits(['keep', 'delete', 'ignore', 'toggle-compare'])
</script>
