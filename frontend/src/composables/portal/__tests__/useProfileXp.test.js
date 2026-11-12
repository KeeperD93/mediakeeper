import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: key => key }) }))

import { levelFloorXp, useProfileXp } from '@/composables/portal/useProfileXp'

describe('useProfileXp, level bar', () => {
  it('starts the first level at 0 XP, like the server', () => {
    expect(levelFloorXp(1)).toBe(0)
    expect(levelFloorXp(2)).toBe(300)
  })

  it('moves the bar from the first XP at level 1', () => {
    const { xpPercent, nextLevelXp } = useProfileXp(ref({ level: 1, xp: 50 }), ref(null))
    expect(nextLevelXp.value).toBe(300)
    expect(xpPercent.value).toBe(17)
  })

  it('measures a higher level from its own floor', () => {
    const { xpPercent } = useProfileXp(ref({ level: 2, xp: 450 }), ref(null))
    expect(xpPercent.value).toBe(50)
  })
})
