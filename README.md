# brazbot.py v2.0.0 🇧🇷

**brazbot.py** é uma biblioteca brasileira nativa, assíncrona e pronta para produção para criação de bots no Discord em Python — construída **diretamente sobre a API HTTP/REST v10, Gateway v10 e Voice Gateway v8 do Discord**, sem depender de nenhuma outra biblioteca de bots.

---

## ✨ Principais Novidades da v2.0.0

- **100% Nativa na API v10 do Discord & Voice Gateway v8 (`?v=8`)**:
  - Suporte completo a `RESUME` (Opcode 6), `RECONNECT` (Opcode 7), `INVALID_SESSION` (Opcode 9), `HEARTBEAT` com *jitter* e cálculo de latência (`bot.latency`), e compressão `zlib-stream`.
  - Cabeçalho `User-Agent: DiscordBot (https://github.com/BosonsHiggs/brazbot.py, 2.0.0)` e **Rate Limiting Preventivo por Bucket (`X-RateLimit-Bucket` + Major Parameters `guild_id`/`channel_id`/`webhook_id`)** em total conformidade com as diretrizes oficiais da comunidade Discord API (`meew0`).
- **Voz e Música Totalmente Reescritas (`VoiceClient` + `yt-dlp`)**:
  - **Criptografia de Transporte AEAD Moderna**: Suporte nativo a `aead_aes256_gcm_rtpsize` (via `cryptography`) e `aead_xchacha20_poly1305_rtpsize` (via `PyNaCl`), substituindo o antigo modo `xsalsa20_poly1305` descontinuado pelo Discord.
  - **IP Discovery de 74 bytes** conforme especificação oficial do protocolo UDP do Discord.
  - **Codificador e Decodificador Opus Nativo (`ctypes` `libopus`) + Demuxer Ogg/Opus Puro**: Transmite quadros Opus reais (48kHz, estéreo, 20ms) com envio automático dos 5 quadros de silêncio (`0xF8, 0xFF, 0xFE`) e recepção/descriptografia de pacotes UDP para *bridges* de voz entre servidores (`example_phone_call.py`).
  - **Motor de Música Integrado (`brazbot.music`)**: Extração assíncrona com `yt-dlp` (YouTube, Playlists, SoundCloud, busca por nome e links diretos), controle real de volume em PCM 16-bit (0% a 200%), `/seek` (avançar/retroceder para um segundo específico) e filtros de áudio FFmpeg em tempo real (`bassboost`, `nightcore`, `vaporwave`, `8d`, `treble`, `karaoke`, `echo`).
- **Novos Recursos da API v10 & Cogs Prontas para Criação de Bots**:
  - **Cogs Nativas Embutidas (`brazbot.cogs_builtin`)**: `MusicCog`, `ModerationCog`, `UtilityCog` e `FunCog` prontas para adicionar com `bot.add_cog(...)`.
  - **Enquetes Nativas (`Poll`)**, **AutoModeração (`AutoModRule`)**, **Soundboard (`Soundboard`)**, **Eventos Agendados (`ScheduledEvent`)**, **Status de Canal de Voz (`VoiceChannel.set_voice_status`)** e **Bulk Ban (`Guild.bulk_ban`)**.
  - **Todos os Menus de Seleção da API v10**: `Dropdown` (`StringSelect`), `UserSelect`, `RoleSelect`, `MentionableSelect`, `ChannelSelect`, além de `Button`, `ActionRow`, `View` e `Form` (Modals).
  - **CLI Integrada (`brazbot`)**: `brazbot init meu_bot`, `brazbot doctor` e `brazbot version`.

---

## 📦 Instalação (Modo Produção)

Certifique-se de utilizar **Python 3.10+** (recomendado Python 3.11+) e o `ffmpeg` instalado no sistema para recursos de voz:

```bash
# Instalação direta do pacote local ou via Git
pip install -U .

# Ou instalando forçando as últimas versões de todos os pacotes (2026):
pip install -U ".[latest]"
```

Para verificar se todas as dependências (`aiohttp`, `PyNaCl`, `cryptography`, `yt-dlp`, `ffmpeg`, `libopus`) estão prontas no seu servidor de produção:

```bash
brazbot doctor
```

---

## 🚀 Criando um Bot Completo em Minutos

Você pode gerar um projeto limpo automaticamente pelo terminal:

```bash
brazbot init meu_bot
```

Ou criar seu arquivo `bot.py`:

