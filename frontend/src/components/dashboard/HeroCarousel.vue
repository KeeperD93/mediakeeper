<template>
  <div class="hero-wrap" :class="{ 'hero-entered': entered }">
    <div v-if="isAudio" class="hero-audio-bg">
      <div v-for="i in 5" :key="i" class="hero-audio-wave" :style="{ animationDelay: (i * 0.15) + 's' }" />
    </div>
    <template v-else>
      <div class="hero-backdrop-layer" :class="{ visible: showA, 'kb-a': true }" :style="{ backgroundImage: backdropA ? `url(${backdropA})` : 'none' }" />
      <div class="hero-backdrop-layer" :class="{ visible: !showA, 'kb-b': true }" :style="{ backgroundImage: backdropB ? `url(${backdropB})` : 'none' }" />
    </template>
    <div class="hero-overlay-bottom" /><div class="hero-overlay-top" />
    <div class="hero-ambiance" :style="ambianceStyle" />
    <div v-if="activeCount > 0" ref="connectedRef" class="hero-connected-wrap">
      <div class="hero-connected hero-connected-clickable" @click.stop="toggleDropdown"><span class="hero-connected-dot" /><span>{{ $t('dashboard.activeCount', { count: activeCount }) }}</span></div>
    </div>
    <Teleport to="body">
      <div v-if="showPopup" class="hero-dropdown" :style="ddPos" @click.stop>
        <div class="hero-dropdown-header">{{ $t('dashboard.users') }} ({{ connectedUsers.length }})</div>
        <div class="hero-dropdown-list">
          <div v-for="(u, i) in connectedUsers" :key="i" class="hero-dropdown-row">
            <span class="hero-dropdown-dot" :class="u.isActive ? 'dot-green' : 'dot-gray'" />
            <div class="hero-dropdown-info"><span class="hero-dropdown-name">{{ u.name }}</span><span class="hero-dropdown-device">{{ u.device || '—' }}</span></div>
            <span class="hero-dropdown-status" :class="u.isActive ? 'status-active' : 'status-idle'">{{ u.isActive ? $t('dashboard.statusActive') : $t('dashboard.statusIdle') }}</span>
          </div>
        </div>
      </div>
    </Teleport>
    <div v-if="sessions.length === 0" class="hero-empty">
      <MkEmptyState :title="$t('dashboard.noSessions')" />
    </div>
    <div v-else class="hero-content">
      <div class="hero-poster hero-poster-clickable anim-slide-up stg-30" :class="{ 'hero-poster-audio': isAudio }" @click="emit('open-fullscreen', current)">
        <img v-if="current.thumb_url && !posterError" :src="current.thumb_url" class="hero-poster-img" @error="posterError = true" />
        <span v-else-if="isAudio" class="hero-poster-ph hero-music-icon">♫</span>
        <span v-else class="hero-poster-ph">▶</span>
      </div>
      <div class="hero-info anim-slide-up stg-45">
        <span class="hero-badge-label" :class="current.is_playing ? (isAudio ? 'badge-audio' : 'badge-playing') : 'badge-paused'">
          <span class="hero-pulse-dot" :class="current.is_playing ? (isAudio ? 'pulse-purple' : 'pulse-green') : 'pulse-yellow'" />
          {{ isAudio ? (current.is_playing ? $t('dashboard.listening') : $t('dashboard.paused')) : (current.is_playing ? $t('dashboard.playing') : $t('dashboard.paused')) }}
        </span>
        <p class="hero-title hero-title-clickable" @click="emit('open-fullscreen', current)">
          {{ current.series || current.media }}
          <a v-if="currentEmbyUrl" :href="currentEmbyUrl" target="_blank" rel="noopener" class="hero-emby-link" :title="$t('dashboard.viewOnEmby')" @click.stop><img src="/assets/icons/emby.svg" class="hero-emby-icon" alt="Emby" /></a>
        </p>
        <p class="hero-sub">{{ current.episode ? `${current.episode} · ${current.media}` : (current.media_type || $t('common.film')) }} — {{ $t('dashboard.userOnDevice', { user: current.user, device: current.client || current.device || $t('common.unknown') }) }}</p>
        <div class="hero-progress"><div class="hero-progress-fill" :style="{ width: (current.progress || 0) + '%' }" /></div>
      </div>
      <div v-if="sessions.length > 1" class="hero-dots anim-slide-up stg-55">
        <button v-for="(s, i) in sessions" :key="i" class="hero-dot-btn" :class="{ active: i === idx }" @click="goTo(i)" />
        <span class="hero-dots-label">{{ $t('dashboard.activeCount', { count: sessions.length }) }}</span>
      </div>
      <div v-if="sessions.length > 1" class="hero-avatars anim-slide-up stg-60">
        <div v-for="(s, i) in sessions.slice(0, 4)" :key="i" class="hero-av" :class="{ 'hero-av-offset': i > 0 }" :style="{ background: avColors[i % avColors.length], zIndex: 10 - i }">
          <img v-if="userImages[s.user_id]" :src="userImages[s.user_id]" class="hero-av-img" @error="($event) => $event.target.remove()" />
          <span>{{ (s.user || '?')[0].toUpperCase() }}</span>
        </div>
        <div v-if="sessions.length > 4" class="hero-av hero-av-more hero-av-offset">+{{ sessions.length - 4 }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useUserImages } from '@/composables/useUserImages'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
