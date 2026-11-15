/**
 * The help articles offered by the wizard, read from the Help Center in the portal's
 * language. Fetched the first time a guide opens, again after a language change.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePortalHelp } from '@/composables/portal/usePortalHelp'

export function useHelpGuides() {
  const { locale } = useI18n()
  const { articles, loading, error, load } = usePortalHelp()
  const loadedLang = ref(null)

  const bySlug = computed(() => new Map(articles.value.map(article => [article.slug, article])))

  async function ensureLoaded() {
    const lang = locale.value
    if (loading.value || loadedLang.value === lang) return
    await load(lang)
    loadedLang.value = error.value ? null : lang
  }

  function articleFor(slug) {
    return bySlug.value.get(slug) || null
  }

  return { loading, error, ensureLoaded, articleFor }
}
