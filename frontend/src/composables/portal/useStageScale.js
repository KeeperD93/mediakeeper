/**
 * Scale of a reduced portal screen: the width of its box over the screen's own width
 * (token --portal-demo-stage-w), never above 1, so the scene never overflows.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const STAGE_WIDTH_TOKEN = '--portal-demo-stage-w'

export function useStageScale(boxRef) {
  const scale = ref(0)
  let observer = null

  function measure() {
    const box = boxRef.value
    if (!box) return
    const stageWidth = parseFloat(getComputedStyle(box).getPropertyValue(STAGE_WIDTH_TOKEN))
    if (!stageWidth) return
    // Rounded down: a rounded-up scale would push the scene a fraction of a pixel out.
    scale.value = Math.min(1, Math.floor((box.clientWidth / stageWidth) * 1000) / 1000)
  }

  onMounted(() => {
    measure()
    if (!boxRef.value || typeof ResizeObserver === 'undefined') return
    observer = new ResizeObserver(measure)
    observer.observe(boxRef.value)
  })
  onBeforeUnmount(() => observer?.disconnect())

  return scale
}