const props = defineProps({ sessions: { type: Array, default: () => [] }, allSessions: { type: Array, default: () => [] }, embyBaseUrl: { type: String, default: '' } })
const emit = defineEmits(['open-fullscreen'])
const { getUserImageUrl } = useUserImages()
const userImages = ref({}); const idx = ref(0); const showPopup = ref(false); const connectedRef = ref(null); const entered = ref(false); const posterError = ref(false)
const avColors = ['#6366f1','#0ea5e9','#f59e0b','#ec4899','#22c55e']; let timer = null
const current = computed(() => props.sessions[idx.value] || {})
const isAudio = computed(() => current.value.media_type === 'Audio')
const currentPoster = computed(() => current.value.thumb_url || null)
const currentEmbyUrl = computed(() => { const s=current.value; if(!props.embyBaseUrl||!s.item_id) return ''; return `${props.embyBaseUrl}/web/index.html#!/item?id=${s.item_id}` })
const showA = ref(true); const backdropA = ref(null); const backdropB = ref(null)
watch(currentPoster, u => { posterError.value=false; if(showA.value){backdropB.value=u;showA.value=false}else{backdropA.value=u;showA.value=true} })
const GENRE_COLORS = {28:'rgba(239,68,68,0.12)',12:'rgba(245,158,11,0.1)',16:'rgba(59,130,246,0.1)',35:'rgba(251,191,36,0.1)',18:'rgba(99,102,241,0.1)',14:'rgba(168,85,247,0.12)',27:'rgba(220,38,38,0.15)',878:'rgba(6,182,212,0.12)',53:'rgba(55,65,81,0.15)',10759:'rgba(239,68,68,0.1)',10765:'rgba(6,182,212,0.1)'}
const ambianceStyle = computed(() => { for(const gid of (current.value.genre_ids||[])){if(GENRE_COLORS[gid]) return {background:GENRE_COLORS[gid]}}; return {background:'transparent'} })
const connectedUsers = computed(() => { const seen=new Map(); for(const s of props.allSessions){const name=s.user||s.UserName||t('common.unknown'); if(!seen.has(name)) seen.set(name,{name,device:s.device||s.client||'',isActive:s.is_playing||s.is_paused})}; return [...seen.values()].sort((a,b)=>b.isActive-a.isActive) })
const activeCount = computed(() => connectedUsers.value.filter(u=>u.isActive).length)
function goTo(i){idx.value=i;posterError.value=false;restartTimer()}
function restartTimer(){if(timer)clearInterval(timer);if(props.sessions.length>1)timer=setInterval(()=>{idx.value=(idx.value+1)%props.sessions.length;posterError.value=false},10000)}
function onClickOutside(e){if(showPopup.value&&connectedRef.value&&!connectedRef.value.contains(e.target)){const dd=document.querySelector('.hero-dropdown');if(dd&&dd.contains(e.target))return;showPopup.value=false}}
const ddPos=ref({})
function toggleDropdown(){if(showPopup.value){showPopup.value=false;return};if(connectedRef.value){const rect=connectedRef.value.getBoundingClientRect();ddPos.value={position:'fixed',top:(rect.bottom+8)+'px',right:(window.innerWidth-rect.right)+'px',zIndex:9999}};showPopup.value=true}
function onKeydown(e){if(e.key==='Escape')showPopup.value=false}
watch(()=>props.sessions.length,()=>{if(idx.value>=props.sessions.length)idx.value=0;restartTimer()})
watch(()=>props.sessions,async sessions=>{
  const userIds=[...new Set((sessions||[]).slice(0,4).map(s=>s.user_id).filter(id=>id&&!userImages.value[id]))]
  if(!userIds.length)return
  const results=await Promise.all(userIds.map(async id=>[id,await getUserImageUrl(id)]))
  const updates=Object.fromEntries(results.filter(([,url])=>url))
  if(Object.keys(updates).length)userImages.value={...userImages.value,...updates}
},{immediate:true})
onMounted(()=>{restartTimer();document.addEventListener('click',onClickOutside);document.addEventListener('keydown',onKeydown);if(currentPoster.value)backdropA.value=currentPoster.value;requestAnimationFrame(()=>{entered.value=true})})
onUnmounted(()=>{if(timer)clearInterval(timer);document.removeEventListener('click',onClickOutside);document.removeEventListener('keydown',onKeydown)})
</script>

