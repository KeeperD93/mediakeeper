<template>
  <form class="pt-search" @submit.prevent="submitSearch">
    <label class="pt-search-shell">
      <Search class="pt-search-icon" :size="16" />

      <input
        ref="inputRef"
        v-model="query"
        class="pt-search-input"
        type="text"
        :placeholder="$t('portal.search.placeholder')"
        :aria-label="$t('portal.search.placeholder')"
      />

      <button
        class="pt-search-submit"
        type="submit"
        :title="$t('portal.search.submit')"
        :aria-label="$t('portal.search.submit')"
        :disabled="!trimmedQuery"
      >
        <ArrowRight :size="16" :stroke-width="2.2" />
      </button>
    </label>
  </form>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Search } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const inputRef = ref(null)
const query = ref('')

const trimmedQuery = computed(() => query.value.trim())

watch(
  () => route.query.q,
  value => {
    query.value = typeof value === 'string' ? value : ''
  },
  { immediate: true },
)

async function submitSearch() {
  if (!trimmedQuery.value) {
    inputRef.value?.focus()
    return
  }

  const target = {
    name: 'portal-search',
    query: { q: trimmedQuery.value },
  }

  if (route.name === 'portal-search' && route.query.q === trimmedQuery.value) {
    return
  }

  if (route.name === 'portal-search') {
    await router.replace(target)
    return
  }

  await router.push(target)
}
</script>

<style scoped>
.pt-search {
  width: 100%;
}

.pt-search-shell {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  height: 44px;
  padding: 0 0.4rem 0 0.85rem;
  border-radius: var(--portal-radius-pill);
  border: 1px solid rgb(255, 255, 255, 0.1);
  background: rgb(255, 255, 255, 0.07);
  color: rgb(255, 255, 255, 0.72);
  transition:
    border-color var(--portal-dur-base) ease,
    background var(--portal-dur-base) ease,
    box-shadow var(--portal-dur-base) ease;
}

.pt-search-shell:focus-within {
  border-color: rgb(var(--accent-rgb, 99, 102, 241), 0.42);
  background: rgb(255, 255, 255, 0.09);
  box-shadow: 0 0 0 4px rgb(var(--accent-rgb, 99, 102, 241), 0.12);
}

.pt-search-icon {
  flex-shrink: 0;
  color: rgb(255, 255, 255, 0.56);
}

.pt-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  color: #fff;
  font-size: var(--portal-text-base);
  outline: none;
}

.pt-search-input::placeholder {
  color: rgb(255, 255, 255, 0.42);
}

.pt-search-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: var(--portal-radius-pill);
  background: linear-gradient(
    135deg,
    rgb(var(--accent-rgb, 99, 102, 241), 0.9),
    rgb(var(--accent-rgb, 99, 102, 241), 0.68)
  );
  color: #fff;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    filter 0.18s ease,
    opacity 0.18s ease;
}

.pt-search-submit:hover:not(:disabled) {
  transform: translateX(1px);
  filter: brightness(1.08);
}

.pt-search-submit:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
</style>
