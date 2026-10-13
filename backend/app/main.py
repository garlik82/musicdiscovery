from fastapi import FastAPI, HTTPException, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
import json
import os
import httpx
import time
import shutil
import uuid
import asyncio
from typing import Optional, Dict, List, Set, Any
from pathlib import Path

app = FastAPI(title="PlexDiscover API")

# Configurar CORS (para o Vue conseguir falar com a API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Em memória (para guardar a sessão de login enquanto o utilizador vai ao browser)
active_pins = {}

# Ficheiro de definições (gravado no volume persistente /data)
DATA_DIR = "/data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_settings(settings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

def load_history() -> set:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def add_to_history(track_key: str):
    history = load_history()
    history.add(track_key.lower().strip())
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(list(history), f)
    except Exception as e:
        print(f"Erro ao gravar histórico: {e}")

IGNORED_ARTISTS_FILE = os.path.join(DATA_DIR, "ignored_artists.json")

def load_ignored_artists() -> set:
    if os.path.exists(IGNORED_ARTISTS_FILE):
        try:
            with open(IGNORED_ARTISTS_FILE, "r") as f:
                return set(item.lower().strip() for item in json.load(f))
        except Exception:
            return set()
    return set()

def save_ignored_artists(artists: set):
    try:
        with open(IGNORED_ARTISTS_FILE, "w") as f:
            json.dump(sorted(list(artists)), f)
    except Exception as e:
        print(f"Erro ao gravar artistas ignorados: {e}")

def add_ignored_artist(artist: str):
    ignored = load_ignored_artists()
    ignored.add(artist.lower().strip())
    save_ignored_artists(ignored)

def remove_ignored_artist(artist: str):
    ignored = load_ignored_artists()
    ignored.discard(artist.lower().strip())
    save_ignored_artists(ignored)

ALBUM_DOWNLOADS_FILE = os.path.join(DATA_DIR, "album_downloads.json")

