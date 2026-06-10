<template>
  <span
    class="mk-col-rsz"
    role="separator"
    aria-orientation="vertical"
    @pointerdown="$emit('start', index, $event)"
    @click.stop
  />
</template>

<script setup>
// Drag handle for resizable table columns. Pair with the useColumnResize
// composable: drop one inside each resizable <th> (which must be position:
// relative) and bind @start to the composable's startResize.
defineProps({ index: { type: Number, required: true } })
defineEmits(['start'])
</script>

<style scoped>
.mk-col-rsz {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 1;
  width: 9px;
  height: 100%;
  cursor: col-resize;
  touch-action: none;
}
/* The thin visible bar between columns; brightens to the accent on hover. */
.mk-col-rsz::after {
  content: '';
  position: absolute;
  top: 20%;
  right: 4px;
  width: 1px;
  height: 60%;
  background: var(--border-strong);
  transition: background var(--duration-fast);
}
@media (hover: hover) {
  .mk-col-rsz:hover::after {
    width: 2px;
    background: var(--accent-500);
  }
}
</style>
