import httpx
import uuid
import asyncio
from typing import List, Dict, Optional

class SlskdClient:
    def __init__(self, url: str, api_key: str):
        # Guarantee URL doesn't have trailing slash for consistency
        self.url = url.rstrip('/')
        self.api_key = api_key
        
    def _headers(self):
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
    async def _clean_stale_searches(self, client: httpx.AsyncClient):
        """ Limpa pesquisas antigas concluídas no slskd para libertar a fila e a rede """
        try:
            res = await client.get(f"{self.url}/api/v0/searches", headers=self._headers())
            if res.status_code == 200:
                searches = res.json()
                for s in searches:
                    s_id = s.get("id")
                    state = s.get("state", "")
                    if s_id and state.startswith("Completed"):
                        await client.delete(f"{self.url}/api/v0/searches/{s_id}", headers=self._headers())
        except Exception:
            pass

    async def search(self, search_query: str, artist_filter: str, title_filter: str, timeout_seconds: int = 20) -> List[Dict]:
        """
        Inicia uma pesquisa e aguarda por resultados de forma inteligente.
        Suporta o estado 'Queued' do Soulseek e termina antecipadamente assim que
        encontra candidatos ideais com slots livres.
        """
        search_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Limpar pesquisas antigas para não sobrecarregar a fila do slskd
            await self._clean_stale_searches(client)
            
            payload = {
                "id": search_id,
                "searchText": search_query,
                "searchTimeout": 7000,
                "filterResponses": False
            }
            
            try:
                start_res = await client.post(f"{self.url}/api/v0/searches", json=payload, headers=self._headers())
                start_res.raise_for_status()
            except Exception as e:
                print(f"Erro ao iniciar pesquisa slskd: {e}")
                return []
                
            import re
            def clean_words(text):
                cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
                return [w for w in cleaned.split() if len(w) >= 2]
                
            title_words = clean_words(title_filter)
            artist_words = clean_words(artist_filter)
            
            results = []
            max_wait = 25.0
            waited = 0.0
            in_progress_time = 0.0
            
            while waited < max_wait:
                await asyncio.sleep(1.0)
                waited += 1.0
                
                try:
                    # Verificar o estado atual da pesquisa no slskd
                    s_res = await client.get(f"{self.url}/api/v0/searches/{search_id}", headers=self._headers())
                    if s_res.status_code != 200:
                        continue
                    s_data = s_res.json()
                    state = s_data.get("state", "")
                    is_complete = s_data.get("isComplete", False) or state.startswith("Completed")
                    
                    if state == "Queued":
                        # Se ainda está na fila do Soulseek, aguarda sem esgotar o tempo de pesquisa ativa
                        continue
                        
                    in_progress_time += 1.0
                    
                    # O slskd expõe a lista completa de respostas quando a pesquisa termina ou atinge o timeout
                    if is_complete or in_progress_time >= 8.0:
                        res = await client.get(f"{self.url}/api/v0/searches/{search_id}/responses", headers=self._headers())
                        if res.status_code == 200:
                            responses = res.json()
                            if responses:
                                for response in responses:
                                    username = response.get("username")
                                    hasFreeUploadSlot = response.get("hasFreeUploadSlot", False)
                                    queueLength = response.get("queueLength", 0)
                                    uploadSpeed = response.get("uploadSpeed", 0)
                                    
                                    if queueLength > 50:
                                        continue
                                        
                                    for f in response.get("files", []):
                                        filename = f.get("filename", "")
                                        fname_lower = filename.lower()
                                        fname_clean = re.sub(r'[^\w\s]', ' ', fname_lower)
                                        
                                        # Validação das palavras do título
                                        if title_words:
                                            title_matches = sum(1 for w in title_words if w in fname_clean)
                                            if title_matches < max(1, int(len(title_words) * 0.5)):
                                                continue
                                                
                                        # Validação das palavras do artista
                                        if artist_words:
                                            artist_matches = sum(1 for w in artist_words if w in fname_clean)
                                            if artist_matches == 0:
                                                continue
                                                
                                        if filename.lower().endswith((".flac", ".mp3", ".m4a", ".ogg")):
                                            results.append({
                                                "username": username,
                                                "filename": filename,
                                                "size": f.get("size", 0),
                                                "bitrate": f.get("bitRate", 0),
                                                "length": f.get("length", 0),
                                                "hasFreeUploadSlot": hasFreeUploadSlot,
                                                "queueLength": queueLength,
                                                "uploadSpeed": uploadSpeed
                                            })
                                break
                except Exception as ex:
                    print(f"Erro ao ler respostas slskd: {ex}")
                    
            # Fechar pesquisa no slskd para libertar a fila para as próximas pesquisas
            try:
                await client.delete(f"{self.url}/api/v0/searches/{search_id}", headers=self._headers())
            except Exception:
                pass
                
            return self._score_results(results, search_query)
            
    def _score_results(self, results: List[Dict], query: str) -> List[Dict]:
        """ Ordena os resultados para escolher a melhor opção (ex: dar prioridade a FLAC e estúdio) """
        query_lower = query.lower()
        is_live_query = bool(re.search(r'\b(live|concert|tour|bootleg|unplugged)\b', query_lower))

        def score(item):
            points = 0
            fname_lower = item["filename"].lower()
            
            # Penalização severa de faixas ao vivo caso a pesquisa não seja intencionalmente ao vivo
            if not is_live_query:
                live_patterns = [
                    r'\blive(\s+at|\s+in|\s+from)?\b',
                    r'\(live\)',
                    r'\[live\]',
                    r'- live\b',
                    r'\bconcert\b',
                    r'\bin\s+concert\b',
                    r'\ben\s+vivo\b',
                    r'\bbootleg\b',
                    r'\btour\b',
                    r'\bfestival\b',
                    r'\bunplugged\b',
                    r'\bsoundboard\b'
                ]
                if any(re.search(pat, fname_lower) for pat in live_patterns):
                    points -= 8000
            
            # Utilizadores com slots livres e pouca fila têm MUITA prioridade
            if item.get("hasFreeUploadSlot"):
                points += 5000
            
            # Penalizar filas: menos 100 pontos por cada pessoa na fila. Se não tem slot livre, isto dói muito.
            queue_len = item.get("queueLength", 0)
            points -= (queue_len * 100)
            
            # Dar pontos extra para malta com boa velocidade de upload
            # uploadSpeed vem em bytes/s (ex: 609096 bytes/s = ~600KB/s)
            speed_kb = item.get("uploadSpeed", 0) / 1024
            points += min(int(speed_kb / 10), 500) # Máximo de 500 pontos pela velocidade
            
            # Queremos FLAC preferencialmente, depois MP3 de qualidade
            if item["filename"].lower().endswith(".flac"):
                points += 1000
            elif item["filename"].lower().endswith(".mp3"):
                if item.get("bitrate") == 320:
                    points += 500
                else:
                    points += 200
            
            # Tamanho plausível para uma música (entre 2MB e 100MB)
            size_mb = item["size"] / (1024 * 1024)
            if 2 <= size_mb <= 100:
                points += 50
                
            return points
            
        # Ordenar pelos que têm maior pontuação
        results.sort(key=score, reverse=True)
        return results

    async def download(self, username: str, filename: str, size: int) -> bool:
        """
        Adiciona o ficheiro à fila de downloads.
        Retorna True se sucesso, False caso contrário.
        """
        payload = [
            {
                "filename": filename,
                "size": size
            }
        ]
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.url}/api/v0/transfers/downloads/{username}",
                    json=payload,
                    headers=self._headers()
                )
                res.raise_for_status()
                return True
        except Exception as e:
            print(f"Erro ao agendar download no slskd: {e}")
            return False

    async def cancel_download(self, username: str, transfer_id: str):
        try:
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"{self.url}/api/v0/transfers/downloads/{username}/{transfer_id}?remove=true",
                    headers=self._headers()
                )
        except Exception as e:
            print(f"Erro ao cancelar download rejeitado: {e}")

    async def remove_download(self, username: str, transfer_id: str):
        """ Remove permanentemente uma transferência concluída ou cancelada """
        await self.cancel_download(username, transfer_id)

    async def clear_completed_downloads(self):
        """ Limpa da interface do slskd todos os downloads terminados (sucesso, rejeitados, cancelados) """
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/api/v0/transfers/downloads", headers=self._headers())
                if res.status_code == 200:
                    for u in res.json():
                        username = u.get("username")
                        for d in u.get("directories", []):
                            for f in d.get("files", []):
                                state = f.get("state", "")
                                if state.startswith("Completed"):
                                    f_id = f.get("id")
                                    if f_id:
                                        await client.delete(
                                            f"{self.url}/api/v0/transfers/downloads/{username}/{f_id}?remove=true",
                                            headers=self._headers()
                                        )
                await client.delete(
                    f"{self.url}/api/v0/transfers/downloads/all/completed",
                    headers=self._headers()
                )
        except Exception as e:
            print(f"Erro ao limpar downloads concluídos no slskd: {e}")

    async def get_transfer_status(self, username: str, filename: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{self.url}/api/v0/transfers/downloads",
                    headers=self._headers()
                )
                if res.status_code == 200:
                    for d in res.json():
                        if d.get("username") == username:
                            for d_info in d.get("directories", []):
                                for f in d_info.get("files", []):
                                    if f.get("filename") == filename:
                                        return f
        except Exception:
            pass
        return None

    async def download_best_available(self, candidates: List[Dict]) -> Optional[Dict]:
        """
        Tenta descarregar o melhor candidato. Se o utilizador rejeitar (ex: 'File not shared', 'Completed, Rejected'),
        cancela essa tentativa e salta imediatamente para o próximo candidato da lista.
        """
        for candidate in candidates[:8]:
            username = candidate["username"]
            filename = candidate["filename"]
            size = candidate["size"]
            
            print(f"A tentar descarregar de {username}: {filename}")
            queued = await self.download(username, filename, size)
            if not queued:
                continue
                
            # Verificar durante 4 segundos se o utilizador rejeitou
            rejected = False
            for _ in range(4):
                await asyncio.sleep(1)
                status = await self.get_transfer_status(username, filename)
                if status:
                    state = status.get("state", "")
                    if state.startswith("Completed, ") and state != "Completed, Succeeded":
                        print(f"Transferência rejeitada por {username} ({state}: {status.get('exception')}). A tentar próximo candidato...")
                        transfer_id = status.get("id")
                        if transfer_id:
                            await self.cancel_download(username, transfer_id)
                        rejected = True
                        break
                    elif state in ["Requested", "Queued", "Initializing", "InProgress", "Completed, Succeeded"]:
                        return candidate
                        
            if not rejected:
                return candidate
                
        return None

    async def download_batch(self, username: str, files: List[Dict]) -> bool:
        """
        Adiciona uma lista de ficheiros à fila de download do slskd de uma só vez.
        files: [{"filename": str, "size": int}, ...]
        """
        payload = [{"filename": f["filename"], "size": f["size"]} for f in files if "filename" in f and "size" in f]
        if not payload:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{self.url}/api/v0/transfers/downloads/{username}",
                    json=payload,
                    headers=self._headers()
                )
                res.raise_for_status()
                return True
        except Exception as e:
            print(f"Erro ao agendar download de lote no slskd ({username}): {e}")
            return False

    async def search_album(self, artist: str, album: str, expected_track_count: int = 0) -> Optional[Dict]:
        """
        Pesquisa um álbum completo no Soulseek via slskd, agrupando resultados por utilizador e pasta.
        Prioriza pastas completas com ficheiros FLAC em qualidade CD 16-bit / 44.1 kHz (Red Book),
        penalizando versões Hi-Res (24-bit/96kHz), vinil ou compilações incompletas.
        """
        import re
        import os

        # Identificar se a busca é explicitamente por um álbum ao vivo
        is_official_live = bool(re.search(r'\b(live|concert|tour|bootleg|unplugged)\b', album.lower()))

        # Limpar caracteres especiais dos nomes para melhorar a pesquisa no Soulseek
        clean_artist = re.sub(r'[^\w\s]', ' ', artist).strip()
        clean_album = re.sub(r'\(.*?\)|\[.*?\]', '', album)
        if not is_official_live:
            clean_album = re.sub(r'\b(live(\s+at|\s+in|\s+from)?.*|concert|tour|bootleg)\b', '', clean_album, flags=re.IGNORECASE)
        clean_album = re.sub(r'[^\w\s]', ' ', clean_album).strip()
        
        search_query = f"{clean_artist} {clean_album} flac".strip()
        search_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._clean_stale_searches(client)
            
            payload = {
                "id": search_id,
                "searchText": search_query,
                "searchTimeout": 8000,
                "filterResponses": False
            }
            
            try:
                start_res = await client.post(f"{self.url}/api/v0/searches", json=payload, headers=self._headers())
                start_res.raise_for_status()
            except Exception as e:
                print(f"Erro ao iniciar pesquisa de álbum no slskd: {e}")
                return None

            max_wait = 25.0
            waited = 0.0
            in_progress_time = 0.0
            responses = []

            while waited < max_wait:
                await asyncio.sleep(1.0)
                waited += 1.0

                try:
                    s_res = await client.get(f"{self.url}/api/v0/searches/{search_id}", headers=self._headers())
                    if s_res.status_code != 200:
                        continue
                    s_data = s_res.json()
                    state = s_data.get("state", "")
                    is_complete = s_data.get("isComplete", False) or state.startswith("Completed")

                    if state == "Queued":
                        continue

                    in_progress_time += 1.0

                    if is_complete or in_progress_time >= 9.0:
                        res = await client.get(f"{self.url}/api/v0/searches/{search_id}/responses", headers=self._headers())
                        if res.status_code == 200:
                            responses = res.json()
                            if responses:
                                break
                except Exception as ex:
                    print(f"Erro ao obter respostas de álbum slskd: {ex}")

            # Limpar pesquisa no slskd
            try:
                await client.delete(f"{self.url}/api/v0/searches/{search_id}", headers=self._headers())
            except Exception:
                pass

            if not responses:
                return None

            # Agrupar ficheiros por (username, pasta)
            candidates_by_folder = {}

            artist_words = [w for w in re.sub(r'[^\w\s]', ' ', artist.lower()).split() if len(w) >= 2]
            album_words = [w for w in re.sub(r'[^\w\s]', ' ', album.lower()).split() if len(w) >= 2]

            for resp in responses:
                username = resp.get("username")
                hasFreeUploadSlot = resp.get("hasFreeUploadSlot", False)
                queueLength = resp.get("queueLength", 0)
                uploadSpeed = resp.get("uploadSpeed", 0)

                if queueLength > 60:
                    continue

                for f in resp.get("files", []):
                    fname = f.get("filename", "")
                    if not fname.lower().endswith(".flac"):
                        continue

                    norm_path = fname.replace('\\', '/')
                    folder_path = os.path.dirname(norm_path)
                    folder_lower = folder_path.lower()

                    # Validar se a pasta contém referências ao artista ou ao álbum
                    if artist_words and not any(w in folder_lower for w in artist_words):
                        continue
                    if album_words and not any(w in folder_lower for w in album_words):
                        continue

                    key = (username, folder_path)
                    if key not in candidates_by_folder:
                        candidates_by_folder[key] = {
                            "username": username,
                            "folder": folder_path,
                            "hasFreeUploadSlot": hasFreeUploadSlot,
                            "queueLength": queueLength,
                            "uploadSpeed": uploadSpeed,
                            "files": []
                        }

                    candidates_by_folder[key]["files"].append({
                        "filename": fname,
                        "size": f.get("size", 0),
                        "bitrate": f.get("bitRate", 0),
                        "length": f.get("length", 0)
                    })

            # Avaliar e pontuar os candidatos a álbum completo
            scored_candidates = []

            for key, cand in candidates_by_folder.items():
                flac_files = cand["files"]
                track_count = len(flac_files)
                
                # Mínimo de 3 faixas para ser considerado um álbum válido
                if track_count < 3:
                    continue

                folder_lower = cand["folder"].lower()
                
                # Rejeição estrita de versões ao vivo quando procuramos álbum de estúdio
                if not is_official_live:
                    live_patterns = [
                        r'\blive(\s+at|\s+in|\s+from)?\b',
                        r'\bconcert\b',
                        r'\bin\s+concert\b',
                        r'\ben\s+vivo\b',
                        r'\bbootleg\b',
                        r'\btour\b',
                        r'\bfestival\b',
                        r'\bunplugged\b',
                        r'\bsoundboard\b',
                        r'\(live\)',
                        r'\[live\]'
                    ]
                    # Descartar se o caminho da pasta contiver referências a concerto/ao vivo
                    if any(re.search(pat, folder_lower) for pat in live_patterns):
                        continue
                        
                    # Descartar se vários ficheiros tiverem indicação de 'live'
                    live_files_count = sum(1 for f in flac_files if any(re.search(pat, f["filename"].lower()) for pat in [r'\blive\b', r'\(live\)', r'\[live\]', r'- live\b']))
                    if live_files_count >= max(2, int(track_count * 0.3)):
                        continue

                points = 0
                
                # Bónus para indícios de versão de estúdio oficial
                if not is_official_live:
                    studio_indicators = ["studio", "original", "remastered", "deluxe edition", "album"]
                    if any(ind in folder_lower for ind in studio_indicators):
                        points += 600

                # 1. Disponibilidade do Utilizador (Slots Livres e Velocidade)
                if cand["hasFreeUploadSlot"]:
                    points += 5000
                points -= (cand["queueLength"] * 100)
                speed_kb = cand["uploadSpeed"] / 1024
                points += min(int(speed_kb / 10), 600)

                # 2. Correspondência com o Número de Faixas Esperadas do MusicBrainz
                if expected_track_count > 0:
                    if track_count == expected_track_count:
                        points += 4500
                    elif abs(track_count - expected_track_count) <= 1:
                        points += 3000
                    elif track_count >= int(expected_track_count * 0.8):
                        points += 1500
                    elif track_count < int(expected_track_count * 0.5):
                        points -= 2000
                else:
                    if track_count >= 8:
                        points += 2000
                    elif track_count >= 5:
                        points += 1000

                # 3. Qualidade CD FLAC 16-bit / 44.1 kHz (Red Book)
                # Bónus para indícios positivos de 16/44 ou CD oficial
                cd_indicators = ["16-44", "16/44", "16 44", "16bit", "44.1", "44100", "cd", "redbook", "eac", "cue", "log"]
                if any(ind in folder_lower for ind in cd_indicators):
                    points += 3000

                # Penalização forte para Hi-Res (24/96, 24/192) ou vinil (não é 16/44.1 CD standard)
                hi_res_indicators = ["24-96", "24/96", "24-192", "24/192", "24-88", "24/88", "24bit", "hi-res", "hires", "sacd", "vinyl", "lp", "cassette", "tape"]
                if any(ind in folder_lower for ind in hi_res_indicators):
                    points -= 3500

                # 4. Verificação de Bitrate Médio
                valid_bitrates = [f["bitrate"] for f in flac_files if f.get("bitrate", 0) > 0]
                if valid_bitrates:
                    avg_bitrate = sum(valid_bitrates) / len(valid_bitrates)
                    # Bitrate típico de FLAC 16/44.1: entre 650 kbps e 1100 kbps
                    if 650 <= avg_bitrate <= 1150:
                        points += 2000
                    elif avg_bitrate > 1800:
                        # Taxa de bits muito elevada indica ficheiro 24-bit Hi-Res
                        points -= 2500

                cand["score"] = points
                cand["total_tracks"] = track_count
                scored_candidates.append(cand)

            if not scored_candidates:
                return None

            # Ordenar pelo maior score
            scored_candidates.sort(key=lambda x: x["score"], reverse=True)
            best = scored_candidates[0]
            print(f"Melhor candidato de álbum encontrado: {best['username']} ({best['total_tracks']} faixas, pontuação {best['score']}) -> {best['folder']}")
            return best


