<template>
  <div class="container">
    <h1>🎧 PlexDiscover</h1>
    
    <div v-if="loading">A verificar estado...</div>
    
    <div v-else-if="!plexLinked" class="auth-section">
      <p>Para começar, precisamos de acesso à tua conta Plex.</p>
      
      <div v-if="!authUrl">
        <button @click="startPlexAuth" class="btn">Ligar conta Plex</button>
      </div>
      
      <div v-else>
        <p>Abre o link abaixo e autoriza a aplicação (abrirá noutro separador):</p>
        <a :href="authUrl" target="_blank" @click="startChecking" class="btn btn-outline">
          Autorizar no Plex
        </a>
        
        <p v-if="isChecking" class="status-msg">
          ⏳ A aguardar a tua autorização no browser...
        </p>
      </div>
    </div>
    
    <div v-else class="app-layout">
      <!-- Barra de Navegação por Separadores -->
      <nav class="main-tabs">
        <button 
          :class="['tab-btn', { active: currentTab === 'dashboard' }]" 
          @click="currentTab = 'dashboard'"
        >
          🎧 Agora a Tocar & Fila
        </button>
        <button 
          :class="['tab-btn', { active: currentTab === 'settings' }]" 
          @click="currentTab = 'settings'"
        >
          ⚙️ Definições
        </button>
      </nav>

      <!-- SEPARADOR: DASHBOARD & FILA -->
      <div v-if="currentTab === 'dashboard'" class="dashboard">
        <!-- Card Agora a Tocar Enriquecido -->
        <div class="now-playing-card">
          <div class="card-header">
            <h3>Agora a Tocar no Plex</h3>
            <span v-if="nowPlaying && nowPlaying.is_playing" :class="['status-pill', nowPlaying.state]">
              {{ nowPlaying.state === 'paused' ? '⏸️ Em Pausa' : '▶️ A Tocar' }}
            </span>
          </div>
          
          <div v-if="nowPlaying" class="track-info">
            <div v-if="nowPlaying.is_playing" class="player-layout">
              <!-- Capa do Álbum com Efeito Vinil -->
              <div class="album-art-wrapper">
                <img 
                  v-if="nowPlaying.thumb" 
                  :src="`${API_BASE}/plex/image?path=${encodeURIComponent(nowPlaying.thumb)}`" 
                  alt="Capa do Álbum" 
                  class="album-art" 
                />
                <div v-else class="album-art-placeholder">🎵</div>
                <div :class="['vinyl-disc', { 'paused': nowPlaying.state === 'paused' }]">💿</div>
              </div>

              <!-- Detalhes da Faixa e Álbum -->
              <div class="player-details">
                <h4 class="track-title">{{ nowPlaying.track }}</h4>
                <p class="track-artist">👤 <strong>{{ nowPlaying.artist }}</strong></p>
                <p class="track-album">💿 {{ nowPlaying.album }}</p>
                <p class="meta">Dispositivo: <strong>{{ nowPlaying.player }}</strong> ({{ nowPlaying.user }})</p>

                <!-- Barra de Progresso do Álbum / Tempo Restante -->
                <div v-if="nowPlaying.is_album && nowPlaying.total_duration_ms > 0" class="album-progress-box">
                  <div class="progress-labels">
                    <span>Faixa {{ nowPlaying.current_track_index }} de {{ nowPlaying.track_count }}</span>
                    <span class="remaining-time">Faltam {{ formatMs(nowPlaying.remaining_ms) }} para acabar o álbum</span>
                  </div>
                  <div class="progress-bar-bg">
                    <div 
                      class="progress-bar-fill" 
                      :style="{ width: `${Math.min(100, (nowPlaying.elapsed_ms / nowPlaying.total_duration_ms) * 100)}%` }"
                    ></div>
                  </div>
                  <div class="time-sub">
                    <span>{{ formatMs(nowPlaying.elapsed_ms) }} decorridos</span>
                    <span>Total álbum: {{ formatMs(nowPlaying.total_duration_ms) }}</span>
                  </div>
                </div>
                <div v-else class="non-album-tag">
                  <span>📻 Reprodução avulsa / rádio</span>
                </div>

                <div class="actions-row">
                  <button class="btn btn-sm" @click="discover(nowPlaying.artist)" :disabled="isDiscovering">
                    {{ isDiscovering ? 'A procurar...' : '🔍 Descobrir Manualmente' }}
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p>Não estás a ouvir música neste momento.</p>
              <p class="subtitle">Abre o Plexamp e mete um álbum a tocar!</p>
            </div>
          </div>
          <div v-else>
            <p>A procurar sessões ativas...</p>
          </div>
        </div>

        <!-- Card da Fila de Descoberta em Tempo Real -->
        <div v-if="discoveryQueue && discoveryQueue.length > 0" class="discovery-card queue-card">
          <div class="card-header">
            <div>
              <h3>🚀 Fila de Descoberta em Tempo Real</h3>
              <p class="subtitle" style="margin-top: 2px;">
                Músicas preparadas e injetadas automaticamente no teu Plexamp
              </p>
            </div>
            <button @click="clearQueue" class="btn-text">Limpar Lista</button>
          </div>

          <div class="queue-list">
            <div v-for="(item, idx) in discoveryQueue" :key="idx" class="queue-row">
              <div class="queue-meta">
                <span class="queue-index">{{ idx + 1 }}</span>
                <div>
                  <strong class="queue-artist">{{ item.artist }}</strong>
                  <span class="queue-title"> — {{ item.title }}</span>
                  <div class="queue-detail" v-if="item.detail">{{ item.detail }}</div>
                </div>
              </div>
              
              <div class="queue-right-col">
                <div class="queue-status-col">
                  <span v-if="item.status === 'searching'" class="badge badge-searching">🔍 A pesquisar...</span>
                  <span v-else-if="item.status === 'downloading'" class="badge badge-downloading">⏳ A transferir</span>
                  <span v-else-if="item.status === 'tagging'" class="badge badge-tagging">🏷️ A etiquetar</span>
                  <span v-else-if="item.status === 'imported'" class="badge badge-imported">📥 Guardada</span>
                  <span v-else-if="item.status === 'injected'" class="badge badge-injected">✨ Injetada no Plexamp</span>
                  <span v-else-if="item.status === 'error'" class="badge badge-error">❌ Erro</span>
                  <span v-else class="badge pending">Pendente</span>
                </div>
                <div class="queue-actions">
                  <button 
                    v-if="item.status === 'imported' || item.status === 'injected'" 
                    @click="promoteArtist(item.artist)" 
                    class="btn-action btn-promote" 
                    title="Promover / Mover esta banda para a biblioteca permanente do Plex"
                  >
                    ⭐ Guardar Banda
                  </button>
                  <button 
                    @click="ignoreArtist(item.artist)" 
                    class="btn-action btn-ignore" 
                    title="Ignorar Artista / Adicionar à lista negra"
                  >
                    🚫 Ignorar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Card de Recomendações Manuais Last.fm (quando feito clique manual) -->
        <div v-if="discoveryResults" class="discovery-card">
          <h3>Recomendações Manuais (Last.fm)</h3>
          <p class="subtitle">Com base em: <strong>{{ discoveryResults.source_artist }}</strong></p>
          
          <div class="playlist">
            <div v-for="(track, index) in discoveryResults.playlist" :key="index" class="track-item">
              <div class="track-details">
                <strong>{{ track.artist }}</strong> - {{ track.title }}
              </div>
              <div class="track-status">
                <button v-if="!track.status || track.status === 'pending'" @click="downloadTrack(track)" class="btn btn-sm">Descarregar</button>
                <span v-else-if="track.status === 'downloading'" class="badge pending">⏳ A procurar...</span>
                <span v-else-if="track.status === 'success'" class="badge success">✅ Agendado</span>
                <span v-else-if="track.status === 'error'" class="badge error">❌ Erro / Não Encontrado</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SEPARADOR: DEFINIÇÕES DEDICADAS -->
      <div v-else-if="currentTab === 'settings'">
        <SettingsView :api-base="API_BASE" @settings-updated="checkSettings" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SettingsView from './components/SettingsView.vue'

