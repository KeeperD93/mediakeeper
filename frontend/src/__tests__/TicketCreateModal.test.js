/**
 * The "report an issue" form is a real dialog (named, modal, Escape closes
 * it, labels name their fields) and builds the payload of its two sources.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/components/portal/tickets/EmbyMediaPicker.vue', () => ({
  default: { name: 'EmbyMediaPicker', props: ['inputId'], template: '<input :id="inputId" />' },
}))
vi.mock('@/components/portal/tickets/TicketSeasonPicker.vue', () => ({
  default: { name: 'TicketSeasonPicker', template: '<div />' },
}))

import TicketCreateModal from '@/components/portal/tickets/TicketCreateModal.vue'

const mountForm = props => mount(TicketCreateModal, { props, attachTo: document.body })

describe('TicketCreateModal', () => {
  let w
  afterEach(() => w?.unmount())

  it('is a modal dialog named by its title, with a named close button', () => {
    w = mountForm()
    const dialog = w.find('[role="dialog"]')

    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(w.find(`#${dialog.attributes('aria-labelledby')}`).text()).toBe('portal.tickets.create')
    expect(w.find('.pt-popup-close').attributes('aria-label')).toBe('common.close')
  })

  it('closes on Escape', () => {
    w = mountForm()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(w.emitted('close')).toHaveLength(1)
  })

  // Escape waits only for the media picker's open list, not for any expanded
  // control (a season toggle).
  const pressEscapeOn = (role, expanded) => {
    const el = document.createElement('button')
    if (role) el.setAttribute('role', role)
    el.setAttribute('aria-expanded', expanded)
    w.find('[role="dialog"]').element.appendChild(el)
    el.focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
  }

  it('still closes on Escape from an expanded season toggle', () => {
    w = mountForm()
    pressEscapeOn(null, 'true')
    expect(w.emitted('close')).toHaveLength(1)
  })

  it('leaves Escape to the media picker while its list is open', () => {
    w = mountForm()
    pressEscapeOn('combobox', 'true')
    expect(w.emitted('close')).toBeUndefined()
  })

  it('links every label to its field, and the menu takes the shared chevron', () => {
    w = mountForm()

    for (const label of w.findAll('label')) {
      expect(w.find(`#${label.attributes('for')}`).exists()).toBe(true)
    }
    expect(w.find('select').classes()).toContain('mk-select-chevron')
  })

  // The test Teleport stub re-creates its content on each render: query the
  // elements again after every step instead of keeping a wrapper.
  const otherMode = () => w.findAll('.pt-mode-pill')[1]

  it('sends a title typed by hand as an "other" media', async () => {
    w = mountForm()

    await otherMode().trigger('click')
    await w.find('input.pt-input').setValue('  Some title  ')
    await w.find('textarea').setValue('  No sound  ')
    await w.find('.pt-btn--primary').trigger('click')

    expect(otherMode().attributes('aria-pressed')).toBe('true')
    expect(w.emitted('submit')).toEqual([
      [
        {
          issue_type: 'video',
          description: 'No sound',
          media_title: 'Some title',
          media_type: 'other',
        },
      ],
    ])
  })

  it('cannot be sent twice while the page sends it', async () => {
    w = mountForm({ busy: true })
    await otherMode().trigger('click')
    await w.find('input.pt-input').setValue('Some title')
    await w.find('textarea').setValue('No sound')

    expect(w.find('.pt-btn--primary').attributes('disabled')).toBeDefined()
  })

  // A failed send keeps the form and what was typed: no closing meanwhile.
  it('stays open while the page sends it', async () => {
    w = mountForm({ busy: true })

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await w.find('.pt-popup-close').trigger('click')
    await w.find('.pt-popup-overlay').trigger('click')

    expect(w.emitted('close')).toBeUndefined()
  })
})
