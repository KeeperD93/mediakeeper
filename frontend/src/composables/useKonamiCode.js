import { onMounted, onUnmounted } from 'vue'

/**
 * Konami Code Easter Egg : ↑↑↓↓←→←→BA
 * Triggers: rainbow hue-rotate 3s + shake sidebar + emoji pop
 */
const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a']

export function useKonamiCode() {
  let pos = 0
  let timeout = null

  function onKeydown(e) {
    if (e.key === KONAMI[pos]) {
      pos++
      if (pos === KONAMI.length) {
        activate()
        pos = 0
      }
    } else {
      pos = 0
    }

    // Auto-reset if too slow (5s)
    clearTimeout(timeout)
    timeout = setTimeout(() => { pos = 0 }, 5000)
  }

  function activate() {
    // Rainbow body
    document.body.classList.add('mk-konami-active')

    // Emoji pop
    const emojis = ['🎬', '🍿', '🎥', '🎮', '🏆', '⭐', '🚀', '🎉']
    const toast = document.createElement('div')
    toast.className = 'mk-konami-toast'
    toast.textContent = emojis[Math.floor(Math.random() * emojis.length)] + ' KONAMI! ' + emojis[Math.floor(Math.random() * emojis.length)]
    document.body.appendChild(toast)

    // Spawn floating emojis
    for (let i = 0; i < 20; i++) {
      spawnEmoji(emojis[Math.floor(Math.random() * emojis.length)], i * 80)
    }

    // Cleanup after 3s
    setTimeout(() => {
      document.body.classList.remove('mk-konami-active')
      toast.remove()
    }, 3000)
  }

  function spawnEmoji(emoji, delay) {
    setTimeout(() => {
      const el = document.createElement('div')
      el.textContent = emoji
      el.style.cssText = `
        position:fixed;
        font-size:${20 + Math.random() * 20}px;
        left:${Math.random() * 100}vw;
        top:100vh;
        z-index:100000;
        pointer-events:none;
        animation: mk-emoji-rise ${2 + Math.random() * 2}s ease-out forwards;
      `
      document.body.appendChild(el)
      setTimeout(() => el.remove(), 4000)
    }, delay)
  }

  onMounted(() => {
    document.addEventListener('keydown', onKeydown)

    // Inject emoji rise keyframes if not present
    if (!document.getElementById('mk-konami-keyframes')) {
      const style = document.createElement('style')
      style.id = 'mk-konami-keyframes'
      style.textContent = `
        @keyframes mk-emoji-rise {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(-110vh) rotate(${360}deg); opacity: 0; }
        }
      `
      document.head.appendChild(style)
    }
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', onKeydown)
    clearTimeout(timeout)
  })
}