const currentTab = ref('dashboard')
const loading = ref(true)
const plexLinked = ref(false)
const lastfmLinked = ref(false)
const slskdLinked = ref(false)
const autoPilotEnabled = ref(false)
const autoPilotLimit = ref(20)
const autoPilotArtistsLimit = ref(15)
const autoPilotTracksPerArtist = ref(1)
const recommendationMode = ref('contextual')
const lastfmUserInput = ref('')
const lastfmKeyInput = ref('')
const slskdUrlInput = ref('')
const slskdKeyInput = ref('')
const authUrl = ref('')
const pinId = ref(null)
const isChecking = ref(false)
let checkInterval = null
let nowPlayingInterval = null

const nowPlaying = ref(null)
const isDiscovering = ref(false)
const discoveryResults = ref(null)
const discoveryQueue = ref([])
const ignoredArtists = ref([])
let queueInterval = null

async function fetchIgnoredArtists() {
  try {
    const res = await fetch(`${API_BASE}/ignored-artists`)
    if (res.ok) {
      ignoredArtists.value = await res.json()
    }
  } catch (e) {
    console.error("Erro ao carregar artistas ignorados:", e)
  }
}

async function ignoreArtist(artistName) {
  if (!confirm(`Tens a certeza que queres ignorar "${artistName}"? Nunca mais será sugerido.`)) return
  try {
    const res = await fetch(`${API_BASE}/ignored-artists`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist: artistName })
    })
    if (res.ok) {
      await fetchIgnoredArtists()
      await fetchDiscoveryQueue()
      alert(`"${artistName}" foi adicionado à lista de ignorados.`)
    }
  } catch (e) {
    alert("Erro ao ignorar artista.")
  }
}

