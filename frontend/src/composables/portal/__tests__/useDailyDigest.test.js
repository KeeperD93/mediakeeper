/**
 * useDailyDigest: the view the account keeps survives two quick switches, and a news
 * item is marked read once, dismissed, so « What's new » does not show it again.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

import { useDailyDigest } from '@/composables/portal/useDailyDigest'

const apiGet = vi.fn()
const apiPost = vi.fn()
const apiPut = vi.fn()
const showToast = vi.fn()

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPost, apiPut }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

const news = (id, isNew) => ({ id, title: `Test news ${id}`, content: 'Hello.', is_new: isNew })

async function setup(digest = { news: [news(1, true), news(2, false)] }) {
  let api
  mount(
    defineComponent({
      setup() {
        api = useDailyDigest()
        return () => h('div')
      },
    }),
  )
  apiGet.mockResolvedValue({ dismissed: false, compact: false, digest })
  await api.load()
  return api
}

describe('useDailyDigest', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset().mockResolvedValue({})
    apiPut.mockReset()
    showToast.mockReset()
  })

  it('keeps the last view chosen when an earlier save fails after it', async () => {
    const api = await setup()
    let failFirst
    apiPut
      .mockImplementationOnce(() => new Promise((_, reject) => (failFirst = reject)))
      .mockResolvedValueOnce({ compact: false })

    const first = api.setCompact(true)
    await api.setCompact(false)
    failFirst(new Error('http_500'))
    await first

    expect(api.compact.value).toBe(false)
    expect(showToast).not.toHaveBeenCalled()
  })

  it('keeps a view switched while the digest was still loading', async () => {
    const api = await setup()
    let answer
    apiGet.mockImplementationOnce(() => new Promise(resolve => (answer = resolve)))
    apiPut.mockResolvedValue({ compact: true })

    const loading = api.load({ force: true })
    await api.setCompact(true)
    answer({ dismissed: false, compact: false, digest: { news: [] } })
    await loading

    expect(api.compact.value).toBe(true)
  })

  it('takes the view the account keeps when nothing was switched meanwhile', async () => {
    const api = await setup()
    apiGet.mockResolvedValueOnce({ dismissed: false, compact: true, digest: { news: [] } })

    await api.load({ force: true })

    expect(api.compact.value).toBe(true)
  })

  it('marks a news item read once, dismissed, and only a new one', async () => {
    const api = await setup()

    api.readNews(1)
    api.readNews(1)
    api.readNews(2)

    expect(apiPost.mock.calls.map(([url]) => url)).toEqual([
      '/api/portal/news/read/1?dismissed=true',
    ])
    expect(api.digest.value.news[0].is_new).toBe(false)
  })

  it('reads on close the new items shown whole, then closes for the day', async () => {
    const api = await setup()

    api.noteNewsSeen(1)
    api.noteNewsSeen(2)
    await api.dismiss()

    expect(apiPost.mock.calls.map(([url]) => url)).toEqual([
      '/api/portal/news/read/1?dismissed=true',
      '/api/portal/daily-digest/dismiss',
    ])
  })
})
