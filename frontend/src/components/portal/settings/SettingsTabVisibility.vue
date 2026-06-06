<template>
  <div class="pt-settings-card">
    <h3 class="pt-settings-section-title">{{ $t('portal.settings.visibility.profileSection') }}</h3>

    <div class="pt-settings-radios">
      <label class="pt-settings-radio" :class="{ 'pt-settings-radio--on': form.is_public }">
        <input
          type="radio"
          :value="true"
          :checked="form.is_public"
          :disabled="visibilityLocked"
          @change="updateField('is_public', true)"
        />
        <span class="pt-settings-radio-title">
          <Globe :size="14" />
          {{ $t('portal.settings.visibility.public') }}
        </span>
        <span class="pt-settings-radio-hint">
          {{ $t('portal.settings.visibility.publicHint') }}
        </span>
      </label>

      <label class="pt-settings-radio" :class="{ 'pt-settings-radio--on': !form.is_public }">
        <input
          type="radio"
          :value="false"
          :checked="!form.is_public"
          :disabled="visibilityLocked"
          @change="updateField('is_public', false)"
        />
        <span class="pt-settings-radio-title">
          <Lock :size="14" />
          {{ $t('portal.settings.visibility.private') }}
        </span>
        <span class="pt-settings-radio-hint">
          {{ $t('portal.settings.visibility.privateHint') }}
        </span>
      </label>
    </div>

    <p v-if="visibilityLocked" class="pt-settings-hint">
      {{ $t('portal.settings.visibility.publicLocked') }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Globe, Lock } from 'lucide-vue-next'

const props = defineProps({
  form: { type: Object, required: true },
  profileData: { type: Object, default: null },
})
const emit = defineEmits(['update-field'])

const visibilityLocked = computed(() => !!props.profileData?.forced_public)

function updateField(key, value) {
  emit('update-field', key, value)
}
</script>
