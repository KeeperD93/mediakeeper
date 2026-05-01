<template>
  <div class="params-appearance-tab">
    <h2 class="params-title">{{ $t('settings.appearance') }}</h2>
    <p class="params-desc">{{ $t('settings.appearanceDesc') }}</p>

    <section class="params-section params-section-full">
      <h3 class="params-section-title">{{ $t('topbar.accent') }}</h3>
      <div class="params-accent-grid">
        <button v-for="preset in accentPresets" :key="preset.name"
          class="params-accent-btn"
          :class="{ active: preset.name === accentName }"
          :style="{ '--dot-color': preset.color }"
          @click="setAccent(preset.name)">
          <span class="accent-dot" :style="{ background: preset.color }" />
          <span class="accent-name">{{ preset.name }}</span>
          <Check v-if="preset.name === accentName" :size="11" :stroke-width="3" />
        </button>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.radiusLabel') }}</h3>
      <p class="params-section-desc">{{ $t('settings.radiusDesc') }}</p>
      <div class="params-slider-row">
        <span class="params-slider-icon">▢</span>
        <input type="range" min="0" max="24" step="2"
          :value="borderRadius"
          class="params-slider"
          @input="setRadius(+$event.target.value)" />
        <span class="params-slider-icon">⬜</span>
        <span class="params-slider-val">{{ borderRadius }}px</span>
      </div>
      <div class="params-radius-preview">
        <div class="radius-demo-card" :style="{ borderRadius: borderRadius + 'px' }">
          <div class="radius-demo-bar" :style="{ borderRadius: Math.max(0, borderRadius - 2) + 'px' }" />
          <div class="radius-demo-line" />
        </div>
        <div class="radius-demo-btn" :style="{ borderRadius: Math.max(4, borderRadius - 4) + 'px' }">
          {{ $t('settings.buttonPreview') }}
        </div>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.bgLabel') }}</h3>
      <p class="params-section-desc">{{ $t('settings.bgDesc') }}</p>
      <div class="params-bg-upload"
        :class="{ 'has-bg': customBg }"
        @dragover.prevent @drop.prevent="onBgDrop($event)">
        <div v-if="customBg" class="params-bg-preview">
          <img :src="customBg" class="params-bg-thumb" />
          <button class="params-bg-clear" @click="clearCustomBg">
            <X :size="12" />
          </button>
        </div>
        <label v-else class="params-bg-label">
          <input type="file" accept="image/*" class="params-bg-input" @change="onBgFile($event)" />
          <Image :size="24" :stroke-width="1.5" />
          <span>{{ $t('settings.bgUpload') }}</span>
        </label>
      </div>

      <div v-if="customBg" class="params-bg-controls">
        <div class="params-bg-ctrl">
          <label class="params-bg-ctrl-label">{{ $t('settings.bgOpacity') }} — {{ Math.round(customBgOpacity * 100) }}%</label>
          <input type="range" min="0.05" max="0.5" step="0.05"
            :value="customBgOpacity"
            class="params-slider"
            @input="setCustomBg(customBg, +$event.target.value, customBgBlur)" />
        </div>
        <div class="params-bg-ctrl">
          <label class="params-bg-ctrl-label">{{ $t('settings.bgBlur') }} — {{ customBgBlur }}px</label>
          <input type="range" min="0" max="40" step="2"
            :value="customBgBlur"
            class="params-slider"
            @input="setCustomBg(customBg, customBgOpacity, +$event.target.value)" />
        </div>
      </div>
    </section>

    <section class="params-section">
      <h3 class="params-section-title">{{ $t('settings.glowLabel') }}</h3>
      <p class="params-section-desc">{{ $t('settings.glowDesc') }}</p>
      <div class="params-slider-row">
        <span class="params-slider-icon">◌</span>
        <input type="range" min="0" max="2" step="0.05"
          :value="glowIntensity"
          class="params-slider"
          @input="setGlowIntensity(+$event.target.value)" />
        <span class="params-slider-icon">◉</span>
        <span class="params-slider-val">{{ Math.round(glowIntensity * 100) }}%</span>
      </div>
      <div class="params-glow-preview">
        <button type="button" class="glow-demo-btn">{{ $t('common.preview') }}</button>
      </div>
    </section>

    <section class="params-section">
      <div class="params-toggle-row">
        <div>
          <h3 class="params-section-title params-section-title-tight">{{ $t('settings.particlesLabel') }}</h3>
          <p class="params-section-desc">{{ $t('settings.particlesDesc') }}</p>
        </div>
        <label class="params-switch">
          <input type="checkbox" :checked="particlesEnabled" @change="setParticles($event.target.checked)" />
          <span class="params-switch-slider" />
        </label>
      </div>
    </section>

    <div class="params-save-row">
      <button class="params-save-btn" :class="{ saved }" :disabled="saving" @click="handleSave">
        <Check v-if="saved" :size="15" :stroke-width="2.5" />
        <Save v-else-if="!saving" :size="15" />
        <MkSpinner v-else size="sm" inline />
        {{ saved ? $t('settings.saved') : $t('settings.save') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { Check, Image, Save, X } from 'lucide-vue-next'
import MkSpinner from '@/components/common/MkSpinner.vue'
import '@/assets/styles/params-appearance.css'

const {
  accentName, accentPresets, setAccent,
  borderRadius, setRadius,
  customBg, customBgOpacity, customBgBlur, setCustomBg, clearCustomBg,
  particlesEnabled, setParticles,
  glowIntensity, setGlowIntensity,
  saveAll,
} = useTheme()

const saving = ref(false)
const saved = ref(false)

async function handleSave() {
  saving.value = true
  saveAll()
  await new Promise(r => setTimeout(r, 600))
  saving.value = false
  saved.value = true
  setTimeout(() => { saved.value = false }, 2500)
}

function resizeImageForBg(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const MAX = 800
      let w = img.width, h = img.height
      if (w > MAX || h > MAX) {
        const ratio = Math.min(MAX / w, MAX / h)
        w = Math.round(w * ratio)
        h = Math.round(h * ratio)
      }
      const cvs = document.createElement('canvas')
      cvs.width = w; cvs.height = h
      cvs.getContext('2d').drawImage(img, 0, 0, w, h)
      resolve(cvs.toDataURL('image/jpeg', 0.7))
    }
    img.onerror = () => resolve(dataUrl)
    img.src = dataUrl
  })
}

function onBgFile(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (ev) => {
    const resized = await resizeImageForBg(ev.target.result)
    setCustomBg(resized, customBgOpacity.value, customBgBlur.value)
  }
  reader.readAsDataURL(file)
}

function onBgDrop(e) {
  const file = e.dataTransfer.files[0]
  if (!file || !file.type.startsWith('image/')) return
  const reader = new FileReader()
  reader.onload = async (ev) => {
    const resized = await resizeImageForBg(ev.target.result)
    setCustomBg(resized, customBgOpacity.value, customBgBlur.value)
  }
  reader.readAsDataURL(file)
}
</script>
