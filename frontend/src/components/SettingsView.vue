<template>
  <div class="settings-view">
    <div class="settings-header">
      <h2>⚙️ Definições do Sistema</h2>
      <p class="subtitle">Personaliza a automação, a estratégia de descoberta de músicas e as integrações.</p>
    </div>

    <!-- 1. Descoberta Inteligente & Buffer Progressivo -->
    <div class="settings-card">
      <div class="card-title-row">
        <span class="card-icon">⚡</span>
        <div>
          <h3>Descoberta Inteligente & Buffer (Lazy Loading)</h3>
          <p class="card-sub">Controla a forma como o PlexDiscover obtém e injeta novas faixas no Plexamp.</p>
        </div>
      </div>

      <div class="setting-group">
        <label class="setting-label">Estratégia de Descoberta</label>
        <div class="radio-cards">
          <label :class="['radio-card', { active: settings.discovery_strategy === 'progressive' }]">
            <input 
              type="radio" 
              value="progressive" 
              v-model="settings.discovery_strategy" 
              @change="saveProgressiveSettings" 
            />
            <div class="radio-content">
              <strong>🚀 Buffer Progressivo (Recomendado)</strong>
              <p>Saca apenas 5 músicas no início e vai sacando mais à medida que ouves e a fila progride. Poupa rede e evita faixas não ouvidas.</p>
            </div>
          </label>

          <label :class="['radio-card', { active: settings.discovery_strategy === 'fixed' }]">
            <input 
              type="radio" 
              value="fixed" 
              v-model="settings.discovery_strategy" 
              @change="saveProgressiveSettings" 
            />
            <div class="radio-content">
              <strong>📦 Lote Fixo Tradicional</strong>
              <p>Descarrega todas as músicas recomendadas de uma só vez logo no início do álbum.</p>
            </div>
          </label>
        </div>
      </div>

      <!-- Configurações do Buffer Progressivo -->
      <div v-if="settings.discovery_strategy === 'progressive'" class="progressive-options">
        <div class="grid-2col">
          <div class="form-field">
            <label class="field-label">
              Tamanho do Lote (Batch Size)
              <span class="help-tooltip" title="Quantas músicas são descarregadas em cada vaga">ℹ️</span>
            </label>
            <select v-model.number="settings.batch_size" @change="saveProgressiveSettings" class="select-input">
              <option :value="3">3 músicas por lote</option>
              <option :value="5">5 músicas por lote (Recomendado)</option>
              <option :value="8">8 músicas por lote</option>
              <option :value="10">10 músicas por lote</option>
            </select>
            <span class="field-hint">Inicia com {{ settings.batch_size }} músicas no final do álbum.</span>
          </div>

          <div class="form-field">
            <label class="field-label">
              Margem de Segurança (Buffer Trigger)
              <span class="help-tooltip" title="Quando faltarem estas faixas na fila do Plexamp, o sistema puxa o próximo lote">ℹ️</span>
            </label>
            <select v-model.number="settings.buffer_trigger" @change="saveProgressiveSettings" class="select-input">
              <option :value="1">Quando faltar 1 música</option>
              <option :value="2">Quando faltarem 2 músicas (Recomendado)</option>
              <option :value="3">Quando faltarem 3 músicas (Mais seguro)</option>
              <option :value="4">Quando faltarem 4 músicas</option>
            </select>
            <span class="field-hint">Garante tempo suficiente para download e indexação antes da fila acabar.</span>
          </div>
        </div>

        <div class="form-field" style="margin-top: 14px;">
          <label class="field-label">
            Limite Máximo por Sessão / Álbum
            <span class="help-tooltip" title="Evita downloads infinitos se adormeceres a ouvir música">ℹ️</span>
          </label>
          <select v-model.number="settings.max_session_tracks" @change="saveProgressiveSettings" class="select-input">
            <option :value="10">Máximo 10 músicas (2 lotes de 5)</option>
            <option :value="15">Máximo 15 músicas (3 lotes de 5)</option>
            <option :value="20">Máximo 20 músicas (Recomendado)</option>
            <option :value="30">Máximo 30 músicas</option>
            <option :value="0">♾️ Ilimitado (Rádio Contínua Sem Fim)</option>
          </select>
          <span class="field-hint">
            {{ settings.max_session_tracks === 0 ? 'A rádio de descoberta nunca para enquanto continuares a ouvir.' : `O sistema para de descarregar após atingir ${settings.max_session_tracks} músicas nesta sessão.` }}
          </span>
        </div>
      </div>
    </div>

    <!-- 2. Piloto Automático & Recomendações -->
    <div class="settings-card">
      <div class="card-title-row">
        <span class="card-icon">🤖</span>
        <div>
          <h3>Piloto Automático (Auto-Pilot)</h3>
          <p class="card-sub">Automação contínua ao iniciar a reprodução de um álbum no Plexamp.</p>
        </div>
      </div>

      <div class="toggle-row">
        <div>
          <strong>Ativar Piloto Automático</strong>
          <p class="field-hint">Quando ativo, deteta álbuns a tocar no Plexamp e prepara descobertas sem intervenção manual.</p>
        </div>
        <label class="switch">
          <input type="checkbox" v-model="settings.auto_pilot" @change="saveAutoPilot" />
          <span class="slider"></span>
        </label>
      </div>

      <div v-if="settings.auto_pilot" class="auto-pilot-settings">
        <div class="grid-2col">
          <div class="form-field">
            <label class="field-label">Músicas por Artista Recomendado</label>
            <select v-model.number="settings.auto_pilot_tracks_per_artist" @change="saveAutoPilotConfig" class="select-input">
              <option :value="1">1 música por artista (Máxima variedade)</option>
              <option :value="2">2 músicas por artista</option>
              <option :value="3">3 músicas por artista</option>
            </select>
          </div>

          <div class="form-field" v-if="settings.discovery_strategy === 'fixed'">
            <label class="field-label">Artistas a Explorar (Modo Fixo)</label>
            <select v-model.number="settings.auto_pilot_artists_limit" @change="saveAutoPilotConfig" class="select-input">
              <option :value="5">5 artistas</option>
              <option :value="10">10 artistas</option>
              <option :value="15">15 artistas (Recomendado)</option>
              <option :value="20">20 artistas</option>
              <option :value="30">30 artistas</option>
            </select>
          </div>
        </div>

        <div class="form-field" style="margin-top: 16px;">
          <label class="field-label">Modo de Recomendação</label>
          <div class="radio-inline-group">
            <label class="radio-inline">
              <input type="radio" value="contextual" v-model="settings.recommendation_mode" @change="saveRecommendationMode" />
              <span><strong>100% Contextual</strong> (Baseado estritamente no álbum atual)</span>
            </label>
            <label class="radio-inline">
              <input type="radio" value="hybrid" v-model="settings.recommendation_mode" @change="saveRecommendationMode" />
              <span><strong>Híbrido 70/30</strong> (70% Álbum atual + 30% Histórico Last.fm)</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 2.5. Álbuns Favoritos & Download Automático (FLAC 16/44) -->
    <div class="settings-card">
      <div class="card-title-row">
        <span class="card-icon">⭐</span>
        <div>
          <h3>Álbuns Favoritos & Download Automático em FLAC (16/44)</h3>
          <p class="card-sub">Ao favoritares uma música no Plexamp, o PlexDiscover descarrega automaticamente o álbum completo em qualidade CD (FLAC 16-bit / 44.1 kHz) para a tua biblioteca permanente (/music).</p>
        </div>
      </div>

      <div class="setting-group">
        <div class="toggle-row">
          <div>
            <strong>Download Automático ao Favoritar</strong>
            <p class="field-hint">Deteta quando avalias uma música com ⭐ (ou ❤️ coração) no Plexamp ou via Webhook do Plex e obtém o álbum completo via Soulseek (slskd).</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.auto_download_favorite_albums" 
              @change="saveFavoriteAlbumSettings"
            />
            <span class="slider round"></span>
          </label>
        </div>
      </div>

      <div class="setting-group" style="margin-top: 14px;">
        <label class="setting-label">Formato & Qualidade de Áudio</label>
        <div class="form-field">
          <select v-model="settings.favorite_album_quality" @change="saveFavoriteAlbumSettings" class="select-input">
            <option value="flac_16_44">FLAC 16-bit / 44.1 kHz (Qualidade CD Red Book - Recomendado)</option>
          </select>
          <span class="field-hint">Filtra e prioriza pastas que contenham os metadados do CD oficial, evitando Hi-Res com tamanhos astronómicos ou perdas de compressão.</span>
        </div>
      </div>

      <!-- Webhook do Plex -->
      <div class="setting-group webhook-box">
        <label class="setting-label">
          <span>⚡ Webhook do Plex (Deteção Instantânea)</span>
        </label>
        <p class="field-hint" style="margin-bottom: 8px;">
          Configura este webhook nas definições do teu Plex Media Server (<strong>Definições → Webhooks → Adicionar Webhook</strong>) para descarregar o álbum no mesmo segundo em que favoritadas uma faixa:
        </p>
        <div class="webhook-input-row">
          <input 
            type="text" 
            readonly 
            :value="plexWebhookUrl" 
            class="text-input webhook-input" 
          />
          <button @click="copyWebhookUrl" class="btn btn-sm" style="white-space: nowrap;">
            {{ copiedWebhook ? '✓ Copiado!' : '📋 Copiar URL' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Contas & Integrações -->
    <div class="settings-card">
      <div class="card-title-row">
        <span class="card-icon">🔑</span>
        <div>
          <h3>Contas & Ligações</h3>
          <p class="card-sub">Credenciais e ligações necessárias para Plex, Last.fm e slskd.</p>
        </div>
      </div>

      <!-- Plex -->
      <div class="integration-block">
        <div class="integration-header">
          <div>
            <strong>Plex Media Server</strong>
            <p class="field-hint">Servidor Plex onde as bibliotecas e a PlayQueue são geridas.</p>
          </div>
          <span v-if="settings.plex_linked" class="badge-status success">✅ Ligado</span>
          <span v-else class="badge-status warning">⚠️ Não Ligado</span>
        </div>

        <div class="grid-2col" style="margin-top: 14px;">
          <div class="form-field">
            <label class="field-label">
              Biblioteca de Descoberta (Plex)
              <span class="help-tooltip" title="Nome da biblioteca no Plex que aponta para a pasta temporária">ℹ️</span>
            </label>
            <input 
              type="text" 
              v-model="settings.plex_discovery_library" 
              @change="savePlexLibraries"
              placeholder="Discover" 
              class="text-input" 
            />
            <span class="field-hint">Pasta no Synology: <code>/volume1/Media/Misc/MusicDiscovery</code></span>
          </div>

          <div class="form-field">
            <label class="field-label">
              Biblioteca Principal (Plex)
              <span class="help-tooltip" title="Nome da tua biblioteca permanente principal onde ficam os álbuns guardados">ℹ️</span>
            </label>
            <input 
              type="text" 
              v-model="settings.plex_permanent_library" 
              @change="savePlexLibraries"
              placeholder="Music" 
              class="text-input" 
            />
            <span class="field-hint">Pasta no Synology: <code>/volume1/Media/Music</code></span>
          </div>
        </div>
      </div>

      <hr class="divider" />

      <!-- Last.fm -->
      <div class="integration-block">
        <div class="integration-header">
          <div>
            <strong>Last.fm</strong>
            <p class="field-hint">Utilizado para calcular artistas semelhantes, popularidade de faixas e modo híbrido.</p>
          </div>
          <span v-if="settings.lastfm_linked" class="badge-status success">✅ Ligado</span>
          <span v-else class="badge-status warning">⚠️ Não Configurado</span>
        </div>

        <div class="grid-2col" style="margin-top: 10px;">
          <div class="form-field">
            <label class="field-label">Utilizador Last.fm (para Modo Híbrido)</label>
            <input 
              type="text" 
              v-model="lastfmUser" 
              placeholder="ex: teu_utilizador" 
              class="text-input" 
            />
          </div>
          <div class="form-field">
            <label class="field-label">API Key do Last.fm</label>
            <input 
              type="password" 
              v-model="lastfmKey" 
              placeholder="Inserir nova chave para atualizar..." 
              class="text-input" 
            />
          </div>
        </div>
        <button @click="submitLastfm" class="btn btn-sm" style="margin-top: 10px;">Gravar Last.fm</button>
      </div>

      <hr class="divider" />

      <!-- slskd -->
      <div class="integration-block">
        <div class="integration-header">
          <div>
            <strong>slskd (Soulseek Daemon)</strong>
            <p class="field-hint">Instância slskd responsável por pesquisar e transferir faixas autorizadas.</p>
          </div>
          <span v-if="settings.slskd_linked" class="badge-status success">✅ Ligado</span>
          <span v-else class="badge-status warning">⚠️ Não Configurado</span>
        </div>

        <div class="grid-2col" style="margin-top: 10px;">
          <div class="form-field">
            <label class="field-label">URL do slskd</label>
            <input 
              type="text" 
              v-model="slskdUrl" 
              placeholder="http://10.0.0.2:5030" 
              class="text-input" 
            />
          </div>
          <div class="form-field">
            <label class="field-label">API Key do slskd</label>
            <input 
              type="password" 
              v-model="slskdKey" 
              placeholder="Inserir API Key do slskd..." 
              class="text-input" 
            />
          </div>
        </div>
        <button @click="submitSlskd" class="btn btn-sm" style="margin-top: 10px;">Gravar slskd</button>
      </div>
    </div>

    <!-- 4. Artistas Ignorados (Lista Negra) -->
    <div class="settings-card">
      <div class="card-title-row">
        <span class="card-icon">🚫</span>
        <div>
          <h3>Artistas Ignorados (Lista Negra)</h3>
          <p class="card-sub">Artistas bloqueados que nunca serão sugeridos nem descarregados pelo Piloto Automático.</p>
        </div>
      </div>

      <div class="add-ignored-row">
        <input 
          type="text" 
          v-model="newIgnoredArtist" 
          @keyup.enter="submitAddIgnored" 
          placeholder="Nome do artista a bloquear (ex: Coldplay)..." 
          class="text-input" 
        />
        <button @click="submitAddIgnored" class="btn btn-sm">Adicionar à Lista Negra</button>
      </div>

      <div v-if="ignoredArtists && ignoredArtists.length > 0" class="ignored-chips-container">
        <span v-for="art in ignoredArtists" :key="art" class="ignored-chip">
          {{ art }}
          <button @click="removeIgnored(art)" class="chip-remove" title="Remover da lista negra">✕</button>
        </span>
      </div>
      <p v-else class="empty-hint">Nenhum artista na lista negra. Podes adicionar manualmente acima ou clicar em 'Ignorar' na fila.</p>
    </div>

    <!-- 5. Manutenção & Limpeza da Biblioteca -->
    <div class="settings-card danger-zone-card">
      <div class="card-title-row">
        <span class="card-icon">🧹</span>
        <div>
          <h3>Manutenção & Limpeza da Biblioteca</h3>
          <p class="card-sub">Apaga todos os ficheiros temporários da pasta <code>/music_discovery</code>, limpa a fila de sessões e força a purga no Plex imediatamente.</p>
        </div>
      </div>

      <div class="cleanup-action-box">
        <div class="cleanup-info">
          <strong>Limpar Biblioteca de Descoberta Agora</strong>
          <p class="field-hint">Útil para reiniciar testes do zero ou libertar espaço. Todas as músicas temporárias serão apagadas e a biblioteca no Plex/Plexamp ficará limpa.</p>
        </div>
        <button 
          @click="triggerManualCleanup" 
          :disabled="isCleaning"
          class="btn btn-danger"
        >
          <span v-if="isCleaning">⏳ A Limpar e a Purgar Plex...</span>
          <span v-else>🗑️ Limpar Biblioteca de Descoberta</span>
        </button>
      </div>
      <p v-if="cleanupMessage" :class="['cleanup-status-feedback', cleanupSuccess ? 'success' : 'error']">
        {{ cleanupMessage }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  apiBase: {
    type: String,
    default: '/api'
  }
})

const emit = defineEmits(['settings-updated'])

const settings = ref({
  plex_linked: false,
  lastfm_linked: false,
  lastfm_username: '',
  slskd_linked: false,
  auto_pilot: false,
  auto_pilot_limit: 15,
  auto_pilot_artists_limit: 15,
  auto_pilot_tracks_per_artist: 1,
  recommendation_mode: 'contextual',
  discovery_strategy: 'progressive',
  batch_size: 5,
  buffer_trigger: 2,
  max_session_tracks: 20,
  plex_discovery_library: 'Discover',
  plex_permanent_library: 'Music',
  auto_download_favorite_albums: true,
  favorite_album_quality: 'flac_16_44'
})

const copiedWebhook = ref(false)
const plexWebhookUrl = computed(() => {
  return `${window.location.protocol}//${window.location.hostname}:8788/api/plex-webhook`
})

function copyWebhookUrl() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(plexWebhookUrl.value)
    copiedWebhook.value = true
    setTimeout(() => { copiedWebhook.value = false }, 2500)
  }
}

