export function initLoginParticles(canvas, page) {
  if (!canvas || !page) return null

  const ctx = canvas.getContext('2d')
  let W = canvas.width = page.offsetWidth
  let H = canvas.height = page.offsetHeight
  let animFrame = null

  const PARTICLE_COUNT = 50
  const particles = []

  function spawnParticle(randomPos) {
    const angle = Math.random() * Math.PI * 2
    const speed = 0.1 + Math.random() * 0.25
    return {
      x: randomPos ? Math.random() * W : W / 2 + (Math.random() - 0.5) * 300,
      y: randomPos ? Math.random() * H : H / 2 + (Math.random() - 0.5) * 300,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: 1 + Math.random() * 2,
      opacity: 0.15 + Math.random() * 0.3,
    }
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(spawnParticle(true))

  function draw() {
    ctx.clearRect(0, 0, W, H)
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i]
      p.x += p.vx
      p.y += p.vy
      if (p.x < -10) p.x = W + 10
      if (p.x > W + 10) p.x = -10
      if (p.y < -10) p.y = H + 10
      if (p.y > H + 10) p.y = -10
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(139, 132, 255, ${p.opacity})`
      ctx.fill()
    }
    animFrame = requestAnimationFrame(draw)
  }

  const ro = new ResizeObserver(() => {
    W = canvas.width = page.offsetWidth
    H = canvas.height = page.offsetHeight
  })
  ro.observe(page)

  draw()

  return () => {
    ro.disconnect()
    if (animFrame) cancelAnimationFrame(animFrame)
  }
}
