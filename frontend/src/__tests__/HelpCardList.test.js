/**
 * HelpCardList: an opened article body is scrubbed before it is rendered.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import HelpCardList from '@/components/portal/help/HelpCardList.vue'

const ARTICLE = {
  id: 1,
  category: 'general',
  icon: 'BookOpen',
  title: 'Test article',
  is_draft: false,
  body_html: '<p>Test body</p><img src="x" onerror="alert(1)"><script>alert(1)</script>',
}

describe('HelpCardList', () => {
  it('scrubs the opened article body before rendering it', () => {
    const w = mount(HelpCardList, { props: { articles: [ARTICLE], expandedId: ARTICLE.id } })
    const body = w.get('.pt-help-card-content').html()
    expect(body).toContain('<p>Test body</p>')
    expect(body).not.toContain('onerror')
    expect(body).not.toContain('<script')
  })
})