async function unignoreArtist(artistName) {
  try {
    const res = await fetch(`${API_BASE}/ignored-artists/${encodeURIComponent(artistName)}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      await fetchIgnoredArtists()
    }
  } catch (e) {
    console.error("Erro ao remover da lista negra:", e)
  }
}

async function promoteArtist(artistName) {
  if (!confirm(`Queres guardar "${artistName}" e mover para a tua biblioteca permanente do Plex?`)) return
  try {
    const res = await fetch(`${API_BASE}/promote-artist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist: artistName })
    })
    const data = await res.json()
    if (res.ok) {
      alert(`⭐ Sucesso: ${data.message}`)
      await fetchDiscoveryQueue()
    } else {
      alert(`Erro: ${data.detail || 'Não foi possível mover os ficheiros.'}`)
    }
  } catch (e) {
    alert("Erro ao comunicar com o servidor.")
  }
}

function formatMs(ms) {
  if (!ms || ms <= 0) return '0:00'
  const totalSeconds = Math.floor(ms / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const padSec = seconds < 10 ? `0${seconds}` : seconds
  if (hours > 0) {
    const padMin = minutes < 10 ? `0${minutes}` : minutes
    return `${hours}:${padMin}:${padSec}`
  }
  return `${minutes}:${padSec}`
}

const API_BASE = '/api'

// Gravar estado do Piloto Automático
async function toggleAutoPilot() {
  try {
    await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_pilot: autoPilotEnabled.value })
    });
  } catch (e) {
    console.error("Erro ao gravar Piloto Automático:", e);
    // revert checkbox visually
    autoPilotEnabled.value = !autoPilotEnabled.value;
  }
}

