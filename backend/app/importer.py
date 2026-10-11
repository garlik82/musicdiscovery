import os
import re
import shutil
import httpx
import mutagen
from pathlib import Path
from typing import Optional, Dict

def sanitize_name(name: str) -> str:
    """Remove caracteres inválidos para pastas e nomes de ficheiros."""
    if not name:
        return "Unknown"
    # Remover caracteres proibidos em sistemas de ficheiros
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean if clean else "Unknown"

async def lookup_musicbrainz(artist: str, title: str) -> Optional[Dict]:
    """
    Pesquisa na API do MusicBrainz pelo artista e música para obter metadados oficiais.
    """
    clean_artist = re.sub(r'\(.*?\)|\[.*?\]', '', artist).strip()
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
    
    headers = {
        "User-Agent": "PlexDiscover/1.0 (contact@plexdiscover.local)"
    }
    query = f'recording:"{clean_title}" AND artist:"{clean_artist}"'
    url = f"https://musicbrainz.org/ws/2/recording/?query={httpx.URL('', params={'q': query}).params['q']}&fmt=json"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                recordings = data.get("recordings", [])
                if recordings:
                    rec = recordings[0]
                    artist_name = rec.get("artist-credit", [{}])[0].get("name", clean_artist)
                    title_name = rec.get("title", clean_title)
                    releases = rec.get("releases", [])
                    album_name = releases[0].get("title", "Singles") if releases else "Singles"
                    date_val = releases[0].get("date", "") if releases else ""
                    
                    return {
                        "artist": artist_name,
                        "title": title_name,
                        "album": album_name,
                        "date": date_val,
                        "musicbrainz_trackid": rec.get("id"),
                        "musicbrainz_albumid": releases[0].get("id") if releases else None
                    }
    except Exception as e:
        print(f"Erro na pesquisa MusicBrainz: {e}")
        
    return {
        "artist": clean_artist,
        "title": clean_title,
        "album": "Singles",
        "date": "",
        "musicbrainz_trackid": None,
        "musicbrainz_albumid": None
    }

