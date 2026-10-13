<template>
  <div class="app-shell">
    <!-- Header Brand Bar & Live Integration Status -->
    <header class="app-header">
      <div class="brand">
        <div class="brand-icon">🎧</div>
        <div class="brand-text">
          <h1>PlexDiscover</h1>
          <span class="brand-tag">Hi-Fi Autonomous Discovery</span>
        </div>
      </div>
      
      <div v-if="plexLinked" class="system-status-pills">
        <div :class="['status-dot-pill', { active: plexLinked }]" title="Ligado ao Plex Media Server">
          <span class="dot"></span> Plex
        </div>
        <div :class="['status-dot-pill', { active: slskdLinked }]" title="Ligado ao Soulseek (slskd)">
          <span class="dot"></span> Soulseek
        </div>
        <div :class="['status-dot-pill', { active: lastfmLinked }]" title="Ligado à API do Last.fm">
          <span class="dot"></span> Last.fm
        </div>
      </div>
    </header>
    
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>A sincronizar com os servidores...</p>
    </div>
    
    <div v-else-if="!plexLinked" class="auth-section">
      <div class="auth-card">
        <div class="auth-icon">🔐</div>
        <h2>Ligar ao Plex</h2>
        <p>Para começar a descoberta e a injeção automática de músicas, conecta a tua conta Plex.</p>
        
        <div v-if="!authUrl" class="auth-actions">
          <button @click="startPlexAuth" class="btn btn-plex">Ligar conta Plex</button>
        </div>
        
        <div v-else class="auth-actions">
          <p class="auth-hint">Abre o link abaixo e autoriza a aplicação (abrirá noutro separador):</p>
          <a :href="authUrl" target="_blank" @click="startChecking" class="btn btn-plex">
            Autorizar no Plex
          </a>
          
          <p v-if="isChecking" class="status-msg">
            ⏳ A aguardar a tua autorização no browser...
          </p>
        </div>
      </div>
    </div>
    
    <div v-else class="app-layout">
      <!-- Barra de Navegação por Separadores -->
      <nav class="main-tabs">
        <button 
          :class="['tab-btn', { active: currentTab === 'dashboard' }]" 
          @click="currentTab = 'dashboard'"
        >
          <span class="tab-icon">🎧</span> Agora a Tocar & Fila
        </button>
        <button 
          :class="['tab-btn', { active: currentTab === 'settings' }]" 
          @click="currentTab = 'settings'"
        >
          <span class="tab-icon">⚙️</span> Definições
        </button>
      </nav>

      <!-- SEPARADOR: DASHBOARD & FILA -->
      <div v-if="currentTab === 'dashboard'" class="dashboard">
        <!-- Card Agora a Tocar Enriquecido com Ambient Glow -->
        <div class="now-playing-card" :class="{ 'is-active': nowPlaying && nowPlaying.is_playing }">
          <!-- Camada de Ambient Glow com a Capa -->
          <div 
            v-if="nowPlaying && nowPlaying.thumb" 
            class="ambient-glow"
            :style="{ backgroundImage: `url(${API_BASE}/plex/image?path=${encodeURIComponent(nowPlaying.thumb)})` }"
          ></div>

          <div class="card-header">
            <div class="header-title-box">
              <h3>Agora a Tocar no Plex</h3>
              <span v-if="nowPlaying && nowPlaying.player" class="player-device-tag">
                <span class="device-icon">{{ nowPlaying.player.toLowerCase().includes('carplay') ? '🚗' : '📱' }}</span>
                {{ nowPlaying.player }} <span v-if="nowPlaying.user">({{ nowPlaying.user }})</span>
              </span>
            </div>
            <div v-if="nowPlaying && nowPlaying.is_playing" class="status-pill-group">
              <span :class="['status-pill', nowPlaying.state]">
                <span v-if="nowPlaying.state !== 'paused'" class="soundwave">
                  <span></span><span></span><span></span><span></span>
                </span>
                {{ nowPlaying.state === 'paused' ? '⏸️ Em Pausa' : '▶️ A Tocar' }}
              </span>
            </div>
          </div>
          
          <div v-if="nowPlaying" class="track-info">
            <div v-if="nowPlaying.is_playing" class="player-layout">
              <!-- Capa do Álbum Limpa Hi-Fi -->
              <div class="album-art-wrapper">
                <img 
                  v-if="nowPlaying.thumb" 
                  :src="`${API_BASE}/plex/image?path=${encodeURIComponent(nowPlaying.thumb)}`" 
                  alt="Capa do Álbum" 
                  class="album-art" 
                />
                <div v-else class="album-art-placeholder">🎵</div>
              </div>

              <!-- Detalhes da Faixa e Álbum -->
              <div class="player-details">
                <h4 class="track-title">{{ nowPlaying.track }}</h4>
                <p class="track-artist">👤 <strong>{{ nowPlaying.artist }}</strong></p>
                <p class="track-album">💿 {{ nowPlaying.album }}</p>
                <div v-if="nowPlaying.is_favorite" class="favorite-indicator-badge">
                  ⭐ Marcada como Favorita no Plexamp (FLAC Agendado)
                </div>

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
                  <button class="btn btn-glass" @click="discover(nowPlaying.artist)" :disabled="isDiscovering">
                    {{ isDiscovering ? '⏳ A pesquisar...' : '🔍 Descobrir Semelhantes' }}
                  </button>

                  <!-- Só exibe o botão de sacar álbum se ainda NÃO estiver na biblioteca permanente -->
                  <button 
                    v-if="!nowPlaying.already_in_library"
                    class="btn btn-hifi" 
                    @click="favoriteAlbum(nowPlaying.artist, nowPlaying.album, nowPlaying.track)" 
                    :disabled="isFavoriting"
                    title="Pesquisa e descarrega o álbum completo em FLAC 16-bit / 44.1 kHz via slskd para a biblioteca permanente (/music)"
                  >
                    {{ isFavoriting ? '⏳ A agendar...' : '💿 Sacar Álbum FLAC (16/44)' }}
                  </button>
                  <div v-else class="badge-in-library" title="Este álbum já faz parte da tua coleção permanente (/music)">
                    ✓ Na Tua Biblioteca Permanente
                  </div>
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
                    @click="favoriteAlbum(item.artist, '', item.title)" 
                    class="btn-action btn-album-fav" 
                    title="Baixar álbum completo em FLAC 16/44 para a biblioteca permanente"
                  >
                    💿 Álbum FLAC
                  </button>
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

        <!-- Card de Álbuns Favoritados / Transferências FLAC 16/44 -->
        <div v-if="favoriteAlbums && favoriteAlbums.length > 0" class="discovery-card album-downloads-card">
          <div class="card-header">
            <div>
              <h3>💿 Álbuns Favoritos & Downloads FLAC (16-bit / 44.1 kHz)</h3>
              <p class="subtitle" style="margin-top: 2px;">
                Álbuns completos descarregados em qualidade CD diretamente para a tua biblioteca permanente (/music)
              </p>
            </div>
            <span class="badge badge-cd-count">{{ favoriteAlbums.length }} {{ favoriteAlbums.length === 1 ? 'álbum' : 'álbuns' }}</span>
          </div>

          <div class="album-cards-grid">
            <div v-for="alb in favoriteAlbums" :key="alb.id" class="album-item-card">
              <div class="album-item-top">
                <div class="album-meta-info">
                  <strong class="alb-artist">{{ alb.artist }}</strong>
                  <h4 class="alb-title">{{ alb.album }} <span v-if="alb.year" class="alb-year">({{ alb.year }})</span></h4>
                  <div class="alb-detail">{{ alb.detail }}</div>
                </div>

                <div class="alb-status-wrapper">
                  <span v-if="alb.status === 'searching'" class="badge badge-searching">🔍 A pesquisar no Soulseek...</span>
                  <span v-else-if="alb.status === 'downloading'" class="badge badge-downloading">⏳ A transferir ({{ alb.completed_tracks }}/{{ alb.total_tracks }})</span>
                  <span v-else-if="alb.status === 'tagging'" class="badge badge-tagging">🏷️ A etiquetar & verificar</span>
                  <span v-else-if="alb.status === 'completed'" class="badge badge-imported">✅ Guardado (/music)</span>
                  <span v-else-if="alb.status === 'already_exists'" class="badge badge-imported">✓ Já existente</span>
                  <span v-else-if="alb.status === 'error'" class="badge badge-error">❌ Erro</span>
                  <span v-else class="badge pending">Pendente</span>

                  <button 
                    @click="removeFavoriteAlbum(alb.id)" 
                    class="btn-delete-alb" 
                    title="Remover do histórico"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <!-- Barra de progresso para downloads ativos -->
              <div v-if="alb.status === 'downloading' && alb.total_tracks > 0" class="album-progress-bar-container">
                <div 
                  class="album-progress-bar-fill" 
                  :style="{ width: `${Math.min(100, Math.round((alb.completed_tracks / alb.total_tracks) * 100))}%` }"
                ></div>
                <span class="album-progress-text">{{ Math.round((alb.completed_tracks / alb.total_tracks) * 100) }}% ({{ alb.completed_tracks }}/{{ alb.total_tracks }} faixas)</span>
              </div>

              <div class="album-item-footer">
                <span class="badge-quality-flac">FLAC 16-bit / 44.1 kHz (CD Red Book)</span>
                <span v-if="alb.username" class="alb-user-tag">Soulseek: {{ alb.username }}</span>
              </div>
            </div>
          </div>
        </div>


        <!-- Card de Recomendações Manuais Last.fm (quando feito clique manual) -->
        <div v-if="discoveryResults" class="discovery-card rec-card">
          <div class="card-header">
            <div>
              <h3>🔍 Recomendações de Bandas Novas</h3>
              <p class="subtitle" style="margin-top: 2px;">
                Semelhantes a <strong>{{ discoveryResults.source_artist }}</strong> (excluindo bandas que já tens na biblioteca • 1 música por banda)
              </p>
            </div>
            <button @click="discoveryResults = null" class="btn-text">✕ Fechar</button>
          </div>
          
          <div v-if="discoveryResults.playlist && discoveryResults.playlist.length > 0" class="rec-list">
            <div v-for="(track, index) in discoveryResults.playlist" :key="index" class="rec-item">
              <div class="rec-art-box">
                <img v-if="track.image" :src="track.image" alt="Capa" class="rec-thumb" />
                <div v-else class="rec-thumb-placeholder">🎵</div>
              </div>
              <div class="rec-details">
                <strong class="rec-artist">{{ track.artist }}</strong>
                <span class="rec-track-title">{{ track.title }}</span>
              </div>
              <div class="rec-actions">
                <button 
                  v-if="!track.status || track.status === 'pending'" 
                  @click="downloadTrack(track)" 
                  class="btn-action btn-hifi"
                  title="Descarregar esta faixa para a fila de descoberta"
                >
                  ⚡ Descarregar Faixa
                </button>
                <button 
                  @click="favoriteAlbum(track.artist, '', track.title)" 
                  class="btn-action btn-album-fav" 
                  title="Descarregar o álbum completo em FLAC 16/44 para a tua biblioteca permanente (/music)"
                >
                  💿 Álbum FLAC
                </button>
                <span v-if="track.status === 'downloading'" class="badge badge-downloading">⏳ A procurar...</span>
                <span v-else-if="track.status === 'success'" class="badge badge-imported">✅ Agendado</span>
                <span v-else-if="track.status === 'error'" class="badge badge-error">❌ Erro</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-rec">
            <p>Todas as bandas mais semelhantes já fazem parte da tua biblioteca permanente!</p>
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

