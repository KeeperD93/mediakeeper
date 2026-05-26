<template>
  <Teleport to="body">
    <div class="m-dash-toolbar" role="toolbar">
      <span class="m-dash-toolbar__label">{{ $t('dashboard.mobileReorderTitle') }}</span>
      <div class="m-dash-toolbar__actions">
        <MkButton variant="ghost" @click="$emit('cancel')">
          {{ $t('dashboard.mobileReorderCancel') }}
        </MkButton>
        <MkButton variant="primary" @click="$emit('confirm')">
          {{ $t('dashboard.mobileReorderDone') }}
        </MkButton>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import MkButton from '@/components/common/MkButton.vue'
import '@/assets/styles/dashboard/mobile-dashboard.css'

defineEmits(['cancel', 'confirm'])
</script>
