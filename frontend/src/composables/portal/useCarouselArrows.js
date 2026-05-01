import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

/**
 * Shared scroll-arrow + fade logic for any horizontal carousel.
 *
 * Returns a `trackRef` that must be bound to the scrollable container
 * (the one with `overflow-x: auto`), plus reactive flags that drive
 * the previous/next arrow `v-show` and the left/right fade overlays.
 *
 * `scroll(dir)` moves by one full "page" of visible cards, sized from
 * the actual card widths + gap read from the DOM — robust to any
 * card size and to responsive breakpoints.
 *
 * Pass a reactive `itemsRef` so the flags update when the underlying
 * list changes (new items appended, filter applied, …).
 */
export function useCarouselArrows(itemsRef = null) {
  const trackRef = ref(null)
  const canScrollLeft = ref(false)
  const canScrollRight = ref(false)

  function onScroll() {
    const el = trackRef.value
    if (!el) return
    // Higher threshold (32px) so scroll-snap's rest position — which
    // often leaves scrollLeft at a few pixels > 0 when the first card
    // is snapped flush to the scroll-padding edge — doesn't falsely
    // reveal the left arrow when we're visually at the leftmost slide.
    canScrollLeft.value = el.scrollLeft > 32
    canScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 32
  }

  function scroll(dir) {
    const el = trackRef.value
    if (!el) return
    const firstCard = el.firstElementChild
    if (!firstCard) return
    const cardRect = firstCard.getBoundingClientRect()
    const trackRect = el.getBoundingClientRect()

    let gap = 12
    const cards = el.children
    if (cards.length >= 2) {
      const a = cards[0].getBoundingClientRect()
      const b = cards[1].getBoundingClientRect()
      gap = b.left - a.right
    }
    const step = cardRect.width + gap
    if (step <= 0) return

    const visible = Math.max(1, Math.floor(trackRect.width / step))
    const amount = visible * step
    el.scrollBy({ left: dir * amount, behavior: 'smooth' })
  }

  let resizeObs = null
  onMounted(() => {
    if (trackRef.value) {
      resizeObs = new ResizeObserver(onScroll)
      resizeObs.observe(trackRef.value)
      nextTick(onScroll)
    }
  })
  onUnmounted(() => resizeObs?.disconnect())

  if (itemsRef) {
    watch(itemsRef, () => nextTick(onScroll))
  }

  return { trackRef, canScrollLeft, canScrollRight, onScroll, scroll }
}
