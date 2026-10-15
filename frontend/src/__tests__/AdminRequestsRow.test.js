import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return { ...actual, useI18n: () => ({ t: key => key, locale: ref('fr') }) }
})

import AdminRequestsRow from '@/components/portal/admin/AdminRequestsRow.vue'

function mountRow(status) {
  return mount(AdminRequestsRow, {
    props: { req: { id: 1, tmdb_id: 7, media_type: 'movie', title: 'Sample', status } },
    global: { stubs: { MkAvatar: true } },
  })
}

const action = (w, label) => w.find(`button[aria-label="${label}"]`)

describe('AdminRequestsRow actions', () => {
  it('lets an approved request be marked available or rejected', async () => {
    const w = mountRow('approved')

    await action(w, 'portal.requests.available').trigger('click')
    await action(w, 'portal.admin.reject').trigger('click')

    expect(w.emitted('action')).toEqual([['available'], ['rejected']])
    expect(action(w, 'portal.admin.approve').exists()).toBe(false)
  })

  it('offers no status action once a request is available', () => {
    const w = mountRow('available')

    expect(action(w, 'portal.admin.reject').exists()).toBe(false)
    expect(action(w, 'portal.admin.delete').exists()).toBe(true)
  })
})
