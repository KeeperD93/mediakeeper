import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { PORTAL_TAB } from '@/constants/portal'
import { safeHref } from '@/utils/safeUrl'
import { useSearchHotkey } from '@/composables/portal/useSearchHotkey'

export function usePortalNav(props, emit) {
  const { t } = useI18n()
  const router = useRouter()
  const { logout } = useAuth()

  const navRef = ref(null)
  const menuRef = ref(null)
  const menuOpen = ref(false)
  const scrolled = ref(false)
  const searchDrawerOpen = ref(false)

  function toggleSearchDrawer() {
    searchDrawerOpen.value = !searchDrawerOpen.value
  }

  function focusVisibleSearchInput() {
    if (typeof document === 'undefined') return false
    const inputs = document.querySelectorAll('.pt-search-input')
    for (const input of inputs) {
      if (!(input instanceof HTMLElement)) continue
      // offsetParent is null for elements with display:none ancestors,
      // so this skips the topbar input when the compact-mode CSS hides it.
      if (input.offsetParent === null) continue
      input.focus()
      if (typeof input.select === 'function') input.select()
      return true
    }
    return false
  }

  function focusPortalSearch() {
    if (focusVisibleSearchInput()) return
    searchDrawerOpen.value = true
    nextTick(() => {
      const drawerInput = document.querySelector('.pt-nav-search-drawer .pt-search-input')
      if (drawerInput instanceof HTMLElement) {
        drawerInput.focus()
        if (typeof drawerInput.select === 'function') drawerInput.select()
      }
    })
  }

  useSearchHotkey(focusPortalSearch)

  // Close the search drawer whenever the route changes.
  watch(
    () => router.currentRoute.value.fullPath,
    () => {
      searchDrawerOpen.value = false
    },
  )

  const tabs = computed(() => {
    const base = [
      { name: PORTAL_TAB.HOME, label: 'portal.tabs.home' },
      { name: PORTAL_TAB.ME, label: 'portal.tabs.profile' },
    ]
    if (props.showRequestsTab) {
      base.push({ name: PORTAL_TAB.REQUESTS, label: 'portal.tabs.discover' })
    }
    base.push({ name: PORTAL_TAB.TICKETS, label: 'portal.tabs.problems' })
    return base
  })

  const avatarInitial = computed(() => props.profile?.display_name?.charAt(0)?.toUpperCase() || '?')
  const roleLabel = computed(() =>
    props.isAdmin ? t('portal.avatar.admin') : t('portal.avatar.user'),
  )
  const supportTitle = computed(() =>
    props.supportUrl ? t('portal.nav.support') : t('portal.nav.supportSoon'),
  )
  const hasHero = computed(
    () => props.activeTab === PORTAL_TAB.HOME || props.activeTab === PORTAL_TAB.ME,
  )

  function isTabActive(name) {
    if (name === PORTAL_TAB.ME) {
      return props.activeTab === PORTAL_TAB.ME
    }
    if (name === PORTAL_TAB.TICKETS) {
      return props.activeTab === PORTAL_TAB.TICKETS || props.activeTab === PORTAL_TAB.TICKET_DETAIL
    }
    return props.activeTab === name
  }

  function navigateTo(name) {
    menuOpen.value = false
    emit('navigate', name)
  }

  function goToDashboard() {
    menuOpen.value = false
    router.push({ name: 'dashboard' })
  }

  function goToSettings() {
    menuOpen.value = false
    router.push({ name: 'portal-settings' })
  }

  function openWhatsNew() {
    menuOpen.value = false
    emit('open-whats-new')
  }

  function openDailyDigest() {
    menuOpen.value = false
    emit('open-daily-digest')
  }

  function openHelp() {
    menuOpen.value = false
    emit('open-help')
  }

  function goToLists() {
    menuOpen.value = false
    router.push({ name: PORTAL_TAB.LISTS })
  }

  function toggleMenu() {
    menuOpen.value = !menuOpen.value
  }

  function openSupport() {
    const target = safeHref(props.supportUrl)
    if (!target) return
    window.open(target, '_blank', 'noopener,noreferrer')
  }

  async function doLogout() {
    menuOpen.value = false
    await logout()
    router.replace({ name: 'login', query: { logged_out: '1' } })
  }

  function handleDocumentClick(event) {
    if (menuRef.value?.contains(event.target)) return
    menuOpen.value = false
  }

  function onScroll() {
    if (!hasHero.value) {
      scrolled.value = true
      return
    }

    const hero = document.querySelector('.pt-hero, .dp-hero')
    if (!hero) {
      scrolled.value = false
      return
    }

    const navHeight = navRef.value?.offsetHeight || 72
    scrolled.value = hero.getBoundingClientRect().bottom <= navHeight - 8
  }

  watch(
    () => props.activeTab,
    () => nextTick(onScroll),
  )

  let heroWatchTimer = null

  onMounted(() => {
    document.addEventListener('mousedown', handleDocumentClick)
    window.addEventListener('scroll', onScroll, { passive: true })
    nextTick(onScroll)

    let tries = 0
    heroWatchTimer = setInterval(() => {
      onScroll()
      tries += 1
      if (document.querySelector('.pt-hero, .dp-hero') || tries > 40) {
        clearInterval(heroWatchTimer)
        heroWatchTimer = null
      }
    }, 100)
  })

  onUnmounted(() => {
    document.removeEventListener('mousedown', handleDocumentClick)
    window.removeEventListener('scroll', onScroll)
    if (heroWatchTimer) clearInterval(heroWatchTimer)
  })

  return {
    navRef,
    menuRef,
    menuOpen,
    scrolled,
    searchDrawerOpen,
    tabs,
    avatarInitial,
    roleLabel,
    supportTitle,
    toggleSearchDrawer,
    focusPortalSearch,
    isTabActive,
    navigateTo,
    goToDashboard,
    goToSettings,
    toggleMenu,
    openSupport,
    doLogout,
    openWhatsNew,
    openDailyDigest,
    openHelp,
    goToLists,
  }
}
