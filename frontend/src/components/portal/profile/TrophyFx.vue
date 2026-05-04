<template>
  <!-- Mastery meta-achievements: ultimateCollector-style aurora, border, rays,
       orbit gems and particles, but WITHOUT the pulsing crown on top — the
       crown above the avatar in RankSidebarCard already signals mastery. -->
  <template
    v-if="ach.status === TROPHY_STATUS.UNLOCKED && ach.category === TROPHY_CATEGORY.MASTERY"
  >
    <div class="gc-uc-aurora" :class="`gc-uc-aurora--${ach.target_category || ach.id}`" />
    <div class="gc-uc-border" :class="`gc-uc-border--${ach.target_category || ach.id}`" />
    <div class="gc-uc-rays"><span v-for="i in 8" :key="'mur' + i" class="gc-uc-ray" /></div>
    <div class="gc-uc-orbit"><span v-for="i in 6" :key="'muo' + i" class="gc-uc-gem" /></div>
    <div class="gc-secret-particles">
      <span v-for="i in 15" :key="'mup' + i" class="gc-uc-particle" />
    </div>
  </template>

  <template
    v-if="
      ach.status === TROPHY_STATUS.UNLOCKED &&
      !ach.secret &&
      ach.category !== TROPHY_CATEGORY.MASTERY
    "
  >
    <div v-if="['platinum', 'mythic', 'supreme'].includes(ach.tier_name)" class="gc-fx-sparkles">
      <span
        v-for="i in ach.tier_name === 'supreme' ? 12 : ach.tier_name === 'mythic' ? 8 : 6"
        :key="i"
        class="gc-sparkle"
      />
    </div>
    <template v-if="ach.tier_name === 'mythic'">
      <div class="gc-fx-legendary-halo" />
      <div class="gc-fx-legendary-embers">
        <span v-for="i in 6" :key="i" class="gc-ember" />
      </div>
    </template>
    <template v-if="ach.tier_name === 'supreme'">
      <div class="gc-fx-mythic-halo" />
      <div class="gc-fx-mythic-embers">
        <span v-for="i in 10" :key="i" class="gc-mythic-spark" />
      </div>
      <div class="gc-fx-mythic-aura-arc" />
    </template>
  </template>

  <template v-if="ach.secret && ach.status === TROPHY_STATUS.UNLOCKED && ach.secret_theme">
    <!-- first: confetti spark burst -->
    <template v-if="ach.secret_theme === 'first'">
      <div class="gc-secret-particles">
        <span v-for="i in 10" :key="'fs' + i" class="gc-first-spark" />
      </div>
      <div class="gc-first-burst" />
    </template>
    <!-- dawn: aurora rays + sparkles -->
    <template v-else-if="ach.secret_theme === 'dawn'">
      <div class="gc-dawn-rays" />
      <div class="gc-secret-particles">
        <span v-for="i in 6" :key="'dw' + i" class="gc-sparkle" />
      </div>
    </template>
    <!-- night: twinkling stars -->
    <div v-else-if="ach.secret_theme === 'night'" class="gc-secret-particles">
      <span v-for="i in 10" :key="'n' + i" class="gc-nightstar" />
    </div>
    <!-- xmas: snow + star + glow -->
    <template v-else-if="ach.secret_theme === 'xmas'">
      <div class="gc-secret-particles"><span v-for="i in 14" :key="'x' + i" class="gc-snow" /></div>
      <div class="gc-xmas-star" />
      <div class="gc-xmas-glow" />
    </template>
    <!-- halloween: bats + fog -->
    <template v-else-if="ach.secret_theme === 'halloween'">
      <div class="gc-secret-particles"><span v-for="i in 10" :key="'h' + i" class="gc-bat" /></div>
      <div class="gc-halloween-fog" />
    </template>
    <!-- valentine: floating hearts -->
    <div v-else-if="ach.secret_theme === 'valentine'" class="gc-secret-particles">
      <span v-for="i in 8" :key="'v' + i" class="gc-heart" />
    </div>
    <!-- newyear: fireworks + confetti + burst -->
    <template v-else-if="ach.secret_theme === 'newyear'">
      <div class="gc-secret-particles">
        <span v-for="i in 12" :key="'ny' + i" class="gc-firework" />
        <span v-for="i in 10" :key="'nyc' + i" class="gc-confetti-bit" />
      </div>
      <div class="gc-newyear-burst" />
    </template>
    <!-- vo: rotating flag colors + shimmer -->
    <template v-else-if="ach.secret_theme === 'vo'">
      <div class="gc-vo-flags" />
      <div class="gc-fx-shimmer" />
    </template>
    <!-- allnight: stars fading + dawn gradient -->
    <template v-else-if="ach.secret_theme === 'allnight'">
      <div class="gc-secret-particles">
        <span v-for="i in 8" :key="'an' + i" class="gc-nightstar" />
      </div>
      <div class="gc-allnight-dawn" />
    </template>
    <!-- classic: film grain + scanlines + vignette -->
    <template v-else-if="ach.secret_theme === 'classic'">
      <div class="gc-classic-grain" />
      <div class="gc-classic-scanlines" />
      <div class="gc-classic-vignette" />
    </template>
    <!-- friday13: blood drops -->
    <div v-else-if="ach.secret_theme === 'friday13'" class="gc-secret-particles">
      <span v-for="i in 8" :key="'f13' + i" class="gc-blood" />
    </div>
    <!-- indecisive: question marks -->
    <div v-else-if="ach.secret_theme === 'indecisive'" class="gc-secret-particles">
      <span v-for="i in 8" :key="'ind' + i" class="gc-qmark" />
    </div>
    <!-- summer: sun rays + sparkles -->
    <template v-else-if="ach.secret_theme === 'summer'">
      <div class="gc-summer-rays" />
      <div class="gc-secret-particles">
        <span v-for="i in 6" :key="'sun' + i" class="gc-sparkle" />
      </div>
    </template>
    <!-- nostalgia: film grain + light leak -->
    <template v-else-if="ach.secret_theme === 'nostalgia'">
      <div class="gc-nostalgia-grain" />
      <div class="gc-nostalgia-leak" />
    </template>
    <!-- pilot: sparkles + rocket trail star -->
    <template v-else-if="ach.secret_theme === 'pilot'">
      <div class="gc-secret-particles">
        <span v-for="i in 8" :key="'pil' + i" class="gc-sparkle" />
      </div>
      <div class="gc-pilot-star" />
    </template>
    <!-- insomnia: night stars + zzz + glow -->
    <template v-else-if="ach.secret_theme === 'insomnia'">
      <div class="gc-secret-particles">
        <span v-for="i in 12" :key="'ins' + i" class="gc-nightstar" />
        <span v-for="i in 4" :key="'insz' + i" class="gc-zzz" />
      </div>
      <div class="gc-insomnia-glow" />
    </template>
    <!-- king: sparkles + orbit + aura -->
    <template v-else-if="ach.secret_theme === 'king'">
      <div class="gc-secret-particles">
        <span v-for="i in 10" :key="'king' + i" class="gc-sparkle" />
      </div>
      <div class="gc-king-orbit"><span v-for="i in 4" :key="'ko' + i" class="gc-king-orb" /></div>
      <div class="gc-king-aura" />
    </template>
    <!-- ghost -->
    <div v-else-if="ach.secret_theme === 'ghost'" class="gc-ghost-wave" />
    <!-- double: mirror reflection -->
    <div v-else-if="ach.secret_theme === 'double'" class="gc-double-mirror" />
    <!-- fourk: crystal sparkles -->
    <div v-else-if="ach.secret_theme === 'fourk'" class="gc-secret-particles">
      <span v-for="i in 10" :key="'4k' + i" class="gc-crystal" />
    </div>
    <!-- easter: floating colored eggs -->
    <div v-else-if="ach.secret_theme === 'easter'" class="gc-secret-particles">
      <span v-for="i in 8" :key="'eg' + i" class="gc-egg" />
    </div>
    <!-- total: sparkles + rotating check -->
    <template v-else-if="ach.secret_theme === 'total'">
      <div class="gc-secret-particles">
        <span v-for="i in 8" :key="'tot' + i" class="gc-sparkle" />
      </div>
      <div class="gc-total-check" />
    </template>
    <!-- lonely: blue rain -->
    <div v-else-if="ach.secret_theme === 'lonely'" class="gc-secret-particles">
      <span v-for="i in 10" :key="'ln' + i" class="gc-raindrop" />
    </div>
    <!-- triple: triple golden bolts -->
    <div v-else-if="ach.secret_theme === 'triple'" class="gc-triple-bolts">
      <span v-for="i in 3" :key="'tb' + i" class="gc-bolt" />
    </div>
    <!-- ultramarathon: embers + rings -->
    <template v-else-if="ach.secret_theme === 'ultramarathon'">
      <div class="gc-secret-particles">
        <span v-for="i in 8" :key="'um' + i" class="gc-ultraember" />
      </div>
      <div class="gc-ultra-rings">
        <span v-for="i in 2" :key="'ur' + i" class="gc-ultra-ring" />
      </div>
    </template>
    <!-- pipi: water drops -->
    <div v-else-if="ach.secret_theme === 'pipi'" class="gc-secret-particles">
      <span v-for="i in 8" :key="'pp' + i" class="gc-drop" />
    </div>
    <!-- zapper: TV static -->
    <div v-else-if="ach.secret_theme === 'zapper'" class="gc-zapper-static" />
    <!-- butterfly: colored wings -->
    <div v-else-if="ach.secret_theme === 'butterfly'" class="gc-secret-particles">
      <span v-for="i in 6" :key="'bf' + i" class="gc-wing" />
    </div>
    <!-- bgNoise: zzz + fade -->
    <template v-else-if="ach.secret_theme === 'bgNoise'">
      <div class="gc-secret-particles"><span v-for="i in 5" :key="'bg' + i" class="gc-zzz" /></div>
      <div class="gc-bgNoise-fade" />
    </template>
    <!-- sunday: lazy clouds + sun -->
    <template v-else-if="ach.secret_theme === 'sunday'">
      <div class="gc-sunday-cloud" />
      <div class="gc-sunday-sun" />
    </template>
    <!-- bilingual: 3D glasses halo -->
    <div v-else-if="ach.secret_theme === 'bilingual'" class="gc-bilingual-halo" />
    <!-- sync: linked rings -->
    <div v-else-if="ach.secret_theme === 'sync'" class="gc-sync-rings">
      <span class="gc-sync-ring gc-sync-ring--1" />
      <span class="gc-sync-ring gc-sync-ring--2" />
    </div>
    <!-- countdown: flash -->
    <div v-else-if="ach.secret_theme === 'countdown'" class="gc-countdown-flash" />
    <!-- late: cobwebs + dust -->
    <template v-else-if="ach.secret_theme === 'late'">
      <div class="gc-secret-particles"><span v-for="i in 6" :key="'lt' + i" class="gc-dust" /></div>
      <div class="gc-late-web" />
    </template>
    <!-- gourmet: rising steam -->
    <div v-else-if="ach.secret_theme === 'gourmet'" class="gc-secret-particles">
      <span v-for="i in 6" :key="'gm' + i" class="gc-steam" />
    </div>
    <!-- Ultimate Collector: full legendary effect -->
    <template v-else-if="ach.secret_theme === 'ultimateCollector'">
      <div class="gc-uc-aurora" />
      <div class="gc-uc-border" />
      <div class="gc-uc-rays"><span v-for="i in 8" :key="'ucr' + i" class="gc-uc-ray" /></div>
      <div class="gc-uc-orbit"><span v-for="i in 6" :key="'uco' + i" class="gc-uc-gem" /></div>
      <div class="gc-secret-particles">
        <span v-for="i in 15" :key="'ucp' + i" class="gc-uc-particle" />
      </div>
      <div class="gc-uc-crown" />
    </template>
  </template>
</template>

<script setup>
import { TROPHY_STATUS, TROPHY_CATEGORY } from '@/constants/achievements'

defineProps({
  ach: { type: Object, required: true },
})
</script>