async function saveFavoriteAlbumSettings() {
  try {
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        auto_download_favorite_albums: settings.value.auto_download_favorite_albums,
        favorite_album_quality: settings.value.favorite_album_quality
      })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar definições de álbuns favoritos:", e)
  }
}


async function savePlexLibraries() {
  try {
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plex_discovery_library: settings.value.plex_discovery_library,
        plex_permanent_library: settings.value.plex_permanent_library
      })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar nomes das bibliotecas Plex:", e)
  }
}

const lastfmUser = ref('')
const lastfmKey = ref('')
const slskdUrl = ref('')
const slskdKey = ref('')
const ignoredArtists = ref([])
const newIgnoredArtist = ref('')

async function fetchSettings() {
  try {
    const res = await fetch(`${props.apiBase}/settings`)
    if (res.ok) {
      const data = await res.json()
      settings.value = { ...settings.value, ...data }
      lastfmUser.value = data.lastfm_username || ''
    }
  } catch (e) {
    console.error("Erro ao carregar definições:", e)
  }
}

async function fetchIgnored() {
  try {
    const res = await fetch(`${props.apiBase}/ignored-artists`)
    if (res.ok) {
      ignoredArtists.value = await res.json()
    }
  } catch (e) {
    console.error("Erro ao carregar lista negra:", e)
  }
}

