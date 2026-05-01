import { ref, onMounted, onUnmounted } from 'vue'

const MOBILE_MAX = 767

export function useMobile() {
  const isMobile = ref(false)
  function check() {
    isMobile.value = typeof window !== 'undefined' && window.innerWidth <= MOBILE_MAX
  }
  onMounted(() => {
    check()
    window.addEventListener('resize', check, { passive: true })
  })
  onUnmounted(() => {
    window.removeEventListener('resize', check)
  })
  return { isMobile }
}
