<template>
  <div class="ql-link" :class="{ 'ql-no-click': editing }" @click="onClick">
    <div class="ql-icon" :style="{ background: iconBg }">
      <slot name="icon" />
    </div>
    <div class="ql-text">
      <template v-if="isLoading">
        <div class="ql-skel ql-skel-title" />
        <div class="ql-skel ql-skel-sub" />
      </template>
      <template v-else>
        <span class="ql-main">{{ title }}</span>
        <span class="ql-sub">{{ subtitle }}</span>
      </template>
    </div>
    <span v-if="!isLoading" class="ql-arrow">→</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  route: { type: String, required: true },
  iconBg: { type: String, default: 'rgba(99,102,241,0.12)' },
  editing: { type: Boolean, default: false },
})

const router = useRouter()
const isLoading = computed(() => props.title === '—' || props.title === '')

function onClick() {
  if (props.editing) return
  router.push(props.route)
}
</script>

<style scoped>
.ql-link {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 100%;
  background: var(--card-bg, rgb(255, 255, 255, 0.03));
  border-radius: var(--radius-card);
  padding: 14px 18px;
  border: 0.5px solid var(--card-border, rgb(255, 255, 255, 0.05));
  cursor: pointer;
  transition:
    border-color var(--duration-base),
    box-shadow var(--duration-slow);
}
.ql-link:hover {
  border-color: var(--card-border-hover, rgb(99, 102, 241, 0.2));
  box-shadow: 0 0 20px rgb(99, 102, 241, 0.06);
}
.ql-no-click {
  cursor: move;
}
.ql-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ql-text {
  flex: 1;
  min-width: 0;
}
.ql-main {
  display: block;
  font-size: var(--text-base);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ql-sub {
  display: block;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: 2px;
}
.ql-arrow {
  font-size: var(--text-md);
  color: var(--text-muted);
  flex-shrink: 0;
}

/* Skeleton shimmer */
.ql-skel {
  border-radius: 5px;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.03) 25%,
    rgb(255, 255, 255, 0.07) 50%,
    rgb(255, 255, 255, 0.03) 75%
  );
  background-size: 200% 100%;
  animation: ql-shimmer var(--duration-animation) ease-in-out infinite;
}
.ql-skel-title {
  height: 14px;
  width: 65%;
}
.ql-skel-sub {
  height: 10px;
  width: 40%;
  margin-top: 6px;
}
@keyframes ql-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ql-link {
    transition: none;
  }
}
</style>
