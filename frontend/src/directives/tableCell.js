// Reflect a partial selection on a checkbox (the DOM-only `indeterminate` prop
// can't be set declaratively).
export const vIndeterminate = {
  mounted: (el, b) => (el.indeterminate = b.value),
  updated: (el, b) => (el.indeterminate = b.value),
}

// Native tooltip only when a cell's text is actually clipped — re-checked on
// hover so it stays accurate after a column resize. No tooltip when it fits.
export const vEllipsisTitle = {
  mounted(el) {
    el.__truncCheck = () => {
      el.title = el.scrollWidth > el.clientWidth ? el.textContent.replace(/\s+/g, ' ').trim() : ''
    }
    el.addEventListener('mouseenter', el.__truncCheck)
  },
  unmounted(el) {
    if (el.__truncCheck) el.removeEventListener('mouseenter', el.__truncCheck)
  },
}