<style scoped>
.hero-wrap{position:relative;height:340px;overflow:hidden;background:var(--hero-bg,#0a0e1a);opacity:0;transform:scale(1.02);transition:opacity 0.8s ease,transform 0.8s ease}
.hero-wrap.hero-entered{opacity:1;transform:scale(1)}
.hero-backdrop-layer{position:absolute;inset:-20px;z-index:0;background-size:cover;background-position:center;filter:blur(10px) brightness(0.55) saturate(1.4);opacity:0;transition:opacity 1.2s ease;will-change:transform}
.hero-backdrop-layer.visible{opacity:1}
.hero-backdrop-layer.kb-a{animation:ken-burns-a 20s ease-in-out infinite alternate}
.hero-backdrop-layer.kb-b{animation:ken-burns-b 22s ease-in-out infinite alternate}
@keyframes ken-burns-a{0%{transform:scale(1.05) translate(0,0)}100%{transform:scale(1.15) translate(-15px,-10px)}}
@keyframes ken-burns-b{0%{transform:scale(1.08) translate(10px,5px)}100%{transform:scale(1.18) translate(-10px,-15px)}}
.hero-wrap:not(:has(.hero-content)) .hero-backdrop-layer{animation:ken-burns-idle 30s ease-in-out infinite alternate}
@keyframes ken-burns-idle{0%{transform:scale(1.02) translate(0,0)}100%{transform:scale(1.08) translate(-8px,-5px)}}
.hero-ambiance{position:absolute;inset:0;z-index:0;transition:background 1.5s ease;pointer-events:none}
.hero-overlay-bottom{position:absolute;bottom:0;left:0;right:0;height:160px;background:linear-gradient(to top,var(--dash-bg,#060a14),transparent);z-index:1;pointer-events:none}
.hero-overlay-top{position:absolute;top:0;left:0;right:0;height:60px;background:linear-gradient(to bottom,rgba(6,10,20,0.6),transparent);z-index:1;pointer-events:none}
.anim-slide-up{opacity:0;transform:translateY(16px);animation:hero-slide-up 0.6s ease-out forwards}
@keyframes hero-slide-up{to{opacity:1;transform:translateY(0)}}
.hero-connected-wrap{position:absolute;top:14px;right:20px;z-index:20}
.hero-connected{display:flex;align-items:center;gap:6px;font-size:var(--text-2xs);color:rgba(255,255,255,0.5);background:rgba(0,0,0,0.3);backdrop-filter:blur(8px);padding:5px 12px;border-radius:var(--radius-card)}
.hero-connected-dot{width:6px;height:6px;border-radius:50%;background:#22c55e}
.hero-empty{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2}
.hero-content{position:absolute;bottom:28px;left:28px;right:28px;display:flex;align-items:flex-end;gap:16px;z-index:2}
.hero-poster{width:95px;height:138px;border-radius:var(--radius-btn);background:rgba(255,255,255,0.05);flex-shrink:0;overflow:hidden;border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow-md)}
.hero-poster-img{width:100%;height:100%;object-fit:cover}
.hero-poster-ph{font-size:28px;opacity:0.3;color:#fff}
.hero-info{flex:1;min-width:0}

/* Badge label alined with title text */
.hero-badge-label{
  display:inline-flex;align-items:center;gap:6px;
  font-size:var(--text-3xs);font-weight:var(--font-regular);letter-spacing:1px;text-transform:uppercase;
  margin-bottom:4px;
}
.badge-playing{color:#22c55e}
.badge-paused{color:#facc15}

/* Pulsing dot — real element, not ::before, for reliable animation */
.hero-pulse-dot{
  width:6px;height:6px;border-radius:50%;flex-shrink:0;
  position:relative;display:inline-block;
}
.pulse-green{background:#22c55e}
.pulse-yellow{background:#facc15}
.pulse-green::after,.pulse-yellow::after{
  content:'';position:absolute;inset:-3px;border-radius:50%;
  animation:hero-pulse var(--duration-pulse) ease-out infinite;
}
.pulse-green::after{background:rgba(34,197,94,0.5)}
.pulse-yellow::after{background:rgba(250,204,21,0.5)}
@keyframes hero-pulse{
  0%{transform:scale(1);opacity:0.7}
  70%{transform:scale(2.5);opacity:0}
  100%{transform:scale(2.5);opacity:0}
}

.hero-title{font-size:22px;font-weight:var(--font-medium);color:#fff;margin:0 0 2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:8px}
.hero-emby-link{display:inline-flex;align-items:center;flex-shrink:0;opacity:0.35;transition:opacity var(--duration-base)}
.hero-emby-link:hover{opacity:0.8}
.hero-emby-icon{width:18px;height:18px}
.hero-sub{font-size:var(--text-sm);color:rgba(255,255,255,0.45);margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hero-progress{margin-top:10px;height:3px;background:rgba(255,255,255,0.1);border-radius:2px;width:240px;max-width:100%}
.hero-progress-fill{height:3px;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:2px;transition:width var(--duration-slower)}
.hero-dots{display:flex;flex-direction:column;align-items:center;gap:6px;flex-shrink:0;padding-bottom:4px}
.hero-dot-btn{width:9px;height:9px;border-radius:50%;background:rgba(255,255,255,0.15);border:2px solid transparent;cursor:pointer;padding:0;transition:all var(--duration-slow)}
.hero-dot-btn.active{background: var(--accent-500);border-color:rgba(255,255,255,0.3);width:10px;height:10px}
.hero-dots-label{font-size:9px;color:var(--text-very-faint);white-space:nowrap}

/* Audio/Music mode */
.hero-audio-bg{position:absolute;inset:0;z-index:0;background:linear-gradient(135deg,#1a0533 0%,#0d1b2a 40%,#1a0533 100%);display:flex;align-items:center;justify-content:center;gap:6px;padding:0 30%}
.hero-audio-wave{width:4px;height:40px;background:rgba(139,132,255,0.3);border-radius:2px;animation:audio-wave 1.2s ease-in-out infinite alternate}
@keyframes audio-wave{0%{height:20px;opacity:0.3}100%{height:80px;opacity:0.6}}
.badge-audio{color:#a78bfa}
.pulse-purple{background:#a78bfa}
.pulse-purple::after{content:'';position:absolute;inset:-3px;border-radius:50%;background:rgba(167,139,250,0.5);animation:hero-pulse var(--duration-pulse) ease-out infinite}
.hero-poster-audio{background:linear-gradient(135deg,rgba(99,102,241,0.15),rgba(167,139,250,0.1));border-color:rgba(139,132,255,0.25)}
.hero-music-icon{font-size:32px;opacity:0.5;color:#a78bfa}
.hero-avatars{display:flex;align-items:center;flex-shrink:0;padding-bottom:8px}
.hero-av{width:36px;height:36px;border-radius:50%;border:2px solid var(--hero-bg,#0a0e1a);display:flex;align-items:center;justify-content:center;font-size:var(--text-xs);font-weight:var(--font-medium);color:#fff;position:relative;overflow:hidden}
.hero-av-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:50%}
.hero-av-more{background:rgba(255,255,255,0.1);font-size:var(--text-2xs);color:var(--text-faint)}
.hero-av-offset{margin-left:-8px}
.hero-connected-clickable{cursor:pointer}
.hero-poster-clickable{cursor:pointer}
.hero-title-clickable{cursor:pointer}
.stg-30{animation-delay:0.3s}
.stg-45{animation-delay:0.45s}
.stg-55{animation-delay:0.55s}
.stg-60{animation-delay:0.6s}
.hero-dropdown-list::-webkit-scrollbar{width:4px}
.hero-dropdown-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}

/* Mobile: stack dots + avatars below the title row so they don't compress the content name */
@media (max-width: 767px){
  .hero-content{flex-wrap:wrap;row-gap:10px;bottom:20px;left:18px;right:18px;gap:14px}
  .hero-info{flex:1 1 calc(100% - 109px);min-width:0}
  .hero-dots{order:2;flex-direction:row;padding-bottom:0;align-items:center}
  .hero-dots-label{font-size:var(--text-3xs)}
  .hero-avatars{order:3;padding-bottom:0;margin-left:auto}
}
</style>
<!-- Non-scoped block intentional: dropdown content uses <Teleport to="body">,
     so scoped-CSS data-v attributes never reach it. All selectors are prefixed
     with .hero-dropdown* to keep the namespace unique (rule §10). -->
<style>
.hero-dropdown{position:fixed;width:300px;max-height:340px;background:rgba(15,20,35,0.97);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius-card);overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.5);animation:dd-in 0.12s ease-out}
@keyframes dd-in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.hero-dropdown-header{padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);font-size:12px;font-weight:500;color:rgba(255,255,255,0.6)}
.hero-dropdown-list{max-height:280px;overflow-y:auto;padding:4px 0}
.hero-dropdown-row{display:flex;align-items:center;gap:10px;padding:9px 16px;transition:background 0.1s}
.hero-dropdown-row:hover{background:rgba(255,255,255,0.03)}
.hero-dropdown-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.hero-dropdown .dot-green{background:var(--color-success)}.hero-dropdown .dot-gray{background:rgba(255,255,255,0.15)}
.hero-dropdown-info{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
.hero-dropdown-name{color:rgba(255,255,255,0.85);font-weight:500;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hero-dropdown-device{color:rgba(255,255,255,0.25);font-size:11px}
.hero-dropdown-status{font-size:10px;flex-shrink:0;padding:2px 7px;border-radius:5px;font-weight:500}
.hero-dropdown .status-active{background:rgba(var(--color-success-rgb),0.12);color:var(--color-success)}
.hero-dropdown .status-idle{background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.3)}
</style>
