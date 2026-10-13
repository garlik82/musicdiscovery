import os
import re
import shutil
import httpx
import mutagen
from pathlib import Path
from typing import Optional, Dict, List, Any

def sanitize_name(name: str) -> str:
    """Remove caracteres inválidos para pastas e nomes de ficheiros."""
    if not name:
        return "Unknown"
    # Remover caracteres proibidos em sistemas de ficheiros
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean if clean else "Unknown"

def is_live_or_compilation(release_dict: Dict) -> bool:
    """
    Verifica se um release do MusicBrainz é ao vivo, compilação, demo ou bootleg.
    """
    rg = release_dict.get("release-group", {})
    stypes = [s.lower() for s in (rg.get("secondary-types") or [])]
    bad_stypes = {"live", "compilation", "remix", "demo", "bootleg", "soundtrack", "mixtape", "dj-mix"}
    if any(st in bad_stypes for st in stypes):
        return True
    
    title = release_dict.get("title", "").lower()
    live_patterns = [
        r'\blive(\s+at|\s+in|\s+from)?\b',
        r'\(live\)',
        r'\[live\]',
        r'\bin\s+concert\b',
        r'\ben\s+vivo\b',
        r'\bbootleg\b',
        r'\btour\b',
        r'\bunplugged\b',
        r'\bgreatest\s+hits\b',
        r'\bbest\s+of\b',
        r'\bthe\s+essential\b',
        r'\banthology\b'
    ]
    if any(re.search(pat, title) for pat in live_patterns):
        return True
        
    return False