const favoriteAlbums = ref([])
const isFavoriting = ref(false)

async function fetchFavoriteAlbums() {
  try {
    const res = await fetch(`${API_BASE}/favorite-albums`)
    if (res.ok) {
      favoriteAlbums.value = await res.json()
    }
  } catch (e) {
    console.error("Erro ao carregar álbuns favoritos:", e)
  }
}

async function favoriteAlbum(artistName, albumName = '', trackTitle = '') {
  if (!artistName) return
  isFavoriting.value = true
  try {
    const res = await fetch(`${API_BASE}/favorite-album`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artist: artistName,
        album: albumName || '',
        track: trackTitle || ''
      })
    })
    const data = await res.json()
    if (res.ok) {
      await fetchFavoriteAlbums()
      alert(`⭐ Pedido registado: O PlexDiscover está à procura do álbum completo de "${artistName}" em FLAC 16/44 no Soulseek!`)
    } else {
      alert(`Erro: ${data.detail || data.message || 'Falha ao agendar álbum.'}`)
    }
  } catch (e) {
    alert("Erro de comunicação ao agendar download do álbum.")
  } finally {
    isFavoriting.value = false
  }
}

async function removeFavoriteAlbum(albumId) {
  try {
    const res = await fetch(`${API_BASE}/favorite-albums/${encodeURIComponent(albumId)}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      await fetchFavoriteAlbums()
    }
  } catch (e) {
    console.error("Erro ao remover álbum favorito:", e)
  }
}

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

// Verifica o que está a tocar, a fila e os álbuns favoritos a cada 4 segundos
function startNowPlayingPolling() {
  fetchNowPlaying()
  fetchDiscoveryQueue()
  fetchFavoriteAlbums()
  if (nowPlayingInterval) clearInterval(nowPlayingInterval)
  nowPlayingInterval = setInterval(fetchNowPlaying, 4000)
  
  if (queueInterval) clearInterval(queueInterval)
  queueInterval = setInterval(() => {
    fetchDiscoveryQueue()
    fetchFavoriteAlbums()
  }, 4000)
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
.app-shell {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 20px 80px;
  min-height: 100vh;
}

/* Header Brand Bar */
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 24px;
  box-shadow: var(--shadow-card);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-icon {
  font-size: 32px;
  line-height: 1;
  filter: drop-shadow(0 0 12px var(--accent-plex-glow));
}

.brand-text h1 {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-tag {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-plex);
}

/* Status Pills */
.system-status-pills {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.status-dot-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.status-dot-pill .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  transition: all 0.2s ease;
}

.status-dot-pill.active {
  color: var(--text-primary);
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
}

.status-dot-pill.active .dot {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

/* Loading & Auth State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent-plex);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

.auth-section {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.auth-card {
  max-width: 460px;
  width: 100%;
  padding: 36px 30px;
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  text-align: center;
}

.auth-icon {
  font-size: 44px;
  margin-bottom: 16px;
}

.auth-card h2 {
  font-size: 24px;
  margin-bottom: 10px;
}

.auth-card p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.btn-plex {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #000;
  font-weight: 700;
  border: none;
  padding: 12px 28px;
  border-radius: var(--radius-md);
  font-size: 15px;
  cursor: pointer;
  box-shadow: 0 4px 16px var(--accent-plex-glow);
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-block;
  margin-top: 16px;
}

.btn-plex:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(245, 158, 11, 0.4);
}

.auth-hint {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 14px;
}

.status-msg {
  color: var(--accent-plex);
  font-size: 14px;
  margin-top: 16px;
}

/* Tabs Navigation */
.main-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  background: rgba(18, 20, 32, 0.6);
  padding: 6px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-subtle);
  width: fit-content;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border-radius: var(--radius-full);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.25s ease;
}

.tab-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  color: #ffffff;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.9) 0%, rgba(217, 119, 6, 0.9) 100%);
  box-shadow: 0 4px 16px var(--accent-plex-glow);
}

/* Now Playing Card */
.now-playing-card {
  position: relative;
  background: var(--bg-card);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: all 0.3s ease;
}

.now-playing-card.is-active {
  border-color: rgba(245, 158, 11, 0.35);
  box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.6), 0 0 25px -5px var(--accent-plex-glow);
}

.ambient-glow {
  position: absolute;
  top: -20%;
  left: -10%;
  width: 120%;
  height: 140%;
  background-size: cover;
  background-position: center;
  filter: blur(80px) saturate(180%);
  opacity: 0.18;
  pointer-events: none;
  z-index: 0;
  transition: opacity 0.5s ease;
}

.now-playing-card.is-active .ambient-glow {
  opacity: 0.28;
}

.card-header {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 22px;
}

.header-title-box {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.card-header h3 {
  font-size: 18px;
  font-weight: 700;
}

.player-device-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-pill-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  background: var(--color-success-bg);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #34d399;
}

.status-pill.paused {
  background: var(--color-warning-bg);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

/* Soundwave Equalizer Animation */
.soundwave {
  display: inline-flex;
  align-items: flex-end;
  gap: 3px;
  height: 14px;
}

.soundwave span {
  width: 3px;
  background: #34d399;
  border-radius: 2px;
  animation: soundwaveBar 1.2s ease-in-out infinite;
}

.soundwave span:nth-child(1) { height: 40%; animation-delay: 0.1s; }
.soundwave span:nth-child(2) { height: 90%; animation-delay: 0.3s; }
.soundwave span:nth-child(3) { height: 60%; animation-delay: 0.2s; }
.soundwave span:nth-child(4) { height: 100%; animation-delay: 0.4s; }

@keyframes soundwaveBar {
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1); }
}

/* Player Layout */
.track-info {
  position: relative;
  z-index: 1;
}

.player-layout {
  display: flex;
  gap: 32px;
  align-items: center;
}

@media (max-width: 768px) {
  .player-layout {
    flex-direction: column;
    text-align: center;
    gap: 20px;
  }
}

.album-art-wrapper {
  position: relative;
  width: 170px;
  height: 170px;
  flex-shrink: 0;
}

.album-art {
  width: 170px;
  height: 170px;
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 2;
}

.album-art-placeholder {
  width: 170px;
  height: 170px;
  border-radius: var(--radius-md);
  background: var(--bg-surface-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 50px;
  border: 1px solid var(--border-subtle);
}


.player-details {
  flex-grow: 1;
  min-width: 0;
}

.track-title {
  font-size: 26px;
  font-weight: 800;
  margin: 0 0 8px 0;
  color: var(--text-primary);
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.track-artist {
  margin: 4px 0;
  font-size: 16px;
  color: var(--accent-plex);
  font-weight: 600;
}

.track-album {
  margin: 4px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.favorite-indicator-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #fbbf24;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: 12px;
  margin-top: 10px;
}

/* Progress Box */
.album-progress-box {
  background: rgba(10, 11, 18, 0.6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin: 14px 0;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.remaining-time {
  color: var(--color-cyan);
  font-family: var(--font-mono);
}

.progress-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-plex), var(--accent-hifi));
  transition: width 0.4s ease;
  box-shadow: 0 0 10px var(--accent-plex-glow);
}

.time-sub {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  margin-top: 6px;
}

.non-album-tag {
  display: inline-block;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-muted);
  margin: 10px 0;
}

.actions-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

/* Glass & HiFi Buttons */
.btn-glass {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  font-weight: 600;
  font-size: 13px;
  padding: 10px 18px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-glass:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-hifi {
  background: linear-gradient(135deg, var(--accent-hifi) 0%, var(--accent-hifi-hover) 100%);
  color: #ffffff;
  border: none;
  font-weight: 700;
  font-size: 13px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  box-shadow: 0 4px 16px var(--accent-hifi-glow);
  transition: all 0.2s ease;
}

.btn-hifi:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.45);
}

.btn-hifi:disabled, .btn-glass:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state .subtitle {
  color: var(--text-muted);
  font-size: 13px;
  margin-top: 6px;
}

/* Real-Time Queue Card */
.discovery-card {
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-card);
}

.discovery-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.subtitle {
  color: var(--text-secondary);
  font-size: 13px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s ease;
}

.btn-text:hover {
  color: var(--text-primary);
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.queue-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(18, 20, 32, 0.7);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
  flex-wrap: wrap;
  gap: 12px;
}

.queue-row:hover {
  background: rgba(28, 32, 50, 0.8);
  border-color: rgba(255, 255, 255, 0.12);
}

.queue-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 200px;
}

.queue-index {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  font-family: var(--font-mono);
  width: 20px;
}

.queue-artist {
  color: var(--text-primary);
  font-size: 14px;
}

.queue-title {
  color: var(--text-secondary);
  font-size: 14px;
}

.queue-detail {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
}

.queue-right-col {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: var(--radius-full);
}

.badge-searching {
  background: var(--color-cyan-bg);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.badge-downloading {
  background: var(--color-warning-bg);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.badge-tagging {
  background: var(--accent-hifi-glow);
  color: #c084fc;
  border: 1px solid rgba(192, 132, 252, 0.3);
}

.badge-imported {
  background: var(--color-success-bg);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.badge-injected {
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
  border: 1px solid rgba(110, 231, 183, 0.4);
}

.badge-error {
  background: var(--color-error-bg);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.3);
}

.badge.pending {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
}

.queue-actions {
  display: flex;
  gap: 6px;
}

.btn-action {
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-album-fav {
  background: var(--accent-hifi-glow);
  color: #c084fc;
  border-color: rgba(192, 132, 252, 0.4);
}

.btn-album-fav:hover {
  background: rgba(139, 92, 246, 0.35);
  color: #ffffff;
}

.btn-promote {
  background: var(--accent-plex-glow);
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.4);
}

.btn-promote:hover {
  background: rgba(245, 158, 11, 0.35);
  color: #ffffff;
}

.btn-ignore {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
  border-color: var(--border-subtle);
}

.btn-ignore:hover {
  background: var(--color-error-bg);
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.4);
}

/* Album Downloads Card */
.badge-cd-count {
  background: var(--accent-hifi-glow);
  color: #c084fc;
  border: 1px solid rgba(192, 132, 252, 0.4);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 700;
}

.album-cards-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.album-item-card {
  background: rgba(18, 20, 32, 0.7);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.album-item-card:hover {
  background: rgba(24, 28, 44, 0.85);
  border-color: rgba(255, 255, 255, 0.15);
}

.album-item-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.album-meta-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alb-artist {
  color: var(--accent-plex);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.alb-title {
  margin: 0;
  font-size: 17px;
  color: var(--text-primary);
  font-weight: 700;
}

.alb-year {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 14px;
}

.alb-detail {
  font-size: 13px;
  color: var(--text-secondary);
}

.alb-status-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-delete-alb {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}

.btn-delete-alb:hover {
  color: #f87171;
  background: var(--color-error-bg);
}

.album-progress-bar-container {
  position: relative;
  height: 20px;
  background: rgba(10, 11, 18, 0.7);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  overflow: hidden;
  display: flex;
  align-items: center;
}

.album-progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-hifi) 0%, #a855f7 100%);
  border-radius: var(--radius-full);
  transition: width 0.4s ease;
  box-shadow: 0 0 12px var(--accent-hifi-glow);
}

.album-progress-text {
  position: absolute;
  width: 100%;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  font-family: var(--font-mono);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}

.album-item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.badge-quality-flac {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 11px;
  font-family: var(--font-mono);
}

.alb-user-tag {
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

/* In Library Badge */
.badge-in-library {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.4);
  color: #34d399;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

/* Playlist & Manual Discovery */
.rec-card {
  margin-top: 24px;
}

.rec-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.rec-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: rgba(18, 20, 32, 0.7);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  gap: 16px;
  flex-wrap: wrap;
  transition: all 0.2s ease;
}

.rec-item:hover {
  background: rgba(26, 30, 48, 0.85);
  border-color: rgba(255, 255, 255, 0.15);
}

.rec-art-box {
  width: 54px;
  height: 54px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
}

.rec-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.rec-thumb-placeholder {
  font-size: 22px;
  color: var(--text-muted);
}

.rec-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 180px;
}

.rec-artist {
  color: var(--accent-plex);
  font-size: 14px;
  font-weight: 700;
}

.rec-track-title {
  color: var(--text-primary);
  font-size: 14px;
}

.rec-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-rec {
  padding: 28px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
  font-style: italic;
}
</style>