// Gravar configuração de Artistas e Músicas por Artista
async function saveAutoPilotConfig() {
  try {
    const total = autoPilotArtistsLimit.value * autoPilotTracksPerArtist.value
    autoPilotLimit.value = total
    await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        auto_pilot_artists_limit: autoPilotArtistsLimit.value,
        auto_pilot_tracks_per_artist: autoPilotTracksPerArtist.value,
        auto_pilot_limit: total
      })
    });
  } catch (e) {
    console.error("Erro ao gravar configuração do Piloto Automático:", e);
  }
}

// Gravar Modo de Recomendação (Contextual vs Híbrido)
async function saveRecommendationMode() {
  try {
    await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recommendation_mode: recommendationMode.value })
    });
  } catch (e) {
    console.error("Erro ao gravar modo de recomendação:", e);
  }
}

// Gravar a Last.fm Key e Username no backend
async function saveLastFmSettings() {
  const payload = {}
  if (lastfmKeyInput.value.trim()) payload.lastfm_api_key = lastfmKeyInput.value.trim()
  if (lastfmUserInput.value.trim()) payload.lastfm_username = lastfmUserInput.value.trim()

  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      if (payload.lastfm_api_key) lastfmLinked.value = true;
      alert("Definições do Last.fm gravadas!");
    }
  } catch (e) {
    alert("Erro ao gravar definições do Last.fm.");
  }
}

// Gravar slskd settings no backend
async function saveSlskdSettings() {
  if (!slskdUrlInput.value.trim() || !slskdKeyInput.value.trim()) return;
  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slskd_url: slskdUrlInput.value.trim(),
        slskd_api_key: slskdKeyInput.value.trim()
      })
    });
    if (res.ok) {
      slskdLinked.value = true;
    }
  } catch (e) {
    alert("Erro ao gravar definições do slskd.");
  }
}

async function discover(artistName) {
  isDiscovering.value = true
  try {
    const res = await fetch(`${API_BASE}/discover?artist=${encodeURIComponent(artistName)}`)
    if (res.ok) {
      const data = await res.json()
      if (data.playlist) {
        data.playlist.forEach(t => t.status = 'pending')
      }
      discoveryResults.value = data
    } else {
      const err = await res.json()
      alert("Erro: " + (err.detail || "Falha ao contactar o Last.fm"))
    }
  } catch (e) {
    console.error(e)
    alert("Erro ao pedir recomendações.")
  } finally {
    isDiscovering.value = false
  }
}

async function downloadTrack(track) {
  track.status = 'downloading'
  try {
    const res = await fetch(`${API_BASE}/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist: track.artist, title: track.title })
    })
    
    if (res.ok) {
      track.status = 'success'
    } else {
      track.status = 'error'
    }
  } catch(e) {
    track.status = 'error'
  }
}

// 1. Ao iniciar, verifica se o backend já tem o Plex Token guardado
async function checkSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`)
    const data = await res.json()
    plexLinked.value = data.plex_linked
    lastfmLinked.value = data.lastfm_linked
    slskdLinked.value = data.slskd_linked
    autoPilotEnabled.value = data.auto_pilot
    autoPilotLimit.value = data.auto_pilot_limit || 20
    autoPilotArtistsLimit.value = data.auto_pilot_artists_limit || 15
    autoPilotTracksPerArtist.value = data.auto_pilot_tracks_per_artist || 1
    recommendationMode.value = data.recommendation_mode || 'contextual'
    lastfmUserInput.value = data.lastfm_username || ''
    
    if (plexLinked.value) {
      startNowPlayingPolling()
    }
    await fetchIgnoredArtists()
  } catch (e) {
    console.error("Erro ao ler settings:", e)
  } finally {
    loading.value = false
  }
}

// Verifica o que está a tocar e a fila a cada 4 segundos
function startNowPlayingPolling() {
  fetchNowPlaying()
  fetchDiscoveryQueue()
  if (nowPlayingInterval) clearInterval(nowPlayingInterval)
  nowPlayingInterval = setInterval(fetchNowPlaying, 4000)
  
  if (queueInterval) clearInterval(queueInterval)
  queueInterval = setInterval(fetchDiscoveryQueue, 4000)
}

