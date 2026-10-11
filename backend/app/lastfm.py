import httpx
import os
from typing import List, Dict, Any

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

class LastFMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def get_similar_artists(self, artist: str, limit: int = 5) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            params = {
                "method": "artist.getsimilar",
                "artist": artist,
                "api_key": self.api_key,
                "format": "json",
                "limit": limit
            }
            response = await client.get(LASTFM_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            artists = []
            if "similarartists" in data and "artist" in data["similarartists"]:
                artist_list = data["similarartists"]["artist"]
                # A API às vezes devolve um dicionário em vez de lista se for só 1
                if isinstance(artist_list, dict):
                    artist_list = [artist_list]
                    
                for a in artist_list:
                    artists.append({
                        "name": a.get("name"),
                        "match": float(a.get("match", 0))
                    })
            return artists

    async def get_top_tracks(self, artist: str, limit: int = 2) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            params = {
                "method": "artist.gettoptracks",
                "artist": artist,
                "api_key": self.api_key,
                "format": "json",
                "limit": limit
            }
            response = await client.get(LASTFM_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            tracks = []
            if "toptracks" in data and "track" in data["toptracks"]:
                track_list = data["toptracks"]["track"]
                if isinstance(track_list, dict):
                    track_list = [track_list]
                    
                for t in track_list:
                    tracks.append({
                        "title": t.get("name"),
                        "artist": artist,
                        "playcount": int(t.get("playcount", 0))
                    })
            return tracks

    async def get_recent_artists(self, username: str, limit: int = 20) -> List[Dict]:
        """
        Obtém as bandas mais recentemente ouvidas pelo utilizador no Last.fm.
        """
        if not username:
            return []
            
        async with httpx.AsyncClient() as client:
            params = {
                "method": "user.getrecenttracks",
                "user": username,
                "api_key": self.api_key,
                "format": "json",
                "limit": limit
            }
            try:
                response = await client.get(LASTFM_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                recent_tracks = []
                if "recenttracks" in data and "track" in data["recenttracks"]:
                    t_list = data["recenttracks"]["track"]
                    if isinstance(t_list, dict):
                        t_list = [t_list]
                    for t in t_list:
                        artist_obj = t.get("artist", {})
                        a_name = artist_obj.get("#text") if isinstance(artist_obj, dict) else str(artist_obj)
                        if a_name and a_name.strip():
                            recent_tracks.append(a_name.strip())
                            
                # Manter ordem mas eliminar duplicados consecutivos
                unique_artists = []
                seen = set()
                for a in recent_tracks:
                    clean = a.lower()
                    if clean not in seen:
                        seen.add(clean)
                        unique_artists.append(a)
                return unique_artists
            except Exception as e:
                print(f"Erro ao obter recent tracks do Last.fm: {e}")
                return []