def tag_audio_file(file_path: str, meta: Dict):
    """
    Aplica as tags ao ficheiro de áudio usando a biblioteca mutagen.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(file_path)
            audio["TITLE"] = meta["title"]
            audio["ARTIST"] = meta["artist"]
            audio["ALBUM"] = meta["album"]
            if meta.get("date"):
                audio["DATE"] = str(meta["date"])
            if meta.get("musicbrainz_trackid"):
                audio["MUSICBRAINZ_TRACKID"] = meta["musicbrainz_trackid"]
            if meta.get("musicbrainz_albumid"):
                audio["MUSICBRAINZ_ALBUMID"] = meta["musicbrainz_albumid"]
            audio.save()
            
        elif ext == ".mp3":
            from mutagen.easyid3 import EasyID3
            try:
                audio = EasyID3(file_path)
            except Exception:
                from mutagen.id3 import ID3
                id3 = ID3()
                id3.save(file_path)
                audio = EasyID3(file_path)
            audio["title"] = meta["title"]
            audio["artist"] = meta["artist"]
            audio["album"] = meta["album"]
            if meta.get("date"):
                audio["date"] = str(meta["date"])
            audio.save()
            
        elif ext in [".m4a", ".mp4"]:
            from mutagen.mp4 import MP4
            audio = MP4(file_path)
            audio["\xa9nam"] = meta["title"]
            audio["\xa9ART"] = meta["artist"]
            audio["\xa9alb"] = meta["album"]
            if meta.get("date"):
                audio["\xa9day"] = str(meta["date"])
            audio.save()
    except Exception as e:
        print(f"Erro ao escrever tags em {file_path}: {e}")

def validate_audio_file(file_path: str, min_size_bytes: int = 500 * 1024) -> bool:
    """
    Valida a integridade do ficheiro áudio com mutagen.
    Garante que o ficheiro tem tamanho suficiente (> 500KB) e cabeçalhos legíveis com duração > 15s.
    """
    if not os.path.exists(file_path):
        return False
        
    size = os.path.getsize(file_path)
    if size < min_size_bytes:
        print(f"Validação falhou: Ficheiro demasiado pequeno ({size} bytes): {file_path}")
        return False
        
    try:
        audio = mutagen.File(file_path)
        if audio is None or audio.info is None:
            print(f"Validação falhou: Mutagen não reconheceu o fluxo de áudio: {file_path}")
            return False
            
        length = getattr(audio.info, 'length', 0)
        if length < 15:
            print(f"Validação falhou: Duração de áudio demasiado curta ({length:.1f}s): {file_path}")
            return False
            
        return True
    except Exception as e:
        print(f"Validação de áudio falhou com erro: {e}")
        return False

def organize_and_move_file(source_path: str, meta: Dict) -> str:
    """
    Move o ficheiro para a biblioteca dedicada de descoberta:
    /music_discovery/{Artista}/{Album}/{titulo}.ext
    (ou fallback para /music/Playlistdiscovery se /music_discovery não estiver disponível).
    """
    artist = sanitize_name(meta["artist"])
    album = sanitize_name(meta["album"])
    title = sanitize_name(meta["title"])
    ext = os.path.splitext(source_path)[1].lower()
    
    # Prioridade para o volume isolado /music_discovery
    if os.path.exists("/music_discovery"):
        dest_dir = os.path.join("/music_discovery", artist, album)
    else:
        dest_dir = os.path.join("/music", "Playlistdiscovery", artist, album)
        
    os.makedirs(dest_dir, exist_ok=True)
    
    dest_file = os.path.join(dest_dir, f"{title}{ext}")
    
    # Se já existir um ficheiro com o mesmo nome, adicionar um sufixo
    if os.path.exists(dest_file) and os.path.abspath(dest_file) != os.path.abspath(source_path):
        dest_file = os.path.join(dest_dir, f"{title}_new{ext}")
        
    shutil.move(source_path, dest_file)
    print(f"Ficheiro movido com sucesso para: {dest_file}")
    
    # Tentar limpar pasta de download de origem se ficou vazia
    try:
        parent_dir = os.path.dirname(source_path)
        if os.path.exists(parent_dir) and not os.listdir(parent_dir) and parent_dir != "/downloads":
            os.rmdir(parent_dir)
    except Exception:
        pass
        
    return dest_file

def find_file_in_downloads(filename_hint: str, base_downloads_dir: str = "/downloads") -> Optional[str]:
    """
    Procura o ficheiro transferido na pasta /downloads (mesmo em subpastas).
    """
    base_name = os.path.basename(filename_hint).replace('\\', '/')
    base_name = base_name.split('/')[-1]
    
    if not os.path.exists(base_downloads_dir):
        return None
        
    for p in Path(base_downloads_dir).rglob("*"):
        if p.is_file() and p.name.lower() == base_name.lower():
            return str(p)
            
    return None

def purge_deleted_plex_tracks(server, library_name: Optional[str] = None):
    """
    Remove do Plex quaisquer faixas órfãs (cujo ficheiro físico já não existe no disco),
    garantindo que itens apagados desaparecem imediatamente da biblioteca.
    """
    try:
        sections = server.library.sections()
        target_sec = None
        if library_name:
            for sec in sections:
                if sec.title.lower() == library_name.lower():
                    target_sec = sec
                    break

        if not target_sec:
            for sec in sections:
                if 'discover' in sec.title.lower():
                    target_sec = sec
                    break

        if not target_sec:
            return

        for artist in target_sec.all():
            artist_has_tracks = False
            for track in artist.tracks():
                track_exists = False
                for media in track.media:
                    for part in media.parts:
                        p_file = part.file
                        # Mapear caminhos do host (/media/Misc/MusicDiscovery ou /volume1/Media/Misc/MusicDiscovery)
                        # para o volume montado no contentor (/music_discovery ou /music)
                        local_p = p_file
                        if '/media/Misc/MusicDiscovery' in p_file:
                            local_p = p_file.replace('/media/Misc/MusicDiscovery', '/music_discovery')
                        elif '/volume1/Media/Misc/MusicDiscovery' in p_file:
                            local_p = p_file.replace('/volume1/Media/Misc/MusicDiscovery', '/music_discovery')
                        elif '/media/Music' in p_file:
                            local_p = p_file.replace('/media/Music', '/music')
                        elif '/volume1/Media/Music' in p_file:
                            local_p = p_file.replace('/volume1/Media/Music', '/music')

                        if os.path.exists(local_p):
                            track_exists = True
                            break
                    if track_exists:
                        break

                if not track_exists:
                    try:
                        track.delete()
                    except Exception:
                        pass
                else:
                    artist_has_tracks = True

            if not artist_has_tracks:
                try:
                    artist.delete()
                except Exception:
                    pass
    except Exception as e:
        print(f"Aviso ao purgar faixas órfãs do Plex: {e}")

def trigger_plex_music_scan(server, library_name: Optional[str] = None, purge_orphans: bool = False):
    """
    Pede atualização da biblioteca no Plex.
    Prioriza a biblioteca de descoberta ('Discover' ou configurada), com fallback para 'Music'.
    """
    try:
        sections = server.library.sections()
        target_sec = None
        if library_name:
            for sec in sections:
                if sec.title.lower() == library_name.lower():
                    target_sec = sec
                    break

        if not target_sec:
            for sec in sections:
                if 'discover' in sec.title.lower():
                    target_sec = sec
                    break

        if not target_sec:
            for sec in sections:
                if sec.type == "artist" or sec.title.lower() == "music":
                    target_sec = sec
                    break

        if target_sec:
            print(f"A pedir scan ao Plex para biblioteca '{target_sec.title}'...")
            target_sec.update()
            try:
                target_sec.emptyTrash()
            except Exception:
                pass
            if purge_orphans:
                purge_deleted_plex_tracks(server, library_name=target_sec.title)
            return True
    except Exception as e:
        print(f"Erro ao pedir scan ao Plex: {e}")
    return False