async function saveProgressiveSettings() {
  try {
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        discovery_strategy: settings.value.discovery_strategy,
        batch_size: settings.value.batch_size,
        buffer_trigger: settings.value.buffer_trigger,
        max_session_tracks: settings.value.max_session_tracks
      })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar definições progressivas:", e)
  }
}

async function saveAutoPilot() {
  try {
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_pilot: settings.value.auto_pilot })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar Piloto Automático:", e)
    settings.value.auto_pilot = !settings.value.auto_pilot
  }
}

async function saveAutoPilotConfig() {
  try {
    const total = settings.value.auto_pilot_artists_limit * settings.value.auto_pilot_tracks_per_artist
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        auto_pilot_artists_limit: settings.value.auto_pilot_artists_limit,
        auto_pilot_tracks_per_artist: settings.value.auto_pilot_tracks_per_artist,
        auto_pilot_limit: total
      })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar opções do Piloto Automático:", e)
  }
}

async function saveRecommendationMode() {
  try {
    await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recommendation_mode: settings.value.recommendation_mode })
    })
    emit('settings-updated')
  } catch (e) {
    console.error("Erro ao gravar modo de recomendação:", e)
  }
}

async function submitLastfm() {
  const payload = {}
  if (lastfmUser.value.trim()) payload.lastfm_username = lastfmUser.value.trim()
  if (lastfmKey.value.trim()) payload.lastfm_api_key = lastfmKey.value.trim()
  try {
    const res = await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      if (payload.lastfm_api_key) settings.value.lastfm_linked = true
      alert("Definições do Last.fm gravadas com sucesso!")
      emit('settings-updated')
    }
  } catch (e) {
    alert("Erro ao gravar Last.fm.")
  }
}

