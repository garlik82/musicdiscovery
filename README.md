# 🎵 PlexDiscover

> **Autonomous Musical Discovery & Progressive Buffer Engine for Plex & Plexamp**

PlexDiscover transforma as tuas sessões de audição no **Plexamp** numa experiência contínua e inteligente de descoberta musical. 

Enquanto ouves os teus álbuns favoritos, o PlexDiscover analisa os teus gostos, pesquisa artistas semelhantes via **Last.fm**, automatiza a obtenção de faixas em alta fidelidade via **Soulseek (slskd)**, enriquece-as com metadados canónicos do **MusicBrainz**, isola-as numa biblioteca temporária para não poluir a tua coleção definitiva e **injeta-as de forma progressiva diretamente na PlayQueue ativa do teu Plexamp** antes que a música termine.

---

## ✨ Funcionalidades Principais

* 🚀 **Auto-Pilot Inteligente:** Deteta automaticamente quando inicias um álbum no Plexamp e ativa a recolha de artistas recomendados.
* ⚡ **Buffer Progressivo (Lazy Loading):** Monitoriza a fila de reprodução ativa em tempo real. Quando restam apenas $N$ faixas (ex: limiar de 2 ou 3 músicas), descarrega e injeta o próximo lote de 5 músicas sem sobrecarregar a fila nem a rede.
* 🛡️ **Proteção Total da Biblioteca Permanente:** A tua coleção principal (`/music`) nunca é alterada. As descobertas são gravadas num volume isolado (`/music_discovery`), com uma biblioteca dedicada no Plex (*Music Discovery*).
* 🏷️ **Etiquetagem Oficial MusicBrainz:** Todos os ficheiros transferidos são validados (integridade áudio e duração) e recebem tags ID3/FLAC oficiais antes de serem indexados pelo Plex.
* 🔍 **Integração Soulseek (slskd) Robusta:** Pesquisa automática, seleção da melhor qualidade disponível (FLAC/MP3 320kbps), reconciliação direta com o sistema de ficheiros e recuperação de downloads pendentes.
* ⭐ **Promoção & Álbuns Favoritos:**
  * **Download Automático de Álbum Completo (FLAC 16-bit / 44.1 kHz):** Quando marcas uma música como favorita (⭐ ou ❤️) no Plexamp ou via Webhook do Plex, o PlexDiscover pesquisa e descarrega o álbum de estúdio completo em qualidade CD Red Book diretamente para a tua biblioteca definitiva (`/music`), aplicando metadados oficiais do MusicBrainz.
  * **Promover Artista:** Move com um clique os ficheiros da biblioteca de descoberta para a tua coleção definitiva.
  * **Lista Negra:** Ignora artistas que não queiras voltar a ouvir.
* 🧹 **Limpeza Automática & Manual:**
  * **Auto-Cleanup (1 hora):** Se a reprodução parar e passarem 60 minutos de inatividade, remove automaticamente as faixas temporárias e purga a biblioteca do Plex.
  * **Botão de Limpeza Manual:** Disponível no separador de Definições para limpar a biblioteca de descoberta e registos a qualquer momento.
* 💻 **Interface Moderna (Vue 3):** Dashboard em tempo real com estado do reprodutor, fila de descoberta, gestão de transferências de álbuns FLAC, pesquisa manual e painel de definições.

---

## 🏗️ Arquitetura do Sistema

```
  ┌──────────────┐          ┌────────────────┐          ┌───────────────┐
  │   Plexamp    │ ◄─────── │  Plex Server   │ ◄─────── │ PlexDiscover  │
  │ (Reprodução) │          │ (PlayQueue/Lib)│          │   (Backend)   │
  └──────────────┘          └────────────────┘          └───────┬───────┘
                                                                │
                     ┌──────────────────┬───────────────────────┼──────────────────┐
                     ▼                  ▼                       ▼                  ▼
              ┌─────────────┐    ┌─────────────┐         ┌─────────────┐    ┌─────────────┐
              │   Last.fm   │    │    slskd    │         │ MusicBrainz │    │ Disco Local │
              │(Semelhantes)│    │ (Soulseek)  │         │(Metadados)  │    │(/discovery) │
              └─────────────┘    └─────────────┘         └─────────────┘    └─────────────┘
```

---

## 📋 Pré-requisitos

1. **Plex Media Server** com a aplicação **Plexamp** instalada nos teus dispositivos.
2. Instância do **[slskd](https://github.com/slskd/slskd)** a correr e acessível na rede local.
3. Chave de API gratuita do **Last.fm** ([Criar conta de API no Last.fm](https://www.last.fm/api/account/create)).
4. **Docker** e **Docker Compose** instalados na máquina/NAS.

---

## 🚀 Instalação e Configuração

### 1. Clonar o Repositório

```bash
git clone https://github.com/garlik82/musicdiscovery.git
cd musicdiscovery
```

### 2. Configurar Variáveis de Ambiente

Copia o ficheiro de exemplo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edita o `.env` com os teus detalhes:

```env
# Plex
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=o_teu_plex_token

# Last.fm
LASTFM_API_KEY=a_tua_api_key_lastfm
LASTFM_USERNAME=o_teu_username_lastfm

# slskd
SLSKD_URL=http://192.168.1.100:5030
SLSKD_API_KEY=a_tua_api_key_slskd

# Pastas de Armazenamento no Host
DOWNLOADS_PATH=/volume1/Media/Downloads/complete
MUSIC_PATH=/volume1/Media/Music
DISCOVERY_PATH=/volume1/Media/Misc/MusicDiscovery
```

> 💡 **Nota sobre as Bibliotecas no Plex:**
> - Cria uma biblioteca do tipo Música no Plex chamada **Music Discovery** apontando para a pasta configurada em `DISCOVERY_PATH`.
> - A tua biblioteca de música principal deve chamar-se **Music** e apontar para `MUSIC_PATH`.

### 3. Iniciar com Docker Compose

```bash
docker compose up -d --build
```

A aplicação ficará disponível em:
- **Interface Web:** `http://<IP_DO_HOST>:8789`
- **API Backend:** `http://<IP_DO_HOST>:8788`

---

## ⚙️ Definições & Personalização

Todas as configurações podem ser ajustadas em tempo real na interface web no separador **⚙️ Definições**:

| Parâmetro | Descrição | Valor Padrão |
| :--- | :--- | :--- |
| **Estratégia de Descoberta** | `Progressivo (Buffer)` ou `Fixo (Lote Único)` | Progressivo |
| **Tamanho do Lote** | Número de músicas a descarregar por lote | `5` músicas |
| **Limiar do Buffer** | Dispara novo lote quando faltam $\le N$ músicas na fila | `2` músicas |
| **Limite por Sessão** | Máximo de músicas a descarregar por álbum ($0$ = sem limite) | `20` músicas |
| **Modo de Recomendação** | `Contextual` (apenas baseado no álbum atual) ou `Híbrido` (mistura álbum + histórico Last.fm) | Contextual |
| **Faixas por Artista** | Quantidade de faixas sugeridas de cada banda similar | `1` faixa |

---

## 🔒 Segurança e Privacidade

- As credenciais (tokens Plex, chaves Last.fm e slskd) são guardadas exclusivamente no volume local persistente (`./data/settings.json`) ou nas variáveis de ambiente (`.env`).
- O ficheiro `.gitignore` vem pré-configurado para ignorar ficheiros sensíveis, dados temporários e ficheiros áudio.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulta o ficheiro `LICENSE` para mais informações.