def load_album_downloads() -> list:
    if os.path.exists(ALBUM_DOWNLOADS_FILE):
        try:
            with open(ALBUM_DOWNLOADS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_album_downloads(downloads: list):
    try:
        with open(ALBUM_DOWNLOADS_FILE, "w") as f:
            json.dump(downloads, f, indent=2)
    except Exception as e:
        print(f"Erro ao gravar album_downloads: {e}")

PROCESSED_FAVORITES_FILE = os.path.join(DATA_DIR, "processed_favorites.json")

def load_processed_favorites() -> set:
    if os.path.exists(PROCESSED_FAVORITES_FILE):
        try:
            with open(PROCESSED_FAVORITES_FILE, "r") as f:
                return set(item.lower().strip() for item in json.load(f))
        except Exception:
            return set()
    return set()

def save_processed_favorites(favorites: set):
    try:
        with open(PROCESSED_FAVORITES_FILE, "w") as f:
            json.dump(sorted(list(favorites)), f)
    except Exception as e:
        print(f"Erro ao gravar favoritos processados: {e}")

def is_favorite_processed(key: str) -> bool:
    favs = load_processed_favorites()
    return key.lower().strip() in favs

def mark_favorite_processed(key: str):
    favs = load_processed_favorites()
    favs.add(key.lower().strip())
    save_processed_favorites(favs)

RECOMMENDED_ARTISTS_FILE = os.path.join(DATA_DIR, "recommended_artists.json")


def load_recent_recommended_artists(retention_days: int = 30) -> dict:
    """
    Devolve {artist_name_lower: timestamp} filtrado por retenção (default 30 dias).
    """
    now = time.time()
    cutoff = now - (retention_days * 86400)
    if os.path.exists(RECOMMENDED_ARTISTS_FILE):
        try:
            with open(RECOMMENDED_ARTISTS_FILE, "r") as f:
                data = json.load(f)
                return {k: v for k, v in data.items() if v >= cutoff}
        except Exception:
            return {}
    return {}

def record_recommended_artist(artist: str):
    records = load_recent_recommended_artists(retention_days=30)
    records[artist.lower().strip()] = time.time()
    try:
        with open(RECOMMENDED_ARTISTS_FILE, "w") as f:
            json.dump(records, f)
    except Exception as e:
        print(f"Erro ao gravar artista recomendado: {e}")

PENDING_FILE = os.path.join(DATA_DIR, "pending_downloads.json")
IMPORTED_FILE = os.path.join(DATA_DIR, "imported_transfers.json")

def load_pending_downloads() -> dict:
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pending_downloads(pending: dict):
    try:
        with open(PENDING_FILE, "w") as f:
            json.dump(pending, f)
    except Exception:
        pass

def load_imported_transfers() -> set:
    if os.path.exists(IMPORTED_FILE):
        try:
            with open(IMPORTED_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_imported_transfer(transfer_id: str):
    imported = load_imported_transfers()
    imported.add(transfer_id)
    try:
        with open(IMPORTED_FILE, "w") as f:
            json.dump(list(imported), f)
    except Exception:
        pass

PENDING_INJECTIONS_FILE = os.path.join(DATA_DIR, "pending_injections.json")

def load_pending_injections() -> list:
    if os.path.exists(PENDING_INJECTIONS_FILE):
        try:
            with open(PENDING_INJECTIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_pending_injections(pending: list):
    try:
        with open(PENDING_INJECTIONS_FILE, "w") as f:
            json.dump(pending, f)
    except Exception:
        pass

ACTIVE_SESSION_FILE = os.path.join(DATA_DIR, "active_session.json")

def load_active_session() -> dict:
    if os.path.exists(ACTIVE_SESSION_FILE):
        try:
            with open(ACTIVE_SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_active_session(session_data: dict):
    try:
        with open(ACTIVE_SESSION_FILE, "w") as f:
            json.dump(session_data, f)
    except Exception:
        pass

DISCOVERY_QUEUE_FILE = os.path.join(DATA_DIR, "discovery_queue.json")

def load_discovery_queue() -> list:
    if os.path.exists(DISCOVERY_QUEUE_FILE):
        try:
            with open(DISCOVERY_QUEUE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_discovery_queue(queue: list):
    try:
        with open(DISCOVERY_QUEUE_FILE, "w") as f:
            json.dump(queue, f)
    except Exception:
        pass

import unicodedata

def normalize_text_key(text: str) -> str:
    if not text:
        return ""
    # Normalizar Unicode (ex: µ vs μ, hífen vs traço tipográfico)
    norm = unicodedata.normalize('NFKD', text)
    # Substituir diferentes tipos de traços/hífens por um hífen simples
    norm = re.sub(r'[\u2010-\u2015\u2212]', '-', norm)
    # Remover pontuação redundante mantendo letras e números
    cleaned = re.sub(r'[^\w\s]', '', norm.lower())
    return " ".join(cleaned.split())

def update_queue_item_status(artist: str, title: str, status: str, detail: str = "", old_artist: str = "", old_title: str = ""):
    queue = load_discovery_queue()
    target_artist_norm = normalize_text_key(artist)
    target_title_norm = normalize_text_key(title)
    old_artist_norm = normalize_text_key(old_artist) if old_artist else ""
    old_title_norm = normalize_text_key(old_title) if old_title else ""

    found = False
    for item in queue:
        item_a = normalize_text_key(item.get('artist', ''))
        item_t = normalize_text_key(item.get('title', ''))

        matches_new = (item_a == target_artist_norm and item_t == target_title_norm)
        matches_old = bool(old_artist_norm and item_a == old_artist_norm and item_t == old_title_norm)
        matches_fuzzy = (item_t == target_title_norm and (item_a in target_artist_norm or target_artist_norm in item_a))

        if matches_new or matches_old or matches_fuzzy:
            # Atualiza o item existente (inclusive os nomes canónicos do MusicBrainz)
            item["artist"] = artist
            item["title"] = title
            item["status"] = status
            item["detail"] = detail
            item["updated_at"] = time.time()
            found = True
            break

    if not found:
        queue.append({
            "artist": artist,
            "title": title,
            "status": status,
            "detail": detail,
            "created_at": time.time(),
            "updated_at": time.time()
        })
    save_discovery_queue(queue)

def get_plex_server(token):
    account = MyPlexAccount(token=token)
    # Procurar o servidor Plex principal do utilizador
    for resource in account.resources():
        if 'server' in resource.provides and resource.owned:
            return resource.connect()
    raise Exception("Nenhum servidor Plex encontrado na tua conta.")

from pydantic import BaseModel

class SettingsUpdate(BaseModel):
    lastfm_api_key: str | None = None
    lastfm_username: str | None = None
    slskd_url: str | None = None
    slskd_api_key: str | None = None
    auto_pilot: bool | None = None
    auto_pilot_limit: int | None = None
    auto_pilot_artists_limit: int | None = None
    auto_pilot_tracks_per_artist: int | None = None
    recommendation_mode: str | None = None # "contextual" ou "hybrid"
    discovery_strategy: str | None = None # "progressive" ou "fixed"
    batch_size: int | None = None # 3, 5, 8, 10
    buffer_trigger: int | None = None # 1, 2, 3, 4
    max_session_tracks: int | None = None # 0 = ilimitado, 10, 15, 20, 30
    plex_discovery_library: str | None = None # default: "Discover"
    plex_permanent_library: str | None = None # default: "Music"
    auto_download_favorite_albums: bool | None = None
    favorite_album_quality: str | None = None # "flac_16_44"

@app.get("/api/settings")
def get_settings():
    settings = load_settings()
    env_lastfm = os.environ.get("LASTFM_API_KEY")
    has_lastfm = bool(settings.get("LASTFM_API_KEY") or (env_lastfm and env_lastfm != "tua_api_key_do_lastfm"))
    
    env_slskd = os.environ.get("SLSKD_API_KEY")
    has_slskd = bool(settings.get("SLSKD_API_KEY") or (env_slskd and env_slskd != "tua_api_key_do_slskd"))
    
    artists_limit = settings.get("AUTO_PILOT_ARTISTS_LIMIT", 15)
    tracks_per_artist = settings.get("AUTO_PILOT_TRACKS_PER_ARTIST", 1)
    
    return {
        "plex_linked": "PLEX_TOKEN" in settings,
        "lastfm_linked": has_lastfm,
        "lastfm_username": settings.get("LASTFM_USERNAME", os.environ.get("LASTFM_USERNAME", "")),
        "slskd_linked": has_slskd,
        "auto_pilot": settings.get("AUTO_PILOT", False),
        "auto_pilot_limit": settings.get("AUTO_PILOT_LIMIT", artists_limit * tracks_per_artist),
        "auto_pilot_artists_limit": artists_limit,
        "auto_pilot_tracks_per_artist": tracks_per_artist,
        "recommendation_mode": settings.get("RECOMMENDATION_MODE", "contextual"), # "contextual" ou "hybrid"
        "discovery_strategy": settings.get("DISCOVERY_STRATEGY", "progressive"), # "progressive" ou "fixed"
        "batch_size": settings.get("BATCH_SIZE", 5),
        "buffer_trigger": settings.get("BUFFER_TRIGGER", 2),
        "max_session_tracks": settings.get("MAX_SESSION_TRACKS", 20),
        "plex_discovery_library": settings.get("PLEX_DISCOVERY_LIBRARY", "Discover"),
        "plex_permanent_library": settings.get("PLEX_PERMANENT_LIBRARY", "Music"),
        "auto_download_favorite_albums": settings.get("AUTO_DOWNLOAD_FAVORITE_ALBUMS", True),
        "favorite_album_quality": settings.get("FAVORITE_ALBUM_QUALITY", "flac_16_44")
    }

@app.post("/api/settings")
def update_settings(update: SettingsUpdate):
    settings = load_settings()
    if update.lastfm_api_key is not None:
        settings["LASTFM_API_KEY"] = update.lastfm_api_key
    if update.lastfm_username is not None:
        settings["LASTFM_USERNAME"] = update.lastfm_username.strip()
    if update.slskd_url is not None:
        settings["SLSKD_URL"] = update.slskd_url
    if update.slskd_api_key is not None:
        settings["SLSKD_API_KEY"] = update.slskd_api_key
    if update.auto_pilot is not None:
        settings["AUTO_PILOT"] = update.auto_pilot
    if update.auto_pilot_limit is not None:
        settings["AUTO_PILOT_LIMIT"] = update.auto_pilot_limit
    if update.auto_pilot_artists_limit is not None:
        settings["AUTO_PILOT_ARTISTS_LIMIT"] = update.auto_pilot_artists_limit
    if update.auto_pilot_tracks_per_artist is not None:
        settings["AUTO_PILOT_TRACKS_PER_ARTIST"] = update.auto_pilot_tracks_per_artist
    if update.recommendation_mode is not None:
        settings["RECOMMENDATION_MODE"] = update.recommendation_mode
    if update.discovery_strategy is not None:
        settings["DISCOVERY_STRATEGY"] = update.discovery_strategy
    if update.batch_size is not None:
        settings["BATCH_SIZE"] = update.batch_size
    if update.buffer_trigger is not None:
        settings["BUFFER_TRIGGER"] = update.buffer_trigger
    if update.max_session_tracks is not None:
        settings["MAX_SESSION_TRACKS"] = update.max_session_tracks
    if update.plex_discovery_library is not None:
        settings["PLEX_DISCOVERY_LIBRARY"] = update.plex_discovery_library.strip()
    if update.plex_permanent_library is not None:
        settings["PLEX_PERMANENT_LIBRARY"] = update.plex_permanent_library.strip()
    if update.auto_download_favorite_albums is not None:
        settings["AUTO_DOWNLOAD_FAVORITE_ALBUMS"] = update.auto_download_favorite_albums
    if update.favorite_album_quality is not None:
        settings["FAVORITE_ALBUM_QUALITY"] = update.favorite_album_quality
    save_settings(settings)
    return {"status": "success"}

import urllib.parse

def get_session_album_info(server, session):
    """
    Verifica se a reprodução tem como origem um Álbum completo no Plex
    (exclui playlists, rádios, estações ou faixas avulsas),
    e calcula a duração total do álbum e o tempo restante estimado.
    """
    try:
        client_id = None
        if hasattr(session, 'players') and session.players:
            client_id = getattr(session.players[0], 'machineIdentifier', None)
        rating_key = str(getattr(session, 'ratingKey', ''))
        
        if not client_id or not rating_key:
            return {'is_album': False}
            
        headers = {'X-Plex-Client-Identifier': client_id}
        pqs = server._server.query('/playQueues', headers=headers)
        for pq in pqs:
            pq_id = pq.attrib.get('id')
            pq_detail = server._server.query(f'/playQueues/{pq_id}', headers=headers)
            
            matched = (pq_detail.attrib.get('playQueueSelectedMetadataItemID') == rating_key)
            if not matched and len(pqs) == 1:
                matched = True
            if not matched:
                try:
                    loaded_pq = PlayQueue.get(server, int(pq_id))
                    if any(str(getattr(it, 'ratingKey', '')) == rating_key for it in getattr(loaded_pq, 'items', [])):
                        matched = True
                except Exception:
                    pass

            if matched:
                source_uri = pq_detail.attrib.get('playQueueSourceURI', '')
                unquoted = urllib.parse.unquote(source_uri)
                if any(x in unquoted.lower() for x in ['playlist', 'station', 'radio']):
                    return {'is_album': False, 'source': 'playlist/radio', 'play_queue_id': int(pq_id) if pq_id else None}
                if '/metadata/' in unquoted:
                    source_key = int(unquoted.split('/metadata/')[-1].split('/')[0])
                    item = server.fetchItem(source_key)
                    if item.TYPE == 'album':
                        tracks = item.tracks()
                        total_album_duration_ms = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
                        current_track_index = getattr(session, 'index', 1) or 1
                        current_track_offset_ms = getattr(session, 'viewOffset', 0) or 0
                        current_track_dur_ms = getattr(session, 'duration', 0) or 0

                        # Somar duração das faixas anteriores + offset da faixa atual
                        elapsed_album_ms = 0
                        for t in tracks:
                            t_idx = getattr(t, 'index', None)
                            t_dur = getattr(t, 'duration', 0) or 0
                            if t_idx is not None and t_idx < current_track_index:
                                elapsed_album_ms += t_dur
                            elif t_idx == current_track_index:
                                elapsed_album_ms += current_track_offset_ms
                                break
                        
                        remaining_album_ms = max(0, total_album_duration_ms - elapsed_album_ms)

                        return {
                            'is_album': True, 
                            'album_id': str(source_key), 
                            'album_title': item.title,
                            'play_queue_id': int(pq_id) if pq_id else None,
                            'thumb': item.thumb or getattr(session, 'parentThumb', None),
                            'total_duration_ms': total_album_duration_ms,
                            'elapsed_ms': elapsed_album_ms,
                            'remaining_ms': remaining_album_ms,
                            'track_count': len(tracks),
                            'current_track_index': current_track_index,
                            'current_track_offset_ms': current_track_offset_ms,
                            'current_track_duration_ms': current_track_dur_ms
                        }
                    else:
                        return {'is_album': False, 'source': item.TYPE, 'play_queue_id': int(pq_id) if pq_id else None}
                return {'is_album': False, 'source': 'queue', 'play_queue_id': int(pq_id) if pq_id else None}
    except Exception as e:
        print(f"Erro ao verificar origem no Plex: {e}")
    return {'is_album': False}

def _get_now_playing_data():
    settings = load_settings()
    token = settings.get("PLEX_TOKEN")
    if not token:
        return {"is_playing": False, "error": "Plex não está ligado"}
        
    try:
        server = get_plex_server(token)
        sessions = server.sessions()
        for session in sessions:
            if session.type == 'track':
                player = session.players[0] if session.players else None
                player_state = getattr(player, 'state', 'playing') if player else 'playing'
                album_info = get_session_album_info(server, session)
                thumb = album_info.get("thumb") or getattr(session, 'thumb', None) or getattr(session, 'parentThumb', None)
                rating_key = str(getattr(session, 'ratingKey', ''))
                user_rating = float(getattr(session, 'userRating', 0) or 0)
                is_favorite = (user_rating >= 8.0)
                return {
                    "is_playing": True,
                    "state": player_state,
                    "artist": session.grandparentTitle,
                    "album": session.parentTitle,
                    "track": session.title,
                    "user": session.usernames[0] if session.usernames else "Local",
                    "player": player.product if player else "Desconhecido",
                    "is_album": album_info.get("is_album", False),
                    "album_id": album_info.get("album_id"),
                    "play_queue_id": album_info.get("play_queue_id"),
                    "rating_key": rating_key,
                    "user_rating": user_rating,
                    "is_favorite": is_favorite,
                    "thumb": thumb,
                    "total_duration_ms": album_info.get("total_duration_ms", getattr(session, 'duration', 0)),
                    "elapsed_ms": album_info.get("elapsed_ms", getattr(session, 'viewOffset', 0)),
                    "remaining_ms": album_info.get("remaining_ms", max(0, (getattr(session, 'duration', 0) or 0) - (getattr(session, 'viewOffset', 0) or 0))),
                    "track_count": album_info.get("track_count"),
                    "current_track_index": album_info.get("current_track_index", getattr(session, 'index', 1)),
                    "source": album_info.get("source", "album" if album_info.get("is_album") else "unknown")
                }
        return {"is_playing": False}
    except Exception as e:
        return {"is_playing": False, "error": str(e)}

@app.get("/api/now-playing")
def get_now_playing():
    data = _get_now_playing_data()
    if data.get("error") == "Plex não está ligado":
        raise HTTPException(status_code=401, detail=data["error"])
    elif data.get("error"):
        raise HTTPException(status_code=500, detail=data["error"])
    return data

@app.get("/api/plex/image")
async def get_plex_image(path: str = Query(...)):
    """
    Proxy autenticado para imagens e capas de álbuns do Plex Media Server.
    """
    settings = load_settings()
    token = settings.get("PLEX_TOKEN")
    if not token:
        raise HTTPException(status_code=401, detail="Plex não autenticado")

    server = get_plex_server(token)
    full_url = server.url(path)
    
    headers = {"X-Plex-Token": token}
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            res = await client.get(full_url, headers=headers)
            if res.status_code == 200:
                content_type = res.headers.get("Content-Type", "image/jpeg")
                return Response(content=res.content, media_type=content_type)
            else:
                raise HTTPException(status_code=res.status_code, detail="Erro ao obter imagem do Plex")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro no proxy de imagem: {e}")

@app.get("/api/discovery-queue")
def get_discovery_queue():
    """
    Devolve a fila de faixas em descoberta e os respetivos estados em tempo real.
    """
    return load_discovery_queue()

@app.delete("/api/discovery-queue")
def clear_discovery_queue():
    """
    Limpa o histórico da fila de descoberta.
    """
    save_discovery_queue([])
    return {"status": "success"}

async def execute_full_cleanup():
    """
    Executa a limpeza completa dos ficheiros de descoberta, histórico de transferências,
    sessão ativa e força a purga no Plex.
    """
    # 1. Apagar ficheiros físicos
    clear_playlist_discovery_folder()
    
    # 2. Reset a ficheiros de dados e sessões
    save_active_session({})
    save_discovery_queue([])
    save_pending_downloads({})
    save_pending_injections([])
    save_cleanup_state({})
    
    # Reset a artistas recomendados recentes para testes imediatos funcionarem
    if os.path.exists(RECOMMENDED_ARTISTS_FILE):
        try:
            with open(RECOMMENDED_ARTISTS_FILE, "w") as f:
                json.dump([], f)
        except Exception:
            pass

    # 3. Limpar transferências no slskd
    settings = load_settings()
    slskd_url = settings.get("SLSKD_URL")
    slskd_key = settings.get("SLSKD_API_KEY")
    if slskd_url and slskd_key:
        try:
            client = SlskdClient(url=slskd_url, api_key=slskd_key)
            await client.clear_completed_downloads()
        except Exception as e:
            print(f"Aviso ao limpar slskd na limpeza geral: {e}")

    # 4. Atualizar e purgar biblioteca Plex
    token = settings.get("PLEX_TOKEN")
    if token:
        try:
            server = get_plex_server(token)
            disc_lib = settings.get("PLEX_DISCOVERY_LIBRARY", "Discover")
            trigger_plex_music_scan(server, library_name=disc_lib, purge_orphans=True)
            try:
                for pl in server.playlists():
                    if pl.title == "PlexDiscover":
                        pl.delete()
            except Exception:
                pass
        except Exception as e:
            print(f"Aviso ao purgar Plex na limpeza geral: {e}")

@app.post("/api/cleanup-now")
async def trigger_manual_cleanup():
    """
    Endpoint para limpeza manual imediata disparada pelo utilizador.
    """
    await execute_full_cleanup()
    return {"status": "success", "message": "Biblioteca de descoberta e registos limpos com sucesso!"}


class IgnoreArtistRequest(BaseModel):
    artist: str

@app.get("/api/ignored-artists")
def get_ignored_artists():
    return sorted(list(load_ignored_artists()))

@app.post("/api/ignored-artists")
def ignore_artist(req: IgnoreArtistRequest):
    if not req.artist.strip():
        raise HTTPException(status_code=400, detail="Nome de artista inválido")
    add_ignored_artist(req.artist)
    return {"status": "success", "message": f"Artista '{req.artist}' adicionado à lista negra"}

@app.delete("/api/ignored-artists/{artist}")
def unignore_artist(artist: str):
    remove_ignored_artist(artist)
    return {"status": "success", "message": f"Artista '{artist}' removido da lista negra"}

class PromoteArtistRequest(BaseModel):
    artist: str

@app.post("/api/promote-artist")
def promote_artist(req: PromoteArtistRequest):
    """
    Move todos os ficheiros do artista da pasta temporária /music/Playlistdiscovery/{Artist}
    para a biblioteca permanente /music/{Artist}, consolidando a banda na coleção definitiva.
    """
    artist_name = req.artist.strip()
    if not artist_name:
        raise HTTPException(status_code=400, detail="Nome de artista inválido")

    # Pastas candidatas de descoberta (/music_discovery ou legado /music/Playlistdiscovery)
    disc_candidates = []
    if os.path.exists("/music_discovery"):
        disc_candidates.append("/music_discovery")
    legacy_folder = os.path.join("/music", "Playlistdiscovery")
    if os.path.exists(legacy_folder):
        disc_candidates.append(legacy_folder)

    found_folder = None
    clean_target = re.sub(r'[^\w]', '', artist_name.lower())
    for disc_folder in disc_candidates:
        if os.path.exists(disc_folder):
            for item in os.listdir(disc_folder):
                if re.sub(r'[^\w]', '', item.lower()) == clean_target:
                    found_folder = os.path.join(disc_folder, item)
                    artist_name = item
                    break
        if found_folder:
            break

    if not found_folder or not os.path.isdir(found_folder):
        raise HTTPException(status_code=404, detail=f"Nenhum ficheiro temporário encontrado para '{artist_name}'")

    dest_folder = os.path.join("/music", artist_name)
    os.makedirs(dest_folder, exist_ok=True)

    moved_count = 0
    # Mover álbuns e ficheiros para a biblioteca permanente
    for album in os.listdir(found_folder):
        src_album = os.path.join(found_folder, album)
        target_album = os.path.join(dest_folder, album)
        if os.path.isdir(src_album):
            os.makedirs(target_album, exist_ok=True)
            for file_name in os.listdir(src_album):
                src_file = os.path.join(src_album, file_name)
                tgt_file = os.path.join(target_album, file_name)
                shutil.move(src_file, tgt_file)
                moved_count += 1
            try:
                shutil.rmtree(src_album)
            except Exception:
                pass
        else:
            shutil.move(src_album, os.path.join(dest_folder, album))
            moved_count += 1

    try:
        shutil.rmtree(found_folder)
    except Exception:
        pass

    # Atualizar Plex em ambas as bibliotecas (Permanente e Descoberta)
    settings = load_settings()
    token = settings.get("PLEX_TOKEN")
    if token:
        try:
            server = get_plex_server(token)
            perm_lib = settings.get("PLEX_PERMANENT_LIBRARY", "Music")
            disc_lib = settings.get("PLEX_DISCOVERY_LIBRARY", "Discover")
            trigger_plex_music_scan(server, library_name=perm_lib)
            trigger_plex_music_scan(server, library_name=disc_lib, purge_orphans=True)
        except Exception as e:
            print(f"Aviso ao acionar scan após promover banda: {e}")

    return {
        "status": "success",
        "message": f"Banda '{artist_name}' promovida com sucesso! {moved_count} ficheiros movidos para a biblioteca permanente.",
        "moved_files": moved_count
    }

class FavoriteAlbumRequest(BaseModel):
    artist: str
    album: str | None = None
    track: str | None = None

@app.post("/api/favorite-album")
async def favorite_album_endpoint(req: FavoriteAlbumRequest):
    """
    Aciona manualmente o download do álbum completo em FLAC 16-bit / 44.1 kHz.
    """
    if not req.artist.strip():
        raise HTTPException(status_code=400, detail="Nome de artista inválido")
    res = await trigger_favorite_album_download(req.artist, req.album or "", req.track or "", manual=True)
    return res

@app.get("/api/favorite-albums")
def get_favorite_albums_endpoint():
    """
    Devolve a lista de álbuns favoritados e o respetivo estado de transferência em FLAC.
    """
    return load_album_downloads()

@app.delete("/api/favorite-albums/{album_id}")
def delete_favorite_album_endpoint(album_id: str):
    """
    Remove um álbum do registo de downloads.
    """
    dls = load_album_downloads()
    dls = [d for d in dls if d.get("id") != album_id]
    save_album_downloads(dls)
    return {"status": "success"}

@app.post("/api/plex-webhook")
async def plex_webhook_endpoint(request: Request):
    """
    Recebe eventos webhook do Plex Media Server.
    Quando deteta 'media.rate' numa faixa de áudio com avaliação >= 8.0 (ou favorita/coração),
    dispara o download automático do álbum em FLAC 16/44 para a biblioteca definitiva.
    """
    try:
        content_type = request.headers.get("content-type", "")
        payload_data = None
        if "multipart/form-data" in content_type:
            form = await request.form()
            payload_str = form.get("payload")
            if payload_str:
                payload_data = json.loads(payload_str)
        else:
            payload_data = await request.json()

        if not payload_data:
            return {"status": "ignored", "reason": "Sem payload"}

        event = payload_data.get("event")
        if event == "media.rate":
            meta = payload_data.get("Metadata", {})
            if meta.get("type") == "track":
                rating_val = float(payload_data.get("rating") or meta.get("userRating") or 0)
                if rating_val >= 8.0:
                    artist = meta.get("grandparentTitle", "")
                    album = meta.get("parentTitle", "")
                    track = meta.get("title", "")
                    settings = load_settings()
                    if settings.get("AUTO_DOWNLOAD_FAVORITE_ALBUMS", True):
                        fav_key = f"{artist} - {album or track}".lower()
                        if not is_favorite_processed(fav_key):
                            mark_favorite_processed(fav_key)
                            print(f"Plex Webhook: Faixa favoritada ({rating_val}/10): {artist} - {track} ({album}). A iniciar download do álbum FLAC 16/44!")
                            asyncio.create_task(trigger_favorite_album_download(artist, album, track))
                            return {"status": "triggered", "artist": artist, "album": album}

        return {"status": "ignored", "event": event}
    except Exception as e:
        print(f"Erro ao processar Plex Webhook: {e}")
        return {"status": "error", "error": str(e)}

from app.lastfm import LastFMClient

@app.get("/api/discover")
async def discover_music(artist: str):
    settings = load_settings()
    lastfm_api_key = settings.get("LASTFM_API_KEY") or os.environ.get("LASTFM_API_KEY")
    
    if not lastfm_api_key or lastfm_api_key == "tua_api_key_do_lastfm":
        raise HTTPException(status_code=400, detail="Falta configurar a API Key do Last.fm. Vai às definições para a configurar.")
        
    lastfm = LastFMClient(api_key=lastfm_api_key)
    
    try:
        similar_artists = await lastfm.get_similar_artists(artist, limit=5)
        
        # Para cada artista, vamos buscar 2 músicas
        playlist_candidates = []
        for similar in similar_artists:
            top_tracks = await lastfm.get_top_tracks(similar["name"], limit=2)
            similar["top_tracks"] = top_tracks
            playlist_candidates.extend(top_tracks)
            
        return {
            "source_artist": artist,
            "similar_artists": similar_artists,
            "playlist": playlist_candidates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao contactar Last.fm: {str(e)}")

@app.get("/api/auth/plex/login")
def plex_login(forwardUrl: str = "http://localhost:8789"):
    # Identificação da nossa App para o Plex
    headers = {
        'X-Plex-Product': 'PlexDiscover',
        'X-Plex-Client-Identifier': 'plexdiscover-app-unique-id'
    }
    pinlogin = MyPlexPinLogin(headers=headers, oauth=True)
    
    pin_id = id(pinlogin)
    active_pins[pin_id] = pinlogin
    
    return {
        "oauth_url": pinlogin.oauthUrl(forwardUrl=forwardUrl), 
        "pin_id": pin_id
    }

@app.get("/api/auth/plex/check/{pin_id}")
def check_plex_login(pin_id: int):
    pinlogin = active_pins.get(pin_id)
    if not pinlogin:
        raise HTTPException(status_code=404, detail="Sessão de login não encontrada. Tenta novamente.")
    
    # O checkLogin() vai aos servidores do Plex ver se já autorizaste
    is_linked = pinlogin.checkLogin()
    
    if is_linked:
        token = pinlogin.token
        settings = load_settings()
        settings["PLEX_TOKEN"] = token
        save_settings(settings)
        
        # Limpar da memória
        del active_pins[pin_id]
        return {"status": "success", "message": "Plex ligado com sucesso!"}
    else:
        return {"status": "pending", "message": "A aguardar autorização..."}

import re

def build_slskd_query(artist: str, title: str) -> str:
    # Remover parentesis e brackets e caracteres especiais
    full_str = f"{artist} {title}"
    clean_str = re.sub(r'\(.*?\)|\[.*?\]', '', full_str)
    clean_str = re.sub(r'[^\w\s]', '', clean_str)
    
    # Palavras com mais de 1 caracter
    words = [w for w in clean_str.split() if len(w) > 1]
    
    # Soulseek falha com pesquisas muito longas. Vamos usar no máximo as primeiras 4 palavras.
    query = " ".join(words[:4])
    return query.strip()

from app.slskd import SlskdClient

class DownloadRequest(BaseModel):
    artist: str
    title: str

async def _download_track_internal(artist: str, title: str):
    settings = load_settings()
    slskd_url = settings.get("SLSKD_URL") or os.environ.get("SLSKD_URL")
    slskd_key = settings.get("SLSKD_API_KEY") or os.environ.get("SLSKD_API_KEY")
    
    if not slskd_url or not slskd_key:
        update_queue_item_status(artist, title, "error", "slskd não configurado")
        raise ValueError("slskd não configurado.")
        
    update_queue_item_status(artist, title, "searching", "A pesquisar no Soulseek...")
    client = SlskdClient(url=slskd_url, api_key=slskd_key)
    search_query = build_slskd_query(artist, title)
    results = await client.search(search_query, artist, title, timeout_seconds=20)
    
    if not results:
        update_queue_item_status(artist, title, "error", "Nenhum ficheiro encontrado")
        raise ValueError("Nenhum ficheiro encontrado no slskd.")
        
    best_accepted = await client.download_best_available(results)
    if best_accepted:
        add_to_history(f"{artist} - {title}")
        base_name = os.path.basename(best_accepted["filename"]).replace('\\', '/').split('/')[-1].lower()
        pending = load_pending_downloads()
        pending[base_name] = {"artist": artist, "title": title, "added_at": time.time()}
        save_pending_downloads(pending)
        update_queue_item_status(artist, title, "downloading", f"Em download ({best_accepted.get('quality', 'Áudio')})")
        return {
            "status": "success", 
            "message": "Download agendado e aceite!", 
            "file": best_accepted["filename"], 
            "username": best_accepted["username"]
        }
    else:
        update_queue_item_status(artist, title, "error", "Utilizadores rejeitaram ou ocupados")
        raise ValueError("Todos os utilizadores encontrados rejeitaram o pedido (ex: ficheiro não partilhado/bloqueado).")

@app.post("/api/download")
async def download_track(req: DownloadRequest):
    try:
        return await _download_track_internal(req.artist, req.title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import asyncio

def is_artist_in_permanent_library(server, artist_name: str) -> bool:
    try:
        settings = load_settings()
        perm_lib = settings.get("PLEX_PERMANENT_LIBRARY", "Music")
        try:
            music = server.library.section(perm_lib)
        except Exception:
            music = server.library.section('Music')
            
        matches = music.searchArtists(title=artist_name)
        clean_target = re.sub(r'[^\w]', '', artist_name.lower())
        for a in matches:
            clean_match = re.sub(r'[^\w]', '', a.title.lower())
            if clean_match == clean_target:
                # Verificar se tem faixas na biblioteca permanente (fora das pastas de descoberta)
                for t in a.tracks()[:5]:
                    for m in getattr(t, 'media', []):
                        for p in getattr(m, 'parts', []):
                            p_file = p.file.lower()
                            if 'musicdiscovery' not in p_file and 'playlistdiscovery' not in p_file:
                                return True
    except Exception as e:
        print(f"Erro ao verificar artista no Plex: {e}")
    return False

def is_track_in_permanent_library(server, artist_name: str, title: str) -> bool:
    try:
        settings = load_settings()
        perm_lib = settings.get("PLEX_PERMANENT_LIBRARY", "Music")
        try:
            music = server.library.section(perm_lib)
        except Exception:
            music = server.library.section('Music')

        matches = music.searchTracks(title=title)
        clean_title = re.sub(r'[^\w]', '', title.lower())
        clean_artist = re.sub(r'[^\w]', '', artist_name.lower())
        for t in matches:
            clean_match_title = re.sub(r'[^\w]', '', t.title.lower())
            clean_match_artist = re.sub(r'[^\w]', '', getattr(t, 'grandparentTitle', '').lower())
            if clean_match_title == clean_title and (clean_artist in clean_match_artist or clean_match_artist in clean_artist):
                for m in getattr(t, 'media', []):
                    for p in getattr(m, 'parts', []):
                        p_file = p.file.lower()
                        if 'musicdiscovery' not in p_file and 'playlistdiscovery' not in p_file:
                            return True
    except Exception:
        pass
    return False

from plexapi.playqueue import PlayQueue
from plexapi.playlist import Playlist

def get_play_queue_remaining_count(server, play_queue_id: int | None, current_rating_key: str | None) -> int | None:
    if not play_queue_id or not server:
        return None
    try:
        pq = PlayQueue.get(server, play_queue_id)
        if not pq or not getattr(pq, 'items', None):
            return None
        current_idx = None
        if current_rating_key:
            for idx, item in enumerate(pq.items):
                if str(getattr(item, 'ratingKey', '')) == str(current_rating_key):
                    current_idx = idx
                    break
        if current_idx is None and hasattr(pq, 'playQueueSelectedItemOffset') and pq.playQueueSelectedItemOffset is not None:
            try:
                current_idx = int(pq.playQueueSelectedItemOffset)
            except Exception:
                pass
            
        if current_idx is not None:
            remaining = max(0, len(pq.items) - current_idx - 1)
            return remaining
    except Exception as e:
        print(f"Aviso ao consultar PlayQueue {play_queue_id}: {e}")
    return None

async def download_next_discovery_batch(
    target_count: int,
    similar_artists: list,
    seen_artists_in_session: set,
    tracks_per_artist: int,
    plex_server,
    history: set,
    ignored_artists: set,
    recent_recommended: dict,
    batch_label: str = ""
) -> int:
    downloaded_count = 0
    settings = load_settings()
    lastfm_api_key = settings.get("LASTFM_API_KEY") or os.environ.get("LASTFM_API_KEY")
    if not lastfm_api_key or lastfm_api_key == "tua_api_key_do_lastfm":
        return 0
    lastfm = LastFMClient(api_key=lastfm_api_key)

    for similar in similar_artists:
        current_check = _get_now_playing_data()
        if not current_check.get("is_playing") or current_check.get("state") == "paused":
            print(f"Auto-pilot [{batch_label}]: Reprodução parada ou em pausa detetada. A interromper recolha.")
            break

        if downloaded_count >= target_count:
            break

        sim_name = similar.get("name", "").strip()
        sim_norm = sim_name.lower()
        if not sim_name or sim_norm in seen_artists_in_session:
            continue

        seen_artists_in_session.add(sim_norm)

        # 1. Ignorados
        if sim_norm in ignored_artists:
            print(f"Auto-pilot [{batch_label}]: A saltar '{sim_name}' (na lista negra)")
            continue

        # 2. Recomendados nos últimos 30 dias
        if sim_norm in recent_recommended:
            print(f"Auto-pilot [{batch_label}]: A saltar '{sim_name}' (já recomendado nos últimos 30 dias)")
            continue

        # 3. Já na biblioteca Plex
        if plex_server and is_artist_in_permanent_library(plex_server, sim_name):
            print(f"Auto-pilot [{batch_label}]: A saltar '{sim_name}' (já existe na tua biblioteca do Plex)")
            continue

        try:
            top_tracks = await lastfm.get_top_tracks(sim_name, limit=10)
            if not top_tracks:
                continue

            tracks_from_this_artist = 0
            for track in top_tracks:
                if tracks_from_this_artist >= tracks_per_artist or downloaded_count >= target_count:
                    break

                if plex_server and is_track_in_permanent_library(plex_server, track['artist'], track['title']):
                    print(f"Auto-pilot [{batch_label}]: A saltar faixa existente: {track['artist']} - {track['title']}")
                    continue

                key = f"{track['artist']} - {track['title']}".lower().strip()
                if key in history:
                    continue

                print(f"Auto-pilot [{batch_label}] vai descarregar ({downloaded_count + 1}/{target_count}): {track['artist']} - {track['title']}")
                try:
                    res = await _download_track_internal(track['artist'], track['title'])
                    print(f"Auto-pilot [{batch_label}] agendou no slskd: {res['file']}")
                    history.add(key)
                    downloaded_count += 1
                    tracks_from_this_artist += 1
                except Exception as dl_err:
                    print(f"Auto-pilot [{batch_label}] falhou download de {track['title']}: {dl_err}")

            if tracks_from_this_artist > 0:
                record_recommended_artist(sim_name)
        except Exception as e:
            print(f"Auto-pilot [{batch_label}] erro para {sim_name}: {e}")

    return downloaded_count

last_processed_album_id = None

async def auto_pilot_loop():
    global last_processed_album_id
    while True:
        await asyncio.sleep(20)
        try:
            settings = load_settings()
            if not settings.get("AUTO_PILOT", False):
                continue
                
            data = _get_now_playing_data()
            if not data.get("is_playing") or data.get("state") == "paused":
                continue

            strategy = settings.get("DISCOVERY_STRATEGY", "progressive")
            batch_size = settings.get("BATCH_SIZE", 5)
            buffer_trigger = settings.get("BUFFER_TRIGGER", 2)
            max_session_tracks = settings.get("MAX_SESSION_TRACKS", 20)
            tracks_per_artist = settings.get("AUTO_PILOT_TRACKS_PER_ARTIST", 1)

            token = settings.get("PLEX_TOKEN")
            plex_server = get_plex_server(token) if token else None

            # CASO 1: NOVO ÁLBUM DETETADO
            if data.get("is_album"):
                current_album_id = data.get("album_id")
                if current_album_id and current_album_id != last_processed_album_id:
                    last_processed_album_id = current_album_id
                    save_discovery_queue([])
                    
                    lastfm_api_key = settings.get("LASTFM_API_KEY") or os.environ.get("LASTFM_API_KEY")
                    if not lastfm_api_key or lastfm_api_key == "tua_api_key_do_lastfm":
                        continue
                        
                    lastfm = LastFMClient(api_key=lastfm_api_key)
                    
                    fetch_limit = 60
                    similar_artists = await lastfm.get_similar_artists(data['artist'], limit=fetch_limit)
                    
                    rec_mode = settings.get("RECOMMENDATION_MODE", "contextual")
                    lastfm_user = settings.get("LASTFM_USERNAME") or os.environ.get("LASTFM_USERNAME")
                    if rec_mode == "hybrid" and lastfm_user:
                        try:
                            recent_user_bands = await lastfm.get_recent_artists(lastfm_user, limit=10)
                            if recent_user_bands:
                                hybrid_candidates = []
                                for hb in recent_user_bands[:3]:
                                    hb_sim = await lastfm.get_similar_artists(hb, limit=10)
                                    hybrid_candidates.extend(hb_sim)
                                merged = []
                                sim_idx = 0
                                hyb_idx = 0
                                while sim_idx < len(similar_artists) or hyb_idx < len(hybrid_candidates):
                                    for _ in range(2):
                                        if sim_idx < len(similar_artists):
                                            merged.append(similar_artists[sim_idx])
                                            sim_idx += 1
                                    if hyb_idx < len(hybrid_candidates):
                                        merged.append(hybrid_candidates[hyb_idx])
                                        hyb_idx += 1
                                similar_artists = merged
                        except Exception as hyb_err:
                            print(f"Aviso no modo híbrido: {hyb_err}")

                    if not similar_artists:
                        continue

                    # Determinar o tamanho do primeiro lote
                    if strategy == "progressive":
                        initial_target = batch_size
                    else:
                        initial_target = settings.get("AUTO_PILOT_LIMIT", 15)

                    if max_session_tracks > 0:
                        initial_target = min(initial_target, max_session_tracks)

                    seen_artists_in_session = set()
                    history = load_history()
                    ignored_artists = load_ignored_artists()
                    recent_recommended = load_recent_recommended_artists(retention_days=30)

                    print(f"Auto-pilot: Novo álbum iniciado: {data['artist']} - {data['album']}. A agendar lote inicial ({initial_target} faixas)...")
                    downloaded = await download_next_discovery_batch(
                        target_count=initial_target,
                        similar_artists=similar_artists,
                        seen_artists_in_session=seen_artists_in_session,
                        tracks_per_artist=tracks_per_artist,
                        plex_server=plex_server,
                        history=history,
                        ignored_artists=ignored_artists,
                        recent_recommended=recent_recommended,
                        batch_label="Lote Inicial"
                    )

                    save_active_session({
                        "album_id": current_album_id,
                        "album_title": data.get("album"),
                        "artist": data.get("artist"),
                        "play_queue_id": data.get("play_queue_id"),
                        "similar_artists": similar_artists,
                        "seen_artists": list(seen_artists_in_session),
                        "total_downloaded": downloaded,
                        "last_batch_time": time.time()
                    })
                    continue

            # CASO 2: SESSÃO EM CURSO & BUFFER PROGRESSIVO
            if strategy == "progressive":
                active_sess = load_active_session()
                similar_artists = active_sess.get("similar_artists", [])
                if not similar_artists:
                    continue

                # Evitar pedidos concorrentes se ainda há downloads ou importações recentes em curso
                pending_dls = load_pending_downloads()
                pending_injs = load_pending_injections()
                now_ts = time.time()
                active_pending_dls = {
                    k: v for k, v in pending_dls.items()
                    if (now_ts - v.get("added_at", now_ts)) < 180
                }
                if active_pending_dls or pending_injs:
                    continue

                total_so_far = active_sess.get("total_downloaded", 0)
                if max_session_tracks > 0 and total_so_far >= max_session_tracks:
                    continue

                # Cooldown de 40s entre lotes
                last_batch_time = active_sess.get("last_batch_time", 0)
                if time.time() - last_batch_time < 40:
                    continue

                pq_id = data.get("play_queue_id") or active_sess.get("play_queue_id")
                if not pq_id or not plex_server:
                    continue

                remaining_in_queue = get_play_queue_remaining_count(plex_server, pq_id, data.get("rating_key"))
                if remaining_in_queue is not None and remaining_in_queue <= buffer_trigger:
                    next_target = batch_size
                    if max_session_tracks > 0:
                        next_target = min(next_target, max_session_tracks - total_so_far)

                    if next_target <= 0:
                        continue

                    print(f"🎵 Auto-pilot [Buffer Trigger]: Faltam apenas {remaining_in_queue} faixas na PlayQueue {pq_id} (limiar <= {buffer_trigger}). A descarregar próximo lote de {next_target} músicas!")

                    seen_artists_in_session = set(active_sess.get("seen_artists", []))
                    history = load_history()
                    ignored_artists = load_ignored_artists()
                    recent_recommended = load_recent_recommended_artists(retention_days=30)

                    newly_downloaded = await download_next_discovery_batch(
                        target_count=next_target,
                        similar_artists=similar_artists,
                        seen_artists_in_session=seen_artists_in_session,
                        tracks_per_artist=tracks_per_artist,
                        plex_server=plex_server,
                        history=history,
                        ignored_artists=ignored_artists,
                        recent_recommended=recent_recommended,
                        batch_label=f"Buffer +{next_target}"
                    )

                    active_sess["seen_artists"] = list(seen_artists_in_session)
                    active_sess["total_downloaded"] = total_so_far + newly_downloaded
                    active_sess["last_batch_time"] = time.time()
                    save_active_session(active_sess)

        except Exception as e:
            print(f"Erro no loop do auto_pilot: {e}")

from app.importer import (
    lookup_musicbrainz,
    lookup_musicbrainz_album,
    tag_audio_file,
    tag_album_flac_file,
    validate_audio_file,
    organize_and_move_file,
    organize_and_move_album,
    find_file_in_downloads,
    trigger_plex_music_scan,
    inspect_flac_audio_quality
)
from plexapi.playqueue import PlayQueue
from plexapi.playlist import Playlist

def find_plex_track_for_meta(server, meta: dict):
    """
    Localiza no Plex a faixa recém-importada, priorizando a biblioteca de descoberta.
    """
    try:
        settings = load_settings()
        disc_lib_name = settings.get("PLEX_DISCOVERY_LIBRARY", "Discover")
        
        target_sections = []
        for sec in server.library.sections():
            if sec.title.lower() == disc_lib_name.lower() or 'discover' in sec.title.lower():
                target_sections.append(sec)
                
        for sec in server.library.sections():
            if sec not in target_sections and (sec.type == 'artist' or sec.title.lower() == 'music'):
                target_sections.append(sec)

        for sec in target_sections:
            try:
                tracks = sec.searchTracks(title=meta['title'])
                for t in tracks:
                    # 1. Faixa que reside no volume de descoberta
                    for m in getattr(t, 'media', []):
                        for p in getattr(m, 'parts', []):
                            p_file = p.file.lower()
                            if 'musicdiscovery' in p_file or 'playlistdiscovery' in p_file:
                                return t
                    # 2. Correspondência por artista e título
                    if t.grandparentTitle.lower() == meta['artist'].lower() and t.title.lower() == meta['title'].lower():
                        return t
            except Exception:
                continue
    except Exception as e:
        print(f"Erro ao pesquisar faixa no Plex: {e}")
    return None

async def find_plex_track_with_retry(server, meta: dict, retries: int = 4, delay: int = 3):
    for _ in range(retries):
        t = find_plex_track_for_meta(server, meta)
        if t:
            return t
        await asyncio.sleep(delay)
    return None

def inject_track_into_plex_queue_and_playlist(server, track, play_queue_id: int | None = None):
    """
    1. Injeta a faixa na PlayQueue ativa do Plexamp (Up Next).
    2. Adiciona a faixa à Playlist 'PlexDiscover' para acesso garantido.
    """
    # 1. Injetar na PlayQueue ativa do Plexamp (colocar no final de toda a fila)
    if play_queue_id:
        try:
            pq = PlayQueue.get(server, play_queue_id)
            existing_rating_keys = [str(getattr(item, 'ratingKey', '')) for item in pq.items]
            if str(track.ratingKey) not in existing_rating_keys:
                last_item = pq.items[-1] if pq.items else None
                pq.addItem(track, playNext=False)
                # O Plex por omissão coloca o item logo a seguir à faixa atual ("Up Next").
                # Movemos para o fim absoluto da fila para tocar APÓS o álbum completo:
                if last_item and last_item.ratingKey != track.ratingKey:
                    try:
                        pq.moveItem(track, after=last_item)
                    except Exception as move_err:
                        print(f"Aviso ao reposicionar faixa no fim da fila: {move_err}")
                print(f"🎵 [Plexamp Auto-Queue] Injetada com sucesso na fila (PlayQueue {play_queue_id}): {track.grandparentTitle} - {track.title}")
            else:
                print(f"[Plexamp Auto-Queue] Faixa já existe na fila PlayQueue {play_queue_id}")
        except Exception as e:
            print(f"Aviso ao injetar na PlayQueue {play_queue_id}: {e}")

    # 2. Adicionar à Playlist PlexDiscover
    try:
        playlist_name = "PlexDiscover"
        playlists = server.playlists()
        pl = next((p for p in playlists if p.title == playlist_name), None)
        if not pl:
            pl = Playlist.create(server, title=playlist_name, items=[track])
            print(f"📁 [Playlist Plex] Criada playlist '{playlist_name}' com: {track.grandparentTitle} - {track.title}")
        else:
            existing_pl_keys = [str(getattr(item, 'ratingKey', '')) for item in pl.items()]
            if str(track.ratingKey) not in existing_pl_keys:
                pl.addItems([track])
                print(f"📁 [Playlist Plex] Adicionada à playlist '{playlist_name}': {track.grandparentTitle} - {track.title}")
    except Exception as e:
        print(f"Aviso ao atualizar Playlist Plex: {e}")

async def process_and_import_file(local_file: str, artist_hint: str = "", title_hint: str = "") -> Optional[Dict]:
    """
    Valida a integridade, obtém tags no MusicBrainz, aplica tags e move para a pasta de descoberta.
    """
    if not os.path.exists(local_file):
        return None

    # Se não tínhamos o hint guardado, ler as tags existentes do próprio ficheiro de áudio
    if not artist_hint or not title_hint:
        try:
            import mutagen
            existing_audio = mutagen.File(local_file)
            if existing_audio:
                if hasattr(existing_audio, 'get'):
                    tag_a = existing_audio.get('artist') or existing_audio.get('ARTIST')
                    tag_t = existing_audio.get('title') or existing_audio.get('TITLE')
                    if tag_a and tag_t:
                        artist_hint = str(tag_a[0] if isinstance(tag_a, list) else tag_a)
                        title_hint = str(tag_t[0] if isinstance(tag_t, list) else tag_t)
                elif hasattr(existing_audio, 'tags') and existing_audio.tags:
                    tags = existing_audio.tags
                    tag_a = tags.get('TPE1') or tags.get('ARTIST')
                    tag_t = tags.get('TIT2') or tags.get('TITLE')
                    if tag_a and tag_t:
                        artist_hint = str(tag_a.text[0] if hasattr(tag_a, 'text') else tag_a)
                        title_hint = str(tag_t.text[0] if hasattr(tag_t, 'text') else tag_t)
        except Exception:
            pass

    if not artist_hint or not title_hint:
        clean_name = os.path.splitext(os.path.basename(local_file))[0]
        parts = clean_name.split(' - ')
        if len(parts) >= 2:
            if parts[0].strip().isdigit() and len(parts) == 2:
                parent_dir = os.path.basename(os.path.dirname(local_file))
                if parent_dir and not parent_dir.lower().startswith('download'):
                    parent_parts = parent_dir.split(' - ')
                    artist_hint = parent_parts[0].strip()
                else:
                    artist_hint = "Unknown"
                title_hint = parts[-1].strip()
            else:
                artist_hint = parts[0].strip()
                title_hint = parts[-1].strip()
        else:
            artist_hint = "Unknown"
            title_hint = clean_name

    # 0. Validar integridade e fluxo áudio
    if not validate_audio_file(local_file):
        print(f"Auto-import: Ficheiro inválido ou corrompido, a ignorar: {local_file}")
        update_queue_item_status(artist_hint, title_hint, "error", "Ficheiro corrompido ou incompleto")
        try:
            os.remove(local_file)
        except Exception:
            pass
        return None

    # 1. Metadados do MusicBrainz
    update_queue_item_status(artist_hint, title_hint, "tagging", "A obter tags no MusicBrainz...")
    meta = await lookup_musicbrainz(artist_hint, title_hint)
    print(f"Auto-import: Metadados MusicBrainz: {meta['artist']} - {meta['title']} ({meta['album']})")

    # 2. Aplicar tags
    tag_audio_file(local_file, meta)

    # 3. Mover e organizar para /music_discovery ou /music/Playlistdiscovery
    dest = organize_and_move_file(local_file, meta)
    print(f"Auto-import: Ficheiro importado para {dest}")
    update_queue_item_status(meta['artist'], meta['title'], "imported", "Guardado na biblioteca Discover", old_artist=artist_hint, old_title=title_hint)
    return meta

async def trigger_favorite_album_download(artist: str, album: str = "", track_title: str = "", manual: bool = False) -> Dict:
    """
    Descarrega o álbum completo oficial em FLAC 16-bit / 44.1 kHz (qualidade CD)
    para a biblioteca permanente do Plex quando uma música é favoritada.
    """
    artist_name = artist.strip() if artist else ""
    album_name = album.strip() if album else ""
    track_name = track_title.strip() if track_title else ""
    
    if not artist_name:
        return {"status": "error", "message": "Nome do artista não fornecido"}

    print(f"Favorito: A iniciar busca de álbum para '{artist_name}' - '{album_name or track_name}'")
    
    # 1. Obter metadados canónicos do álbum pelo MusicBrainz
    mb_album = await lookup_musicbrainz_album(artist_name, album_name, track_name)
    canonical_artist = mb_album.get("artist") or artist_name
    canonical_album = mb_album.get("album") or album_name or "Álbum Desconhecido"
    track_count = mb_album.get("track_count", 0)
    year = mb_album.get("year", "")

    # 2. Verificar se o álbum já existe na biblioteca permanente
    clean_art = re.sub(r'[\\/*?:"<>|]', '', canonical_artist).strip()
    clean_alb = re.sub(r'[\\/*?:"<>|]', '', canonical_album).strip()
    dest_check = os.path.join("/music", clean_art, clean_alb)
    if os.path.exists(dest_check):
        existing_files = [f for f in os.listdir(dest_check) if f.lower().endswith(('.flac', '.mp3', '.m4a'))]
        if len(existing_files) >= max(3, int(track_count * 0.7)):
            print(f"Favorito: Álbum '{canonical_album}' de '{canonical_artist}' já existe em /music ({len(existing_files)} faixas).")
            return {
                "status": "already_exists",
                "artist": canonical_artist,
                "album": canonical_album,
                "detail": f"Álbum já existe na biblioteca permanente ({len(existing_files)} faixas)",
                "message": "Álbum já existe na coleção definitiva"
            }

    # 3. Verificar se já existe um download ativo para este álbum
    album_downloads = load_album_downloads()
    for item in album_downloads:
        if item.get("artist", "").lower() == canonical_artist.lower() and item.get("album", "").lower() == canonical_album.lower():
            if item.get("status") in ["searching", "downloading", "tagging", "completed"]:
                print(f"Favorito: Download do álbum '{canonical_album}' já registado ({item.get('status')})")
                return item

    # 4. Criar registo de download pendente
    album_id = str(uuid.uuid4())
    item_record = {
        "id": album_id,
        "artist": canonical_artist,
        "album": canonical_album,
        "year": year,
        "track_title": track_name,
        "status": "searching",
        "detail": "A pesquisar versões FLAC 16-bit / 44.1 kHz no Soulseek...",
        "total_tracks": track_count,
        "completed_tracks": 0,
        "files": [],
        "musicbrainz": mb_album,
        "created_at": time.time(),
        "updated_at": time.time()
    }
    album_downloads.insert(0, item_record)
    save_album_downloads(album_downloads)

    # 5. Iniciar pesquisa no slskd
    settings = load_settings()
    slskd_url = settings.get("SLSKD_URL") or os.environ.get("SLSKD_URL")
    slskd_key = settings.get("SLSKD_API_KEY") or os.environ.get("SLSKD_API_KEY")
    if not slskd_url or not slskd_key:
        item_record["status"] = "error"
        item_record["detail"] = "slskd não configurado"
        item_record["updated_at"] = time.time()
        save_album_downloads(album_downloads)
        return item_record

    client = SlskdClient(url=slskd_url, api_key=slskd_key)
    candidate = await client.search_album(canonical_artist, canonical_album, expected_track_count=track_count)
    if not candidate:
        item_record["status"] = "error"
        item_record["detail"] = "Nenhuma versão FLAC 16/44 encontrada no Soulseek"
        item_record["updated_at"] = time.time()
        save_album_downloads(album_downloads)
        return item_record

    # 6. Agendar transferência em lote no slskd
    username = candidate.get("username")
    cand_files = candidate.get("files", [])
    
    item_record["username"] = username
    item_record["folder"] = candidate.get("folder", "")
    item_record["total_tracks"] = len(cand_files)
    item_record["files"] = [
        {
            "filename": f["filename"],
            "base_name": os.path.basename(f["filename"].replace('\\', '/')).lower(),
            "size": f.get("size", 0),
            "bitrate": f.get("bitrate", 0),
            "state": "Queued",
            "is_cd_quality": False,
            "quality_desc": ""
        }
        for f in cand_files
    ]
    item_record["status"] = "downloading"
    item_record["detail"] = f"A descarregar de {username} ({len(cand_files)} faixas em FLAC)"
    item_record["updated_at"] = time.time()
    save_album_downloads(album_downloads)

    queued = await client.download_batch(username, cand_files)
    if not queued:
        item_record["status"] = "error"
        item_record["detail"] = f"Falha ao enviar pedido de download ao slskd ({username})"
        item_record["updated_at"] = time.time()
        save_album_downloads(album_downloads)
        return item_record

    print(f"Favorito: {len(cand_files)} faixas do álbum '{canonical_album}' agendadas com sucesso no slskd!")
    return item_record

async def favorite_monitor_loop():
    """
    Monitoriza a reprodução no Plexamp a cada 12 segundos.
    Quando uma faixa é favoritada (userRating >= 8.0 ou coração),
    aciona automaticamente o download do álbum completo em FLAC 16-bit / 44.1 kHz.
    """
    while True:
        await asyncio.sleep(12)
        try:
            settings = load_settings()
            if not settings.get("AUTO_DOWNLOAD_FAVORITE_ALBUMS", True):
                continue

            now_data = _get_now_playing_data()
            if not now_data.get("is_playing"):
                continue

            user_rating = now_data.get("user_rating", 0)
            if user_rating >= 8.0:
                artist = now_data.get("artist")
                album = now_data.get("album")
                track = now_data.get("track")
                if artist:
                    fav_key = f"{artist} - {album or track}".lower()
                    if not is_favorite_processed(fav_key):
                        mark_favorite_processed(fav_key)
                        print(f"Favorito detetado no Plexamp ({user_rating}/10): {artist} - {track} ({album}). A iniciar download do álbum FLAC 16/44!")
                        asyncio.create_task(trigger_favorite_album_download(artist, album or "", track or ""))
        except Exception:
            pass

async def auto_import_loop():
    """
    Monitoriza o slskd e a pasta de downloads de 20 em 20 segundos por transferências concluídas.
    Reconcilia faixas normais de descoberta e álbuns completos favoritos em FLAC 16/44.
    """
    while True:
        await asyncio.sleep(20)
        try:
            settings = load_settings()
            slskd_url = settings.get("SLSKD_URL") or os.environ.get("SLSKD_URL")
            slskd_key = settings.get("SLSKD_API_KEY") or os.environ.get("SLSKD_API_KEY")
            if not slskd_url or not slskd_key:
                continue

            client = SlskdClient(url=slskd_url, api_key=slskd_key)
            transfers = []
            try:
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    res = await http_client.get(f"{slskd_url.rstrip('/')}/api/v0/transfers/downloads", headers={"X-API-KEY": slskd_key})
                    if res.status_code == 200:
                        transfers = res.json()
            except Exception as tr_err:
                print(f"Aviso ao consultar transferências slskd: {tr_err}")

            imported_transfers = load_imported_transfers()
            pending_downloads = load_pending_downloads()
            imported_any = False
            newly_imported_metas = []

            # Carregar registo de álbuns ativos para isolar do fluxo de descoberta
            album_downloads = load_album_downloads()
            album_active_basenames = {
                f.get("base_name", "").lower()
                for alb in album_downloads
                if alb.get("status") in ["searching", "downloading", "tagging"]
                for f in alb.get("files", [])
                if f.get("base_name")
            }

            # 1. Processar transferências ativas ou concluídas do SLSKD (apenas faixas de descoberta)
            for user_transfers in transfers:
                username = user_transfers.get("username")
                for d in user_transfers.get("directories", []):
                    for f in d.get("files", []):
                        state = f.get("state", "")
                        transfer_id = f.get("id")
                        filename = f.get("filename", "")
                        base_name = os.path.basename(filename).replace('\\', '/').split('/')[-1].lower()

                        # Se este ficheiro pertence a um download de álbum ativo em FLAC, NÃO processar como descoberta!
                        if base_name in album_active_basenames:
                            continue

                        # Se falhou, foi cancelado ou rejeitado no SLSKD
                        if any(err_st in state for err_st in ["Errored", "Cancelled", "TimedOut", "Rejected"]):
                            if base_name in pending_downloads:
                                meta_hint = pending_downloads.pop(base_name)
                                save_pending_downloads(pending_downloads)
                                update_queue_item_status(meta_hint.get("artist", ""), meta_hint.get("title", ""), "error", f"Transferência cancelada/falhou: {state}")
                            if transfer_id and username:
                                try:
                                    await client.remove_download(username, transfer_id)
                                except Exception:
                                    pass
                            continue

                        if state == "Completed, Succeeded" and transfer_id and transfer_id not in imported_transfers:
                            local_file = find_file_in_downloads(base_name)
                            if local_file and os.path.exists(local_file):
                                print(f"Auto-import: Ficheiro descarregado detetado (SLSKD): {local_file}")
                                meta_hint = pending_downloads.get(base_name, {})
                                meta = await process_and_import_file(local_file, meta_hint.get("artist", ""), meta_hint.get("title", ""))
                                save_imported_transfer(transfer_id)
                                if base_name in pending_downloads:
                                    del pending_downloads[base_name]
                                    save_pending_downloads(pending_downloads)
                                if transfer_id and username:
                                    try:
                                        await client.remove_download(username, transfer_id)
                                    except Exception:
                                        pass
                                if meta:
                                    newly_imported_metas.append(meta)
                                    imported_any = True

            # 1.5 Processar Transferências de Álbuns Completos em FLAC 16/44 (para a biblioteca permanente)
            album_downloads = load_album_downloads()
            album_updated = False
            for album in album_downloads:
                if album.get("status") != "downloading":
                    continue

                files = album.get("files", [])
                for f in files:
                    if f.get("state") == "Completed, Succeeded":
                        continue
                    base_name = f.get("base_name", "").lower()
                    local_file = find_file_in_downloads(base_name)
                    if local_file and os.path.exists(local_file):
                        f["state"] = "Completed, Succeeded"
                        f["local_path"] = local_file
                        q_info = inspect_flac_audio_quality(local_file)
                        f["is_cd_quality"] = q_info.get("is_cd_quality", False)
                        f["quality_desc"] = q_info.get("description", "")
                        album_updated = True

                completed_count = sum(1 for f in files if f.get("state") == "Completed, Succeeded")
                album["completed_tracks"] = completed_count
                total_count = album.get("total_tracks", len(files))
                album["detail"] = f"{completed_count}/{total_count} faixas transferidas"

                ready_files = [f.get("local_path") for f in files if f.get("local_path") and os.path.exists(f.get("local_path"))]
                is_finished = (completed_count >= total_count) or (total_count > 0 and completed_count >= int(total_count * 0.85) and not any(
                    any(os.path.basename(tr_f.get("filename", "")).lower() in [f.get("base_name") for f in files if f.get("state") != "Completed, Succeeded"]
                        for tr_f in d.get("files", []))
                    for ut in transfers for d in ut.get("directories", [])
                ))

                if is_finished and len(ready_files) >= max(3, int(total_count * 0.7)):
                    print(f"Auto-import Álbum: Álbum '{album.get('artist')} - {album.get('album')}' pronto para importar ({len(ready_files)} faixas)!")
                    album["status"] = "tagging"
                    album["detail"] = "A validar áudio e a aplicar tags oficiais do MusicBrainz..."
                    save_album_downloads(album_downloads)

                    mb_album = album.get("musicbrainz", {})
                    dest_folder = organize_and_move_album(ready_files, mb_album, mb_album.get("tracks", []), dest_base="/music")

                    album["status"] = "completed"
                    cd_count = sum(1 for f in files if f.get("is_cd_quality"))
                    album["detail"] = f"Guardado na Coleção Permanente ({len(ready_files)} faixas, FLAC 16-bit / 44.1 kHz)"
                    album["dest_folder"] = dest_folder
                    album_updated = True

                    # Registar transferências como importadas para evitar qualquer reprocessamento
                    for ut in transfers:
                        for d in ut.get("directories", []):
                            for tr_f in d.get("files", []):
                                tr_b = os.path.basename(tr_f.get("filename", "")).replace('\\', '/').split('/')[-1].lower()
                                if tr_b in [f.get("base_name", "").lower() for f in files]:
                                    if tr_f.get("id"):
                                        save_imported_transfer(tr_f["id"])

                    token = settings.get("PLEX_TOKEN")
                    if token:
                        try:
                            server = get_plex_server(token)
                            perm_lib = settings.get("PLEX_PERMANENT_LIBRARY", "Music")
                            trigger_plex_music_scan(server, library_name=perm_lib)
                            print(f"Scan à biblioteca permanente '{perm_lib}' do Plex acionado para o álbum {album.get('album')}!")
                        except Exception as px_err:
                            print(f"Aviso ao acionar scan ao Plex para álbum permanente: {px_err}")

            if album_updated:
                save_album_downloads(album_downloads)

            # 2. Reconciliação direta de pending_downloads (ficheiros já no disco ou downloads que expiraram)
            pending_downloads = load_pending_downloads()
            now_ts = time.time()
            stale_keys = []
            for base_name, hint in list(pending_downloads.items()):
                local_file = find_file_in_downloads(base_name)
                if local_file and os.path.exists(local_file):
                    print(f"Auto-import: Ficheiro pendente encontrado no disco em /downloads: {local_file}")
                    meta = await process_and_import_file(local_file, hint.get("artist", ""), hint.get("title", ""))
                    if meta:
                        newly_imported_metas.append(meta)
                        imported_any = True
                    stale_keys.append(base_name)
                else:
                    added_at = hint.get("added_at")
                    # Se expirou (> 180s ou sem timestamp e sem transferência ativa)
                    if not added_at or (now_ts - added_at > 180):
                        is_active = any(
                            any(os.path.basename(f.get("filename", "")).lower() == base_name for f in d.get("files", []))
                            for ut in transfers for d in ut.get("directories", [])
                        )
                        if not is_active:
                            print(f"Auto-import: Download expirou sem resposta: {hint.get('artist')} - {hint.get('title')}")
                            update_queue_item_status(hint.get("artist", ""), hint.get("title", ""), "error", "Download expirou ou cancelado")
                            stale_keys.append(base_name)

            if stale_keys:
                pending_downloads = load_pending_downloads()
                for k in stale_keys:
                    pending_downloads.pop(k, None)
                save_pending_downloads(pending_downloads)

            # 3. Varrer a pasta /downloads por ficheiros de áudio prontos (que não pertencem a álbuns ativos)
            album_active_basenames = {
                f.get("base_name", "").lower()
                for alb in load_album_downloads()
                if alb.get("status") in ["searching", "downloading", "tagging"]
                for f in alb.get("files", [])
                if f.get("base_name")
            }

            if os.path.exists("/downloads"):
                for p_audio in list(Path("/downloads").rglob("*")):
                    if p_audio.is_file() and p_audio.suffix.lower() in [".flac", ".mp3", ".m4a", ".ogg"]:
                        if p_audio.name.lower() in album_active_basenames:
                            continue
                        is_active_dl = any(
                            any(os.path.basename(f.get("filename", "")).lower() == p_audio.name.lower() for f in d.get("files", []))
                            for ut in transfers for d in ut.get("directories", [])
                        )
                        if not is_active_dl:
                            print(f"Auto-import: Ficheiro de áudio detetado em /downloads: {p_audio}")
                            meta = await process_and_import_file(str(p_audio))
                            if meta:
                                newly_imported_metas.append(meta)
                                imported_any = True

            # Manter a fila de downloads do slskd limpa e sem transferências concluídas acumuladas
            try:
                await client.clear_completed_downloads()
            except Exception:
                pass

            # Adicionar novas faixas importadas à lista pendente de injeção
            pending_injections = load_pending_injections()
            if newly_imported_metas:
                for n_meta in newly_imported_metas:
                    # Evitar duplicados na lista pendente
                    if not any(p.get('artist', '').lower() == n_meta.get('artist', '').lower() and p.get('title', '').lower() == n_meta.get('title', '').lower() for p in pending_injections):
                        pending_injections.append(n_meta)
                save_pending_injections(pending_injections)

            token = settings.get("PLEX_TOKEN")
            if token and pending_injections:
                server = get_plex_server(token)
                if imported_any:
                    disc_lib = settings.get("PLEX_DISCOVERY_LIBRARY", "Discover")
                    trigger_plex_music_scan(server, library_name=disc_lib)
                    
                # Obter a PlayQueue ativa
                active_sess = load_active_session()
                pq_id = active_sess.get("play_queue_id")
                if not pq_id:
                    live_data = _get_now_playing_data()
                    pq_id = live_data.get("play_queue_id")
                    
                remaining_injections = []
                for imp_meta in pending_injections:
                    track = await find_plex_track_with_retry(server, imp_meta, retries=2, delay=1)
                    if track:
                        inject_track_into_plex_queue_and_playlist(server, track, play_queue_id=pq_id)
                        update_queue_item_status(imp_meta['artist'], imp_meta['title'], "injected", "Disponível e injetada no Plexamp!")
                    else:
                        attempts = imp_meta.get('attempts', 0) + 1
                        imp_meta['attempts'] = attempts
                        if attempts <= 5:
                            print(f"Auto-import: Plex ainda não indexou {imp_meta['artist']} - {imp_meta['title']} (tentativa {attempts}/5)")
                            update_queue_item_status(imp_meta['artist'], imp_meta['title'], "imported", "A aguardar indexação do Plex...")
                            remaining_injections.append(imp_meta)
                        else:
                            print(f"Auto-import: Desistência após 5 tentativas de indexação para {imp_meta['artist']} - {imp_meta['title']}.")
                            update_queue_item_status(imp_meta['artist'], imp_meta['title'], "error", "Tempo limite de indexação excedido")
                        
                save_pending_injections(remaining_injections)
        except Exception as e:
            print(f"Erro no auto_import_loop: {e}")

CLEANUP_STATE_FILE = os.path.join(DATA_DIR, "cleanup_state.json")

def load_cleanup_state() -> dict:
    if os.path.exists(CLEANUP_STATE_FILE):
        try:
            with open(CLEANUP_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cleanup_state(state: dict):
    try:
        with open(CLEANUP_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass

def get_discovery_folders() -> list[str]:
    folders = []
    if os.path.exists("/music_discovery"):
        folders.append("/music_discovery")
    legacy = os.path.join("/music", "Playlistdiscovery")
    if os.path.exists(legacy):
        folders.append(legacy)
    return folders

def playlist_discovery_has_files() -> bool:
    for folder in get_discovery_folders():
        for root, dirs, files in os.walk(folder):
            if files:
                return True
    return False

def clear_playlist_discovery_folder():
    for folder in get_discovery_folders():
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"Erro ao apagar {item_path}: {e}")

async def auto_cleanup_loop():
    """
    Monitoriza a reprodução no Plex.
    Se a pasta de descoberta contiver ficheiros e tiver passado 1 hora (3600 segundos)
    desde que a sessão de reprodução parou/terminou, apaga todos os ficheiros temporários
    e aciona novo scan à biblioteca Discover do Plex.
    """
    while True:
        await asyncio.sleep(30)
        try:
            settings = load_settings()
            if not settings.get("AUTO_PILOT", False):
                continue
                
            has_files = playlist_discovery_has_files()
            if not has_files:
                save_cleanup_state({})
                continue
                
            now_playing = _get_now_playing_data()
            is_playing = now_playing.get("is_playing", False)
            state = load_cleanup_state()
            
            if is_playing:
                # Sessão de música ainda ativa: reset ao temporizador de paragem
                if state.get("stopped_at") is not None:
                    save_cleanup_state({})
            else:
                # Sessão parada/inativa
                stopped_at = state.get("stopped_at")
                if stopped_at is None:
                    stopped_at = time.time()
                    state["stopped_at"] = stopped_at
                    save_cleanup_state(state)
                    print("Auto-cleanup: Sessão parou. Temporizador de 1 hora iniciado para limpeza da biblioteca de descoberta.")
                else:
                    elapsed = time.time() - stopped_at
                    # 1 hora = 3600 segundos
                    if elapsed >= 3600:
                        print(f"Auto-cleanup: 1 hora decorrida desde a paragem da sessão ({elapsed:.0f}s). A limpar descoberta...")
                        clear_playlist_discovery_folder()
                        save_cleanup_state({})
                        
                        token = settings.get("PLEX_TOKEN")
                        if token:
                            server = get_plex_server(token)
                            disc_lib = settings.get("PLEX_DISCOVERY_LIBRARY", "Discover")
                            trigger_plex_music_scan(server, library_name=disc_lib, purge_orphans=True)
                            print(f"Auto-cleanup: Novo scan e purga do Plex acionados na biblioteca '{disc_lib}'.")
                            try:
                                for pl in server.playlists():
                                    if pl.title == "PlexDiscover":
                                        pl.delete()
                                        print("Auto-cleanup: Playlist 'PlexDiscover' apagada com sucesso após 1h de inatividade.")
                            except Exception as pl_err:
                                print(f"Erro ao remover playlist na limpeza: {pl_err}")
                        save_active_session({})
        except Exception as e:
            print(f"Erro no auto_cleanup_loop: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_pilot_loop())
    asyncio.create_task(auto_import_loop())
    asyncio.create_task(auto_cleanup_loop())
    asyncio.create_task(favorite_monitor_loop())