async function submitSlskd() {
  if (!slskdUrl.value.trim() || !slskdKey.value.trim()) {
    alert("Preenche o URL e a API Key do slskd.")
    return
  }
  try {
    const res = await fetch(`${props.apiBase}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slskd_url: slskdUrl.value.trim(),
        slskd_api_key: slskdKey.value.trim()
      })
    })
    if (res.ok) {
      settings.value.slskd_linked = true
      alert("Definições do slskd gravadas com sucesso!")
      emit('settings-updated')
    }
  } catch (e) {
    alert("Erro ao gravar slskd.")
  }
}

async function submitAddIgnored() {
  const name = newIgnoredArtist.value.trim()
  if (!name) return
  try {
    const res = await fetch(`${props.apiBase}/ignored-artists`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artist: name })
    })
    if (res.ok) {
      newIgnoredArtist.value = ''
      await fetchIgnored()
    }
  } catch (e) {
    alert("Erro ao adicionar artista.")
  }
}

async function removeIgnored(artistName) {
  try {
    const res = await fetch(`${props.apiBase}/ignored-artists/${encodeURIComponent(artistName)}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      await fetchIgnored()
    }
  } catch (e) {
    console.error("Erro ao remover da lista negra:", e)
  }
}

const isCleaning = ref(false)
const cleanupMessage = ref('')
const cleanupSuccess = ref(true)

