import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import HelpEditor from '@/components/portal/help/HelpEditor.vue'

let wrapper

afterEach(() => wrapper?.unmount())

function mountEditor(modelValue) {
  wrapper = mount(HelpEditor, { props: { modelValue } })
  return wrapper
}

describe('HelpEditor', () => {
  it('replaces the content silently when the parent changes modelValue', async () => {
    mountEditor('<p>first</p>')
    await wrapper.setProps({ modelValue: '<h2>second</h2>' })

    expect(wrapper.find('.pt-help-editor-prose h2').text()).toBe('second')
    // An emit here would bounce the normalised HTML back to the parent and mark the card dirty.
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('applies then clears the font size from the toolbar select', async () => {
    mountEditor('<p>hello</p>')
    const select = wrapper.find('select.pt-help-tb-select')

    wrapper.vm.editor.commands.selectAll()
    await select.setValue('1.35em')
    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toBe(
      '<p><span style="font-size: 1.35em;">hello</span></p>',
    )

    wrapper.vm.editor.commands.selectAll()
    await select.setValue('')
    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toBe('<p>hello</p>')
  })

  it('registers each extension once, link and underline included', () => {
    mountEditor('')
    const names = wrapper.vm.editor.extensionManager.extensions.map(ext => ext.name)

    expect(new Set(names).size).toBe(names.length)
    expect(names).toEqual(expect.arrayContaining(['link', 'underline', 'fontSize', 'table']))
  })
})
