import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalNews() {
  const { apiGet, apiPost, apiPut, apiDelete, loading, error } = useApi()
  const news = ref([])
  const unreadNews = ref([])
  const hasMore = ref(false)
  const nextCursor = ref(null)

  async function fetchNews(reset = true) {
    if (reset) {
      news.value = []
      nextCursor.value = null
    }
    let url = '/api/portal/news?limit=20'
    if (nextCursor.value) url += `&cursor=${nextCursor.value}`
    try {
      const res = await apiGet(url)
      if (!res) return
      if (reset) news.value = res.items || []
      else news.value.push(...(res.items || []))
      nextCursor.value = res.next_cursor
      hasMore.value = res.has_more
    } catch {
      if (reset) news.value = []
    }
  }

  async function fetchUnread() {
    try {
      const res = await apiGet('/api/portal/news/unread')
      if (res) unreadNews.value = res.items || []
    } catch {
      unreadNews.value = []
    }
  }

  async function markRead(newsId, dismissed = false) {
    return await apiPost(`/api/portal/news/read/${newsId}?dismissed=${dismissed}`)
  }

  async function createNews(data) {
    return await apiPost('/api/portal/news', data)
  }

  async function updateNews(newsId, data) {
    return await apiPut(`/api/portal/news/${newsId}`, data)
  }

  async function deleteNews(newsId) {
    return await apiDelete(`/api/portal/news/${newsId}`)
  }

  return {
    news, unreadNews, hasMore, nextCursor,
    fetchNews, fetchUnread, markRead,
    createNews, updateNews, deleteNews,
    loading, error,
  }
}