async function triggerManualCleanup() {
  if (!confirm("Tens a certeza que queres apagar todas as faixas da biblioteca de descoberta e limpar a fila de sessões?")) {
    return
  }

  isCleaning.value = true
  cleanupMessage.value = ''
  try {
    const res = await fetch(`${props.apiBase}/cleanup-now`, {
      method: 'POST'
    })
    const data = await res.json()
    if (res.ok) {
      cleanupSuccess.value = true
      cleanupMessage.value = data.message || "Biblioteca limpa com sucesso!"
      emit('settings-updated')
    } else {
      cleanupSuccess.value = false
      cleanupMessage.value = data.detail || "Erro ao executar limpeza."
    }
  } catch (e) {
    cleanupSuccess.value = false
    cleanupMessage.value = `Erro de comunicação: ${e.message}`
  } finally {
    isCleaning.value = false
    setTimeout(() => {
      cleanupMessage.value = ''
    }, 6000)
  }
}

onMounted(() => {
  fetchSettings()
  fetchIgnored()
})
</script>

<style scoped>
.settings-view {
  max-width: 900px;
  margin: 0 auto;
  text-align: left;
  padding-bottom: 40px;
}

.settings-header {
  margin-bottom: 24px;
}

.settings-header h2 {
  font-size: 26px;
  font-weight: 800;
  margin: 0 0 6px 0;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.settings-card {
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: var(--radius-lg);
  padding: 26px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
}

.card-title-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 22px;
}

