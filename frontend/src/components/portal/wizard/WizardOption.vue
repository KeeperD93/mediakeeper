<template>
  <label class="wz-opt" :class="{ 'is-on': checked, 'is-off': disabled }">
    <input
      class="wz-radio"
      type="radio"
      :name="name"
      :checked="checked"
      :disabled="disabled"
      @change="$emit('pick')"
    />
    <span class="dd-grow">
      <span class="wz-ot">
        <slot name="icon" />
        {{ label }}
        <span v-if="badge" class="wz-rec">{{ badge }}</span>
      </span>
      <span class="wz-oh" :lang="hintLang || undefined">{{ hint }}</span>
    </span>
  </label>
</template>

<script setup>
// A choice card of a radio group (language, visibility, image): a real radio inside.
defineProps({
  name: { type: String, required: true },
  label: { type: String, required: true },
  hint: { type: String, required: true },
  checked: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  badge: { type: String, default: '' },
  // Language of the hint when it is not the page's (each language describes itself).
  hintLang: { type: String, default: '' },
})
defineEmits(['pick'])
</script>