async function fetchNowPlaying() {
  try {
    const res = await fetch(`${API_BASE}/now-playing`)
    if (res.ok) {
      nowPlaying.value = await res.json()
    }
  } catch (e) {
    console.error("Erro ao obter música atual:", e)
  }
}

async function fetchDiscoveryQueue() {
  try {
    const res = await fetch(`${API_BASE}/discovery-queue`)
    if (res.ok) {
      discoveryQueue.value = await res.json()
    }
  } catch (e) {
    console.error("Erro ao obter fila de descoberta:", e)
  }
}

async function clearQueue() {
  try {
    await fetch(`${API_BASE}/discovery-queue`, { method: 'DELETE' })
    discoveryQueue.value = []
  } catch (e) {
    console.error("Erro ao limpar fila:", e)
  }
}

// 2. Pede ao backend para gerar um PIN e um Link de Login do Plex
async function startPlexAuth() {
  try {
    const res = await fetch(`${API_BASE}/auth/plex/login?forwardUrl=${encodeURIComponent(window.location.origin)}`)
    const data = await res.json()
    authUrl.value = data.oauth_url
    pinId.value = data.pin_id
  } catch (e) {
    alert("Erro ao contactar o servidor PlexDiscover.")
  }
}

// 3. Fica a fazer "polling" ao backend a cada 2 segundos até autorizares
function startChecking() {
  isChecking.value = true
  
  if (checkInterval) clearInterval(checkInterval)
  
  checkInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/plex/check/${pinId.value}`)
      const data = await res.json()
      
      if (data.status === 'success') {
        clearInterval(checkInterval)
        plexLinked.value = true
        isChecking.value = false
        startNowPlayingPolling()
      }
    } catch (e) {
      console.error(e)
    }
  }, 2000)
}

onMounted(() => {
  checkSettings()
})
</script>

<style scoped>
.container { 
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: 600px; 
  margin: 60px auto; 
  text-align: center; 
}
h1 { color: #e5a00d; }
.btn { 
  background: #e5a00d; 
  color: white; 
  border: none; 
  padding: 12px 24px; 
  font-size: 16px; 
  font-weight: bold;
  cursor: pointer; 
  border-radius: 6px; 
  text-decoration: none; 
  display: inline-block; 
  margin-top: 15px;
}
.btn:hover { background: #c68a0a; }
.btn-outline { 
  background: transparent; 
  border: 2px solid #e5a00d; 
  color: #e5a00d; 
}
.btn-outline:hover {
  background: #e5a00d;
  color: white;
}
.input-text {
  padding: 10px;
  width: 80%;
  max-width: 300px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-right: 10px;
}
.status-msg { margin-top: 25px; color: #666; font-style: italic; font-size: 14px; }
.dashboard { padding: 30px; border: 1px solid #eee; border-radius: 12px; background: #fafafa; }
.subtitle { color: #777; font-size: 14px; margin-top: 10px; }

.now-playing-card, .discovery-card {
  margin-top: 30px;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}
.track-info p { margin: 8px 0; }
.meta { font-size: 12px; color: #999; margin-top: 15px; }
.spin-disc { font-size: 40px; margin-bottom: 15px; animation: spin 4s linear infinite; }
.spin-disc.paused { animation-play-state: paused; opacity: 0.6; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.playlist { margin-top: 20px; text-align: left; }
.track-item { 
  display: flex; 
  justify-content: space-between; 
  align-items: center;
  padding: 12px; 
  border-bottom: 1px solid #eee; 
}
.track-item:last-child { border-bottom: none; }
.badge { 
  font-size: 11px; 
  padding: 4px 8px; 
  border-radius: 12px; 
  font-weight: bold; 
}
.badge.pending { background: #eee; color: #666; }
.badge.success { background: #d4edda; color: #155724; }
.badge.error { background: #f8d7da; color: #721c24; }
.btn-sm { padding: 6px 12px; font-size: 13px; margin-top: 0; }

/* Novo Layout do Player e Capa */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
  margin-bottom: 16px;
}
.card-header h3 { margin: 0; }
.status-pill {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  font-weight: bold;
  background: #e8f5e9;
  color: #2e7d32;
}
.status-pill.paused {
  background: #fff3e0;
  color: #ef6c00;
}
.player-layout {
  display: flex;
  gap: 24px;
  align-items: center;
  text-align: left;
}
@media (max-width: 600px) {
  .player-layout { flex-direction: column; text-align: center; }
}
.album-art-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  flex-shrink: 0;
}
.album-art {
  width: 140px;
  height: 140px;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  position: relative;
  z-index: 2;
}
.album-art-placeholder {
  width: 140px;
  height: 140px;
  border-radius: 8px;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
}
.vinyl-disc {
  position: absolute;
  top: 15px;
  right: -20px;
  font-size: 80px;
  line-height: 1;
  z-index: 1;
  opacity: 0.8;
  animation: spin 5s linear infinite;
}
.vinyl-disc.paused {
  animation-play-state: paused;
  opacity: 0.4;
}
.player-details {
  flex-grow: 1;
  min-width: 0;
}
.track-title {
  font-size: 20px;
  margin: 0 0 6px 0;
  color: #222;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-artist, .track-album {
  margin: 4px 0;
  font-size: 14px;
  color: #444;
}
.album-progress-box {
  background: #f8f9fa;
  border: 1px solid #eaeaea;
  border-radius: 8px;
  padding: 10px 14px;
  margin: 12px 0;
}
.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}
.remaining-time {
  color: #0066cc;
}
.progress-bar-bg {
  width: 100%;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #e5a00d, #ffc107);
  transition: width 0.4s ease;
}
.time-sub {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}
.non-album-tag {
  display: inline-block;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  margin: 10px 0;
}
.actions-row {
  margin-top: 10px;
}

/* Fila de Descoberta */
.queue-card { text-align: left; }
.btn-text {
  background: none;
  border: none;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
}
.btn-text:hover { color: #555; }
.queue-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.queue-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #fdfdfd;
  border: 1px solid #eee;
  border-radius: 6px;
}
.queue-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}
.queue-index {
  font-size: 12px;
  font-weight: bold;
  color: #bbb;
  width: 16px;
}
.queue-artist {
  color: #222;
}
.queue-title {
  color: #666;
}
.queue-detail {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}
.badge-searching { background: #e3f2fd; color: #1565c0; }
.badge-downloading { background: #fff8e1; color: #f57f17; }
.badge-tagging { background: #ede7f6; color: #512da8; }
.badge-imported { background: #e0f2f1; color: #00695c; }
.badge-injected { background: #e8f5e9; color: #2e7d32; }
.badge-error { background: #ffebee; color: #c62828; }

.queue-right-col {
  display: flex;
  align-items: center;
  gap: 12px;
}
.queue-actions {
  display: flex;
  gap: 6px;
}
.btn-action {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.btn-promote {
  background: #fff8e1;
  color: #b78103;
  border-color: #ffe082;
}
.btn-promote:hover {
  background: #ffecb3;
  color: #8c6000;
}
.btn-ignore {
  background: #f5f5f5;
  color: #666;
  border-color: #ddd;
}
.btn-ignore:hover {
  background: #ffebee;
  color: #c62828;
  border-color: #ffcdd2;
}

/* Chips de Artistas Ignorados */
.ignored-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.ignored-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #eee;
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 12px;
  color: #444;
}
.chip-remove {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
  display: flex;
  align-items: center;
}
.chip-remove:hover {
  color: #c62828;
}

/* Navegação por Separadores */
.main-tabs {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}
.tab-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 10px 22px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tab-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}
.tab-btn.active {
  background: #0066cc;
  border-color: #0066cc;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 102, 204, 0.25);
}
</style>