.card-icon {
  font-size: 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  padding: 10px;
  border-radius: var(--radius-sm);
  line-height: 1;
}

.card-title-row h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-sub {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.setting-group {
  margin-bottom: 20px;
}

.setting-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.radio-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 640px) {
  .radio-cards {
    grid-template-columns: 1fr;
  }
}

.radio-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: rgba(18, 20, 32, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.radio-card:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(28, 32, 50, 0.85);
}

.radio-card.active {
  border-color: var(--accent-plex);
  background: rgba(245, 158, 11, 0.08);
  box-shadow: 0 0 20px -5px var(--accent-plex-glow);
}

.radio-content strong {
  display: block;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.radio-content p {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.45;
  margin: 0;
}

.progressive-options {
  background: rgba(10, 11, 18, 0.6);
  border-radius: var(--radius-md);
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-left: 4px solid var(--accent-plex);
  margin-top: 16px;
}

.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 640px) {
  .grid-2col {
    grid-template-columns: 1fr;
  }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.4;
}

.help-tooltip {
  cursor: help;
  font-size: 12px;
}

.select-input, .text-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  font-size: 13px;
  background: rgba(10, 11, 18, 0.7);
  color: var(--text-primary);
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.select-input option {
  background: #121420;
  color: #f8fafc;
}

