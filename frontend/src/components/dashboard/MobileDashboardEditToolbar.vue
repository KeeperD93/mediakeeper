<template>
  <Teleport to="body">
    <div class="m-dash-toolbar" role="toolbar">
      <span class="m-dash-toolbar__label">{{ $t('dashboard.mobileReorderTitle') }}</span>
      <div class="m-dash-toolbar__actions">
        <button type="button" class="m-dash-toolbar__btn" @click="$emit('cancel')">
          {{ $t('dashboard.mobileReorderCancel') }}
        </button>
        <button
          type="button"
          class="m-dash-toolbar__btn m-dash-toolbar__btn--primary"
          @click="$emit('confirm')"
        >
          {{ $t('dashboard.mobileReorderDone') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import '@/assets/styles/dashboard/mobile-dashboard.css'

defineEmits(['cancel', 'confirm'])
</script>