async def lookup_musicbrainz(artist: str, title: str) -> Optional[Dict]:
    """
    Pesquisa na API do MusicBrainz pelo artista e música para obter metadados oficiais.
    Prioriza sempre álbuns de estúdio oficiais, rejeitando versões ao vivo e compilações.
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
                
                chosen_rec = None
                chosen_release = None
                
                def matches_artist(rel):
                    rel_artists = [ac.get("name", "").lower() for ac in rel.get("artist-credit", [])]
                    if not rel_artists:
                        return True
                    ca = clean_artist.lower()
                    return any(ca in a or a in ca for a in rel_artists)

                # 1. Prioridade máxima: Álbum oficial de estúdio do próprio artista
                for rec in recordings:
                    for rel in rec.get("releases", []):
                        if not matches_artist(rel):
                            continue
                        rg = rel.get("release-group", {})
                        p_type = rg.get("primary-type", "")
                        status = rel.get("status", "")
                        if p_type == "Album" and status == "Official" and not is_live_or_compilation(rel):
                            chosen_rec = rec
                            chosen_release = rel
                            break
                    if chosen_release:
                        break
                
                # 2. Prioridade secundária: Álbum ou EP não-live do artista
                if not chosen_release:
                    for rec in recordings:
                        for rel in rec.get("releases", []):
                            if not matches_artist(rel):
                                continue
                            rg = rel.get("release-group", {})
                            p_type = rg.get("primary-type", "")
                            if p_type in ["Album", "EP", "Single"] and not is_live_or_compilation(rel):
                                chosen_rec = rec
                                chosen_release = rel
                                break
                        if chosen_release:
                            break

                # 3. Qualquer release que não seja ao vivo
                if not chosen_release:
                    for rec in recordings:
                        for rel in rec.get("releases", []):
                            if not matches_artist(rel):
                                continue
                            if not is_live_or_compilation(rel):
                                chosen_rec = rec
                                chosen_release = rel
                                break
                        if chosen_release:
                            break

                # 4. Fallback final caso só haja lançamentos ao vivo
                if not chosen_release and recordings:
                    chosen_rec = recordings[0]
                    rels = chosen_rec.get("releases", [])
                    chosen_release = rels[0] if rels else None

                if chosen_rec:
                    artist_name = chosen_rec.get("artist-credit", [{}])[0].get("name", clean_artist)
                    title_name = chosen_rec.get("title", clean_title)
                    album_name = chosen_release.get("title", "Singles") if chosen_release else "Singles"
                    date_val = chosen_release.get("date", "") if chosen_release else ""
                    
                    return {
                        "artist": artist_name,
                        "title": title_name,
                        "album": album_name,
                        "date": date_val,
                        "musicbrainz_trackid": chosen_rec.get("id"),
                        "musicbrainz_albumid": chosen_release.get("id") if chosen_release else None
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

def inspect_flac_audio_quality(file_path: str) -> Dict:
    """
    Inspeciona um ficheiro FLAC com mutagen para verificar a taxa de amostragem
    e a profundidade de bits (ex: 16-bit / 44.1 kHz CD Quality).
    """
    if not os.path.exists(file_path):
        return {"valid": False, "error": "Ficheiro não existe", "is_cd_quality": False, "description": "Inexistente"}
        
    try:
        from mutagen.flac import FLAC
        audio = FLAC(file_path)
        sample_rate = getattr(audio.info, 'sample_rate', 0)
        bits_per_sample = getattr(audio.info, 'bits_per_sample', 0)
        channels = getattr(audio.info, 'channels', 2)
        duration = getattr(audio.info, 'length', 0)
        
        is_cd_quality = (sample_rate == 44100 and bits_per_sample == 16)
        desc = f"FLAC {bits_per_sample}-bit / {sample_rate/1000:.1f} kHz"
        
        return {
            "valid": True,
            "sample_rate": sample_rate,
            "bits_per_sample": bits_per_sample,
            "channels": channels,
            "duration": duration,
            "is_cd_quality": is_cd_quality,
            "description": desc
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "is_cd_quality": False,
            "description": "FLAC Desconhecido"
        }

async def lookup_musicbrainz_album(artist: str, album: str = "", track_title: str = "") -> Optional[Dict]:
    """
    Pesquisa na API do MusicBrainz pelo álbum oficial de estúdio do artista.
    Devolve metadados canónicos e a lista oficial de faixas.
    """
    clean_artist = re.sub(r'\(.*?\)|\[.*?\]', '', artist).strip()
    clean_album = re.sub(r'\(.*?\)|\[.*?\]', '', album).strip() if album else ""
    clean_track = re.sub(r'\(.*?\)|\[.*?\]', '', track_title).strip() if track_title else ""
    
    headers = {
        "User-Agent": "PlexDiscover/1.0 (contact@plexdiscover.local)"
    }
    
    release_id = None
    canonical_album = clean_album
    canonical_artist = clean_artist
    
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            # 1. Se temos o nome do álbum, pesquisar releases diretamente
            clean_album_studio = re.sub(r'\b(live(\s+at|\s+in|\s+from)?.*|concert|tour|bootleg)\b', '', clean_album, flags=re.IGNORECASE).strip()
            album_queries = [clean_album]
            if clean_album_studio and clean_album_studio.lower() != clean_album.lower():
                album_queries.append(clean_album_studio)

            for alb_q in album_queries:
                if not alb_q or alb_q.lower() in ["singles", "unknown", "desconhecido"]:
                    continue
                query = f'release:"{alb_q}" AND artist:"{clean_artist}"'
                url = f"https://musicbrainz.org/ws/2/release/?query={httpx.URL('', params={'q': query}).params['q']}&fmt=json"
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    releases = data.get("releases", [])
                    # Dar prioridade a lançamentos oficiais de estúdio (Album) sem Live
                    for r in releases:
                        status = r.get("status", "")
                        rg = r.get("release-group", {})
                        p_type = rg.get("primary-type", "")
                        if (p_type == "Album" or status == "Official") and not is_live_or_compilation(r):
                            release_id = r.get("id")
                            canonical_album = r.get("title", alb_q)
                            canonical_artist = r.get("artist-credit", [{}])[0].get("name", clean_artist)
                            break
                    if release_id:
                        break

            # 2. Se não encontramos pelo álbum, pesquisar pela música de referência
            if not release_id and clean_track:
                query = f'recording:"{clean_track}" AND artist:"{clean_artist}"'
                url = f"https://musicbrainz.org/ws/2/recording/?query={httpx.URL('', params={'q': query}).params['q']}&fmt=json"
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    recordings = data.get("recordings", [])
                    if recordings:
                        for rec in recordings:
                            for r in rec.get("releases", []):
                                status = r.get("status", "")
                                rg = r.get("release-group", {})
                                p_type = rg.get("primary-type", "")
                                if (p_type == "Album" or status == "Official") and not is_live_or_compilation(r):
                                    release_id = r.get("id")
                                    canonical_album = r.get("title", clean_album)
                                    canonical_artist = rec.get("artist-credit", [{}])[0].get("name", clean_artist)
                                    break
                            if release_id:
                                break
                        # Fallback se não houver álbum de estúdio puro
                        if not release_id and recordings and recordings[0].get("releases"):
                            for r in recordings[0]["releases"]:
                                if not is_live_or_compilation(r):
                                    release_id = r.get("id")
                                    canonical_album = r.get("title", clean_album)
                                    break
                            if not release_id:
                                r0 = recordings[0]["releases"][0]
                                release_id = r0.get("id")
                                canonical_album = r0.get("title", clean_album)

            # 3. Se temos o release_id, obter o alinhamento completo de faixas (tracklist)
            if release_id:
                detail_url = f"https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings+artist-credits&fmt=json"
                d_res = await client.get(detail_url, headers=headers)
                if d_res.status_code == 200:
                    rel_data = d_res.json()
                    media = rel_data.get("media", [])
                    tracks = []
                    pos = 1
                    for m in media:
                        for t in m.get("tracks", []):
                            rec = t.get("recording", {})
                            tracks.append({
                                "position": t.get("position", pos),
                                "title": t.get("title", rec.get("title", f"Track {pos}")),
                                "length": t.get("length", rec.get("length", 0)),
                                "id": rec.get("id", t.get("id")),
                            })
                            pos += 1
                            
                    date_val = rel_data.get("date", "")
                    year_val = date_val.split("-")[0] if date_val else ""
                    return {
                        "artist": canonical_artist,
                        "album": canonical_album,
                        "release_id": release_id,
                        "date": date_val,
                        "year": year_val,
                        "track_count": len(tracks),
                        "tracks": tracks
                    }
    except Exception as e:
        print(f"Erro na pesquisa de álbum MusicBrainz: {e}")

    # Fallback simples caso não encontre
    return {
        "artist": clean_artist,
        "album": clean_album or "Álbum Desconhecido",
        "release_id": None,
        "date": "",
        "year": "",
        "track_count": 0,
        "tracks": []
    }

def tag_album_flac_file(file_path: str, album_meta: Dict, track_info: Dict):
    """
    Aplica tags Vorbis completas ao ficheiro FLAC do álbum.
    """
    try:
        from mutagen.flac import FLAC
        audio = FLAC(file_path)
        audio["ARTIST"] = album_meta.get("artist", "")
        audio["ALBUM"] = album_meta.get("album", "")
        audio["TITLE"] = track_info.get("title", os.path.splitext(os.path.basename(file_path))[0])
        
        pos = track_info.get("position")
        total = album_meta.get("track_count")
        if pos:
            audio["TRACKNUMBER"] = str(pos)
            if total:
                audio["TRACKTOTAL"] = str(total)
                
        if album_meta.get("date"):
            audio["DATE"] = str(album_meta["date"])
            
        if track_info.get("id"):
            audio["MUSICBRAINZ_TRACKID"] = str(track_info["id"])
        if album_meta.get("release_id"):
            audio["MUSICBRAINZ_ALBUMID"] = str(album_meta["release_id"])
            
        audio.save()
    except Exception as e:
        print(f"Erro ao aplicar tags ao ficheiro FLAC {file_path}: {e}")

def organize_and_move_album(source_files: List[str], album_meta: Dict, tracks_info: Optional[List[Dict]] = None, dest_base: str = "/music") -> str:
    """
    Move todos os ficheiros do álbum para a biblioteca definitiva (/music/{Artista}/{Álbum}).
    Renomeia ordenadamente: {01} - {Título}.flac
    """
    artist = sanitize_name(album_meta.get("artist", "Artista Desconhecido"))
    album = sanitize_name(album_meta.get("album", "Álbum Desconhecido"))
    
    dest_dir = os.path.join(dest_base, artist, album)
    os.makedirs(dest_dir, exist_ok=True)
    
    tracks_by_pos = {t.get("position"): t for t in (tracks_info or []) if t.get("position")}
    
    for idx, src in enumerate(source_files, 1):
        if not os.path.exists(src):
            continue
            
        ext = os.path.splitext(src)[1].lower()
        base_name = os.path.splitext(os.path.basename(src))[0]
        
        m = re.match(r'^(\d+)', base_name.strip())
        track_num = int(m.group(1)) if m else idx
        
        matched_track = tracks_by_pos.get(track_num)
        if matched_track:
            title = sanitize_name(matched_track.get("title", base_name))
        else:
            clean_t = re.sub(r'^\d+[\s\-_.]*', '', base_name).strip()
            title = sanitize_name(clean_t) if clean_t else f"Faixa {track_num:02d}"
            
        final_filename = f"{track_num:02d} - {title}{ext}"
        target_path = os.path.join(dest_dir, final_filename)
        
        if ext == ".flac":
            tag_album_flac_file(src, album_meta, matched_track or {"position": track_num, "title": title})
            
        shutil.move(src, target_path)
        print(f"Álbum importado: {target_path}")
        
    for src in source_files:
        try:
            parent = os.path.dirname(src)
            if os.path.exists(parent) and not os.listdir(parent) and parent != "/downloads":
                shutil.rmtree(parent)
        except Exception:
            pass
            
    return dest_dir



