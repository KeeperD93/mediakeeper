/**
 * Help Center store — fetch the published catalogue once per overlay
 * open, expose grouping by category and a free-text search filter.
 *
 * Lives as a regular composable (not Pinia) like the other portal
 * stores. Each call to ``usePortalHelp()`` returns its own state, but
 * inside the overlay we instantiate it at the root and pass refs down,
 * so a single fetch covers the whole session.
 */
import { computed, ref } from 'vue'
import { useApi } from '@/composables/useApi'

const HELP_CATEGORIES = ['general', 'requests', 'profile', 'lists', 'issues', 'misc']

export function usePortalHelp() {
  const { apiGet } = useApi()

  const articles = ref([])
  const lang = ref('fr')
  const loading = ref(false)
  const error = ref(null)
  const search = ref('')
  const activeCategory = ref('general')
  const activeArticleId = ref(null)

  async function load(requestedLang, { admin = false } = {}) {
    loading.value = true
    error.value = null
    try {
      const langQS = encodeURIComponent(requestedLang || 'fr')
      const path = admin
        ? `/api/portal/admin/help/articles?include_deleted=0&lang=${langQS}`
        : `/api/portal/help/articles?lang=${langQS}`
      const res = await apiGet(path)
      articles.value = Array.isArray(res?.items) ? res.items : []
      lang.value = res?.lang || requestedLang || 'fr'
    } catch (err) {
      error.value = err?.data?.detail || 'help_load_failed'
      articles.value = []
    } finally {
      loading.value = false
    }
  }

  function stripHtml(html) {
    if (!html) return ''
    return String(html)
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  const filteredArticles = computed(() => {
    const q = search.value.trim().toLowerCase()
    if (!q) return articles.value
    return articles.value.filter(a => {
      const blob = `${a.title || ''} ${stripHtml(a.body_html)}`.toLowerCase()
      return blob.includes(q)
    })
  })

  const groupedByCategory = computed(() => {
    const map = {}
    for (const cat of HELP_CATEGORIES) map[cat] = []
    for (const a of filteredArticles.value) {
      if (!map[a.category]) map[a.category] = []
      map[a.category].push(a)
    }
    return map
  })

  const categoryCounts = computed(() => {
    const counts = {}
    for (const cat of HELP_CATEGORIES) {
      counts[cat] = (groupedByCategory.value[cat] || []).length
    }
    return counts
  })

  const articlesInActiveCategory = computed(
    () => groupedByCategory.value[activeCategory.value] || [],
  )

  const activeArticle = computed(() => {
    if (activeArticleId.value == null) return null
    return articles.value.find(a => a.id === activeArticleId.value) || null
  })

  function selectArticle(id) {
    activeArticleId.value = id
  }

  function clearArticle() {
    activeArticleId.value = null
  }

  function selectCategory(cat) {
    if (HELP_CATEGORIES.includes(cat)) {
      activeCategory.value = cat
      activeArticleId.value = null
    }
  }

  return {
    HELP_CATEGORIES,
    articles,
    lang,
    loading,
    error,
    search,
    activeCategory,
    activeArticleId,
    filteredArticles,
    groupedByCategory,
    categoryCounts,
    articlesInActiveCategory,
    activeArticle,
    load,
    selectArticle,
    clearArticle,
    selectCategory,
  }
}