.select-input:focus, .text-input:focus {
  outline: none;
  border-color: var(--accent-plex);
  box-shadow: 0 0 0 3px var(--accent-plex-glow);
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.auto-pilot-settings {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.radio-inline-group {
  display: flex;
  gap: 20px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.radio-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}

.radio-inline:hover {
  color: var(--text-primary);
}

/* Switch Toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 46px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(255, 255, 255, 0.15);
  transition: .3s;
  border-radius: 24px;
  border: 1px solid var(--border-subtle);
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: #ffffff;
  transition: .3s;
  border-radius: 50%;
  box-shadow: 0 1px 4px rgba(0,0,0,0.4);
}

input:checked + .slider {
  background-color: var(--accent-plex);
  border-color: var(--accent-plex);
  box-shadow: 0 0 12px var(--accent-plex-glow);
}

input:checked + .slider:before {
  transform: translateX(22px);
  background-color: #000000;
}

.divider {
  border: 0;
  border-top: 1px solid var(--border-subtle);
  margin: 18px 0;
}

.integration-block {
  padding: 8px 0;
}

.integration-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badge-status {
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.badge-status.success {
  background: var(--color-success-bg);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.badge-status.warning {
  background: var(--color-warning-bg);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.btn {
  background: linear-gradient(135deg, var(--accent-plex) 0%, var(--accent-plex-hover) 100%);
  color: #000;
  border: none;
  padding: 9px 18px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 10px var(--accent-plex-glow);
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.4);
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
}

.webhook-box {
  margin-top: 16px;
  background: rgba(10, 11, 18, 0.6);
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.webhook-input-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
}

.webhook-input {
  font-family: var(--font-mono);
  font-size: 13px;
  background: rgba(18, 20, 32, 0.9);
  color: var(--color-cyan);
}

.add-ignored-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.ignored-chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ignored-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 500;
  transition: all 0.2s ease;
}

.ignored-chip:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.15);
}

.chip-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  line-height: 1;
  transition: color 0.2s ease;
}

.chip-remove:hover {
  color: #f87171;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-muted);
  font-style: italic;
  margin: 0;
}

/* Danger Zone */
.danger-zone-card {
  border-left: 4px solid var(--color-error);
}

.cleanup-action-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  padding: 16px 20px;
  border-radius: var(--radius-md);
}

.cleanup-info strong {
  color: #fca5a5;
  font-size: 14px;
}

.btn-danger {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  white-space: nowrap;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  box-shadow: 0 6px 18px rgba(239, 68, 68, 0.45);
}

.btn-danger:disabled {
  background: rgba(239, 68, 68, 0.4);
  cursor: not-allowed;
  box-shadow: none;
}

.cleanup-status-feedback {
  margin-top: 12px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
}

.cleanup-status-feedback.success {
  background: var(--color-success-bg);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.cleanup-status-feedback.error {
  background: var(--color-error-bg);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.3);
}
</style>


