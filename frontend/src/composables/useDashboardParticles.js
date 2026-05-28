/**
 * Canvas particles background for the desktop dashboard.
 *
 * Split out of DashboardView.vue so the page stays focused on layout
 * and data orchestration. The composable owns the canvas init loop,
 * the resize observer and the requestAnimationFrame teardown, and
 * runs through the full mount/activate/deactivate/unmount cycle so
 * the canvas stops painting when the page is parked behind KeepAlive.
 */
import { nextTick, onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'

const PARTICLE_COUNT = 50

export function useDashboardParticles(containerRef, canvasRef, enabledRef) {
  let cleanup = null

  function init() {
    const canvas = canvasRef.value
    const container = containerRef.value
    if (!canvas || !container) return null

    const ctx = canvas.getContext('2d')
    // Read --accent-rgb at init time so the particle colour follows
    // the active admin palette instead of a baked brand purple. The
    // value is captured once per init; if the operator changes the
    // accent at runtime, the canvas refreshes on the next mount cycle.
    const accentRgb = getComputedStyle(container).getPropertyValue('--accent-rgb').trim()
    const particles = []
    let raf = null
    let prevW = 0
    let prevH = 0

    function resize() {
      const newW = container.clientWidth
      const newH = container.scrollHeight
      canvas.width = newW
      canvas.height = newH
      // Rescale existing positions when the container changes shape so
      // particles don't snap to (0, 0) on a resize.
      if (prevW > 0 && prevH > 0) {
        const sx = newW / prevW
        const sy = newH / prevH
        for (const p of particles) {
          p.x *= sx
          p.y *= sy
        }
      }
      prevW = newW
      prevH = newH
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(container)

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const a = Math.random() * Math.PI * 2
      const s = 0.1 + Math.random() * 0.25
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: 1 + Math.random() * 2,
        dx: Math.cos(a) * s,
        dy: Math.sin(a) * s,
        o: 0.15 + Math.random() * 0.3,
      })
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      for (const p of particles) {
        p.x += p.dx
        p.y += p.dy
        if (p.x < -10) p.x = canvas.width + 10
        if (p.x > canvas.width + 10) p.x = -10
        if (p.y < -10) p.y = canvas.height + 10
        if (p.y > canvas.height + 10) p.y = -10
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${accentRgb},${p.o})`
        ctx.fill()
      }
      raf = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      ro.disconnect()
      if (raf) cancelAnimationFrame(raf)
    }
  }

  onMounted(async () => {
    await nextTick()
    if (enabledRef.value) cleanup = init()
  })

  onActivated(() => {
    if (!cleanup && enabledRef.value) cleanup = init()
  })

  onDeactivated(() => {
    if (cleanup) {
      cleanup()
      cleanup = null
    }
  })

  onUnmounted(() => {
    if (cleanup) cleanup()
  })
}