```python
import os
from brazbot import Bot, Embed, FunCog, ModerationCog, MusicCog, UtilityCog

intents = ["GUILDS", "GUILD_VOICE_STATES", "GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_MEMBERS"]

class MeuBot(Bot):
    async def setup_hook(self):
        # Ativa mais de 25 comandos prontos de Música, Moderação, Utilidades e Diversão!
        self.add_cog(MusicCog(self))
        self.add_cog(ModerationCog(self))
        self.add_cog(UtilityCog(self))
        self.add_cog(FunCog(self))

    async def on_ready(self, data):
        print(f"Conectado como {data['user']['username']} (App ID: {self.application_id})")
        await self.command_handler.sync_commands(guild_id=os.getenv("DISCORD_GUILD_ID"))

bot = MeuBot(token=os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=intents)

@bot.command(name="ola", description="Envia uma saudação personalizada")
async def ola(ctx):
    await ctx.reply(
        embed=Embed(
            title="Olá! 👋",
            description=f"Bem-vindo(a), {ctx.author.mention}!",
            color=Embed.Color.GREEN,
        )
    )

if __name__ == "__main__":
    bot.run()
```

---

## 🗂️ Estrutura Limpa da Biblioteca

```text
brazbot/
├── __init__.py             # Exportações públicas unificadas da biblioteca
├── bot.py                  # Cliente Gateway v10 (DiscordBot / Bot), RESUME e Voice States
├── bot_itimized.py         # Variante com compressão zlib-stream habilitada por padrão
├── http.py                 # Cliente REST v10 com Rate Limiting preventivo por Bucket e Global
├── voiceclient.py          # Voice Gateway v8, UDP IP Discovery (74B), AEAD RTP e Opus (ctypes/Ogg)
├── music.py                # Motor de música assíncrono (yt-dlp, GuildMusicPlayer, filtros FFmpeg, seek)
├── commands.py             # CommandContext híbrido (Prefix + Slash + Context Menus + Autocomplete)
├── decorators.py           # Decoradores (@has_permissions, @in_voice_channel, @rate_limit, @tasks, etc.)
├── cogs.py                 # Classe base modular Cog
├── cogs_builtin.py         # Cogs prontas: MusicCog, ModerationCog, UtilityCog, FunCog
├── subgroups.py            # SubCommandGroup para comandos aninhados (SUB_COMMAND / SUB_COMMAND_GROUP)
├── channels.py             # Channel, TextChannel, VoiceChannel, StageChannel, Category, Forum, Media, DM
├── guilds.py               # Guild (membros, cargos, bans, bulk_ban, automod, templates, webhooks)
├── member.py               # Member e VoiceState (timeout, untimeout, roles, DM, voice.channel)
├── roles.py                # Role (criação, edição, atribuição e cálculo de permissões)
├── threads.py              # Thread (arquivamento, tags de fórum, membros)
├── message_handler.py      # Envio/edição de mensagens, interações, follow-ups, modais e reações
├── messages.py             # Message e PartialMessage
├── embed.py                # Construtor fluente Embed e paleta EmbedColor
├── buttons.py              # Button, ButtonStyle, ActionRow e View com callbacks
├── dropdowns.py            # Dropdown (StringSelect), UserSelect, RoleSelect, MentionableSelect, ChannelSelect
├── forms.py                # Form e FormField (Modals da API v10)
├── polls.py                # Enquetes nativas da API v10 (Poll, PollAnswer, PollMedia)
├── automod.py              # Regras de AutoModeração da API v10 (AutoModRule)
├── soundboard.py           # Efeitos sonoros do Soundboard da API v10 (Soundboard, SoundboardSound)
├── scheduled_events.py     # Eventos agendados do servidor (ScheduledEvent)
├── webhooks.py             # Gerenciamento e execução de Webhooks
├── permissions.py          # Bitfields completos de Permissions e Intents da API v10
├── audit_log_entry.py      # AuditLogEntry
├── eventstype.py           # Enum EventTypes de auditoria da API v10
├── errors.py               # Hierarquia completa de exceções (BrazbotError, HTTPException, etc.)
├── cache.py                # Cache em memória com expiração TTL
├── snowflake.py            # Utilitários de Snowflake (64 bits)
├── utils.py                # Funções auxiliares de embeds, paginação e timestamps
└── cli.py                  # Interface de linha de comando (`brazbot init`, `brazbot doctor`, `brazbot version`)
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
