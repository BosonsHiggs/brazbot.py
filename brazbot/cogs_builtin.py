"""
Coleção de Cogs prontas para uso na criação de bots com a biblioteca brazbot.py:
- `MusicCog`: Comandos completos de música e voz (`/join`, `/leave`, `/play`, `/search`, `/pause`, `/resume`,
  `/skip`, `/stop`, `/queue`, `/nowplaying`, `/loop`, `/volume`, `/shuffle`, `/remove`, `/move`, `/seek`, `/filter`, `/voice_status`)
- `ModerationCog`: Comandos de moderação (`/ban`, `/unban`, `/kick`, `/timeout`, `/untimeout`, `/clear`, `/slowmode`,
  `/lock`, `/unlock`, `/nick`, `/addrole`, `/removerole`, `/automod_keywords`)
- `UtilityCog`: Comandos de utilidades e servidor (`/ping`, `/serverinfo`, `/userinfo`, `/avatar`, `/roleinfo`,
  `/channelinfo`, `/poll`, `/endpoll`, `/embed`, `/botinfo`)
- `FunCog`: Comandos de diversão e engajamento (`/8ball`, `/dice`, `/coinflip`, `/choose`, `/rps`)
"""

import random
import time
from datetime import datetime, timezone
from typing import Literal, Optional

from brazbot.buttons import Button, ButtonStyle
from brazbot.channels import Channel, TextChannel, VoiceChannel
from brazbot.cogs import Cog
from brazbot.decorators import describe, guild_only, has_permissions, in_voice_channel, rate_limit
from brazbot.embed import Embed
from brazbot.member import Member
from brazbot.music import AUDIO_FILTERS
from brazbot.polls import Poll
from brazbot.roles import Role
from brazbot.utils import create_error_embed, format_discord_timestamp


class MusicCog(Cog):
    """Cog pronta de Música e Voz com suporte a YouTube (`yt-dlp`), filtros FFmpeg, seek e fila."""

    def __init__(self, bot):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="join", description="Conecta o bot a um canal de voz")
        @describe(channel="Canal de voz para conectar (opcional se você já estiver em um)")
        async def join(ctx, channel: Optional[VoiceChannel] = None):
            await ctx.defer()
            target_channel = channel or (
                ctx.author.voice.channel if ctx.author and ctx.author.voice else None
            )
            if not target_channel:
                await ctx.send(embed=create_error_embed("Você precisa estar em um canal de voz ou informar um canal!"))
                return
            vc = await target_channel.connect()
            embed = Embed(
                title="🔊 Conectado ao Canal de Voz",
                description=f"Conectado com sucesso a **{target_channel.name}**",
                color=Embed.Color.GREEN,
            ).add_field("Modo de Criptografia", f"`{vc.udp.mode}`", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="leave", description="Desconecta o bot do canal de voz e limpa a fila")
        async def leave(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc:
                await ctx.send(embed=create_error_embed("O bot não está conectado a nenhum canal de voz."))
                return
            ch_name = vc.channel.name
            player = self.bot.get_music_player(ctx.guild_id)
            player.queue.clear()
            player.current = None
            await vc.disconnect()
            await ctx.send(
                embed=Embed(
                    title="👋 Desconectado",
                    description=f"Saí do canal **{ch_name}**.",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="play", aliases=["p"], description="Toca música a partir de uma URL ou pesquisa no YouTube")
        @describe(query="Nome da música, URL do YouTube, Playlist ou link direto MP3/OGG")
        async def play(ctx, query: str):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_connected():
                if ctx.author and ctx.author.voice and ctx.author.voice.channel:
                    vc = await ctx.author.voice.channel.connect()
                else:
                    await ctx.send(embed=create_error_embed("Entre em um canal de voz primeiro ou use `/join`!"))
                    return

            player = self.bot.get_music_player(ctx.guild_id)
            player.text_channel_id = ctx.channel_id
            requester = str(ctx.author) if ctx.author else "Desconhecido"

            tracks = await player.enqueue(query, requester=requester)
            if not tracks:
                await ctx.send(embed=create_error_embed("Nenhuma faixa encontrada para a sua busca."))
                return

            first = tracks[0]
            desc = (
                f"**[{first.title}]({first.url})**"
                if len(tracks) == 1
                else f"Adicionadas **{len(tracks)} faixas** da playlist à fila!"
            )
            embed = (
                Embed(title="🎵 Adicionado à Fila", description=desc, color=Embed.Color.GREEN)
                .add_field("Duração", first.formatted_duration, inline=True)
                .add_field("Pedido por", requester, inline=True)
                .set_footer(f"Total na fila: {len(player.queue)} faixa(s)")
            )
            if first.thumbnail:
                embed.set_thumbnail(first.thumbnail)
            await ctx.send(embed=embed)

        @self.command(name="pause", description="Pausa a música atual")
        async def pause(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_playing():
                await ctx.send(embed=create_error_embed("Não há nenhuma música tocando no momento."))
                return
            await vc.pause()
            await ctx.send(embed=Embed(title="⏸️ Pausado", description="Reprodução pausada.", color=Embed.Color.GOLD))

        @self.command(name="resume", description="Retoma a música pausada")
        async def resume(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_paused():
                await ctx.send(embed=create_error_embed("A reprodução não está pausada."))
                return
            await vc.resume()
            await ctx.send(embed=Embed(title="▶️ Retomado", description="Reprodução retomada!", color=Embed.Color.GREEN))

        @self.command(name="skip", aliases=["s"], description="Pula para a próxima música da fila")
        async def skip(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            player = self.bot.get_music_player(ctx.guild_id)
            if not vc or not player.current:
                await ctx.send(embed=create_error_embed("Não há nada tocando para pular."))
                return
            skipped_title = player.current.title
            vc._after_callback = None
            await vc.stop()
            await player.play_next()
            await ctx.send(
                embed=Embed(
                    title="⏭️ Música Pulada",
                    description=f"Pulou **{skipped_title}**.",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="stop", description="Para a reprodução e limpa a fila de músicas")
        async def stop(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            player = self.bot.get_music_player(ctx.guild_id)
            player.queue.clear()
            player.current = None
            if vc:
                await vc.stop()
            await ctx.send(
                embed=Embed(
                    title="⏹️ Parado",
                    description="A reprodução foi interrompida e a fila foi limpa.",
                    color=Embed.Color.RED,
                )
            )

        @self.command(name="queue", aliases=["q"], description="Exibe a fila de reprodução atual")
        async def queue(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            if not player.current and not player.queue:
                await ctx.send("📭 A fila de reprodução está vazia.")
                return
            embed = Embed(title="🎶 Fila de Música", color=Embed.Color.BLURPLE)
            if player.current:
                embed.add_field(
                    "▶️ Tocando Agora",
                    f"**[{player.current.title}]({player.current.url})** (`{player.current.formatted_duration}`)\n"
                    f"{player.current.progress_bar()}\nPedido por: {player.current.requester}",
                    inline=False,
                )
            if player.queue:
                lines = [
                    f"`{idx}.` **{t.title}** (`{t.formatted_duration}`) — {t.requester}"
                    for idx, t in enumerate(player.queue[:10], 1)
                ]
                if len(player.queue) > 10:
                    lines.append(f"... e mais **{len(player.queue) - 10}** faixa(s)")
                embed.add_field(f"📋 Próximas ({len(player.queue)})", "\n".join(lines), inline=False)
            embed.set_footer(f"Loop: {player.loop_mode} | Volume: {int(player.volume * 100)}% | Filtro: {player.audio_filter}")
            await ctx.send(embed=embed)

        @self.command(name="nowplaying", aliases=["np"], description="Mostra detalhes e barra de progresso da música atual")
        async def nowplaying(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            curr = player.current
            if not curr:
                await ctx.send(embed=create_error_embed("Nenhuma música está sendo reproduzida agora."))
                return
            embed = (
                Embed(
                    title="🎵 Tocando Agora",
                    description=f"**[{curr.title}]({curr.url})**\n\n{curr.progress_bar()}",
                    color=Embed.Color.GREEN,
                )
                .add_field("Pedido por", curr.requester, inline=True)
                .add_field("Canal/Autor", curr.uploader or "Desconhecido", inline=True)
                .add_field("Filtro", f"`{player.audio_filter}`", inline=True)
            )
            if curr.thumbnail:
                embed.set_thumbnail(curr.thumbnail)
            await ctx.send(embed=embed)

        @self.command(name="volume", description="Ajusta o volume do player (0 a 200%)")
        @describe(level="Nível de volume entre 0 e 200")
        async def volume(ctx, level: int):
            await ctx.defer()
            if not (0 <= level <= 200):
                await ctx.send(embed=create_error_embed("O volume deve estar entre 0 e 200%."))
                return
            player = self.bot.get_music_player(ctx.guild_id)
            player.set_volume(level / 100.0)
            filled = int((level / 200.0) * 20)
            bar = "█" * filled + "░" * (20 - filled)
            await ctx.send(
                embed=Embed(
                    title="🔊 Volume Ajustado",
                    description=f"`{bar}` **{level}%**",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="seek", description="Avança ou retrocede para um segundo específico da faixa atual")
        @describe(seconds="Posição em segundos para onde pular")
        async def seek(ctx, seconds: int):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            ok = await player.seek(seconds)
            if not ok:
                await ctx.send(embed=create_error_embed("Não foi possível reposicionar a faixa atual."))
                return
            m, s = divmod(max(0, int(seconds)), 60)
            await ctx.send(
                embed=Embed(
                    title="⏩ Posição Alterada",
                    description=f"Faixa reposicionada para `{m}:{s:02d}`.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="filter", description="Aplica um filtro de efeito sonoro FFmpeg em tempo real")
        @describe(effect="Filtro: off, bassboost, nightcore, vaporwave, 8d, treble, karaoke, echo")
        async def filter_cmd(
            ctx,
            effect: Literal[
                "off", "bassboost", "nightcore", "vaporwave", "8d", "treble", "karaoke", "echo"
            ],
        ):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            await player.set_filter(effect)
            await ctx.send(
                embed=Embed(
                    title="🎛️ Filtro de Áudio",
                    description=f"Filtro definido para **`{effect}`**.",
                    color=Embed.Color.BLURPLE,
                )
            )

        @self.command(name="loop", description="Altera o modo de repetição (off, track, queue)")
        @describe(mode="Modo de repetição: off, track ou queue")
        async def loop_cmd(ctx, mode: Literal["off", "track", "queue"]):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            player.loop_mode = mode
            await ctx.send(
                embed=Embed(
                    title="🔁 Modo de Loop",
                    description=f"Modo de repetição alterado para **`{mode}`**.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="shuffle", description="Embaralha as músicas na fila")
        async def shuffle_cmd(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            count = player.shuffle()
            await ctx.send(
                embed=Embed(
                    title="🔀 Fila Embaralhada",
                    description=f"**{count}** faixas foram embaralhadas.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="voice_status", description="Define o status personalizado do canal de voz atual")
        @describe(status="Texto de status para o canal de voz")
        async def voice_status_cmd(ctx, status: str):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc:
                await ctx.send(embed=create_error_embed("O bot precisa estar em um canal de voz!"))
                return
            await vc.channel.set_voice_status(status)
            await ctx.send(
                embed=Embed(
                    title="💬 Status do Canal de Voz Atualizado",
                    description=f"Novo status: **{status}**",
                    color=Embed.Color.GREEN,
                )
            )


class ModerationCog(Cog):
    """Cog completa de Moderação e Administração de Servidores (API v10)."""

    def __init__(self, bot):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="ban", description="Bane um membro do servidor")
        @has_permissions(ban_members=True)
        @describe(member="Membro a ser banido", reason="Motivo do banimento")
        async def ban_cmd(ctx, member: Member, reason: Optional[str] = None):
            await ctx.defer()
            await member.ban(reason=reason)
            embed = (
                Embed(
                    title="🔨 Membro Banido",
                    description=f"**{member}** (`{member.id}`) foi banido do servidor.",
                    color=Embed.Color.RED,
                )
                .add_field("Moderador", str(ctx.author), inline=True)
                .add_field("Motivo", reason or "Não especificado", inline=True)
                .set_timestamp()
            )
            await ctx.send(embed=embed)

        @self.command(name="unban", description="Remove o banimento de um usuário pelo ID")
        @has_permissions(ban_members=True)
        @describe(user_id="ID do usuário a ser desbanido", reason="Motivo")
        async def unban_cmd(ctx, user_id: str, reason: Optional[str] = None):
            await ctx.defer()
            guild = await ctx.get_guild()
            await guild.unban(user_id, reason=reason)
            await ctx.send(
                embed=Embed(
                    title="🔓 Usuário Desbanido",
                    description=f"O usuário `{user_id}` foi desbanido.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="kick", description="Expulsa um membro do servidor")
        @has_permissions(kick_members=True)
        @describe(member="Membro a ser expulso", reason="Motivo da expulsão")
        async def kick_cmd(ctx, member: Member, reason: Optional[str] = None):
            await ctx.defer()
            await member.kick(reason=reason)
            await ctx.send(
                embed=Embed(
                    title="👢 Membro Expulso",
                    description=f"**{member}** foi expulso. Motivo: {reason or 'Não informado'}",
                    color=Embed.Color.ORANGE,
                )
            )

        @self.command(name="timeout", description="Aplica castigo temporário (mute/timeout) em um membro")
        @has_permissions(moderate_members=True)
        @describe(member="Membro alvo", minutes="Duração em minutos (0 para remover)", reason="Motivo")
        async def timeout_cmd(ctx, member: Member, minutes: int, reason: Optional[str] = None):
            await ctx.defer()
            await member.timeout(minutes * 60 if minutes > 0 else None, reason=reason)
            if minutes > 0:
                await ctx.send(
                    embed=Embed(
                        title="🔇 Membro em Timeout",
                        description=f"**{member}** recebeu timeout por **{minutes} minuto(s)**.\nMotivo: {reason or 'Não informado'}",
                        color=Embed.Color.ORANGE,
                    )
                )
            else:
                await ctx.send(
                    embed=Embed(
                        title="🔊 Timeout Removido",
                        description=f"O timeout de **{member}** foi removido.",
                        color=Embed.Color.GREEN,
                    )
                )

        @self.command(name="purge", description="Limpa uma quantidade de mensagens no canal atual")
        @has_permissions(manage_messages=True)
        @describe(amount="Quantidade de mensagens para apagar (1 a 100)")
        async def purge_cmd(ctx, amount: int):
            await ctx.defer(ephemeral=True)
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            deleted = await ch.purge(limit=min(100, max(1, int(amount))))
            await ctx.send(f"🗑️ **{len(deleted)}** mensagens foram apagadas.", ephemeral=True)

        @self.command(name="slowmode", description="Define o tempo de modo lento (slowmode) do canal")
        @has_permissions(manage_channels=True)
        @describe(seconds="Segundos entre mensagens (0 para desativar)")
        async def slowmode_cmd(ctx, seconds: int):
            await ctx.defer()
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            await ch.set_slowmode(seconds)
            await ctx.send(
                embed=Embed(
                    title="⏱️ Slowmode Atualizado",
                    description=f"Modo lento definido para **{seconds}s** neste canal.",
                    color=Embed.Color.BLURPLE,
                )
            )

        @self.command(name="lock", description="Tranca o canal atual para envio de mensagens")
        @has_permissions(manage_channels=True)
        async def lock_cmd(ctx):
            await ctx.defer()
            ch = await ctx.get_channel()
            await ch.set_lock(True, reason=f"Locked by {ctx.author}")
            await ctx.send(
                embed=Embed(
                    title="🔒 Canal Trancado",
                    description="Este canal foi trancado para membros comuns.",
                    color=Embed.Color.RED,
                )
            )

        @self.command(name="unlock", description="Destranca o canal atual")
        @has_permissions(manage_channels=True)
        async def unlock_cmd(ctx):
            await ctx.defer()
            ch = await ctx.get_channel()
            await ch.set_lock(False, reason=f"Unlocked by {ctx.author}")
            await ctx.send(
                embed=Embed(
                    title="🔓 Canal Destrancado",
                    description="Este canal foi destrancado.",
                    color=Embed.Color.GREEN,
                )
            )


class UtilityCog(Cog):
    """Cog de Utilidades, Informações e Enquetes Nativas da API v10."""

    def __init__(self, bot):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="ping", description="Mostra a latência atual do bot com o Gateway do Discord")
        async def ping_cmd(ctx):
            ms = round(self.bot.latency * 1000, 1) if self.bot.latency else 0.0
            embed = Embed(
                title="🏓 Pong!",
                description=f"Latência do Gateway: **`{ms} ms`**",
                color=Embed.Color.GREEN,
            )
            await ctx.send(embed=embed)

        @self.command(name="userinfo", description="Exibe informações detalhadas de um membro")
        @describe(user="Membro para consultar (opcional)")
        async def userinfo_cmd(ctx, user: Optional[Member] = None):
            await ctx.defer()
            target = user or ctx.author
            if not target:
                await ctx.send(embed=create_error_embed("Usuário não encontrado."))
                return
            embed = (
                Embed(
                    title=f"👤 Informações de {target.display_name}",
                    color=target.color or Embed.Color.BLURPLE,
                )
                .set_thumbnail(target.avatar_url)
                .add_field("Tag / Username", str(target), inline=True)
                .add_field("ID", f"`{target.id}`", inline=True)
                .add_field("Conta criada em", format_discord_timestamp(target.created_at, "F"), inline=False)
            )
            if target.joined_at:
                embed.add_field("Entrou no servidor", format_discord_timestamp(target.joined_at, "R"), inline=True)
            if target.roles:
                embed.add_field("Cargos", f"{len(target.roles)} cargo(s)", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="serverinfo", description="Exibe informações detalhadas do servidor atual")
        async def serverinfo_cmd(ctx):
            await ctx.defer()
            guild = await ctx.get_guild()
            if not guild:
                await ctx.send(embed=create_error_embed("Comando disponível apenas em servidores."))
                return
            embed = (
                Embed(
                    title=f"🏰 {guild.name}",
                    description=guild.description or "Sem descrição configurada.",
                    color=Embed.Color.BLURPLE,
                )
                .add_field("ID do Servidor", f"`{guild.id}`", inline=True)
                .add_field("Dono", f"<@{guild.owner_id}>", inline=True)
                .add_field("Membros", str(guild.member_count or "N/A"), inline=True)
                .add_field("Cargos", str(len(guild.roles)), inline=True)
                .add_field("Nível de Boost", f"Tier {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
                .add_field("Criado em", format_discord_timestamp(guild.created_at, "D"), inline=True)
            )
            if guild.icon_url:
                embed.set_thumbnail(guild.icon_url)
            await ctx.send(embed=embed)

        @self.command(name="avatar", description="Mostra o avatar em alta resolução de um usuário")
        @describe(user="Usuário para exibir o avatar")
        async def avatar_cmd(ctx, user: Optional[Member] = None):
            await ctx.defer()
            target = user or ctx.author
            embed = Embed(
                title=f"🖼️ Avatar de {target.display_name}",
                color=Embed.Color.BLURPLE,
            ).set_image(target.avatar_url)
            await ctx.send(embed=embed)

        @self.command(name="poll", description="Cria uma enquete nativa da API v10 do Discord")
        @describe(
            question="Pergunta da enquete",
            options="Opções separadas por barra vertical | (ex.: Sim | Não | Talvez)",
            hours="Duração em horas (padrão: 24)",
        )
        async def poll_cmd(ctx, question: str, options: str, hours: Optional[int] = 24):
            await ctx.defer()
            choices = [o.strip() for o in options.split("|") if o.strip()]
            if len(choices) < 2:
                await ctx.send(
                    embed=create_error_embed("Informe pelo menos 2 opções separadas por `|` (ex.: `Opção 1 | Opção 2`).")
                )
                return
            poll = Poll(question=question, answers=choices[:10], duration_hours=hours or 24)
            await ctx.send(poll=poll)


class FunCog(Cog):
    """Cog de Diversão e Minijogos para servidores Discord."""

    def __init__(self, bot):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="dice", description="Rola um dado de N lados")
        @describe(sides="Número de lados do dado (padrão: 6)")
        async def dice_cmd(ctx, sides: Optional[int] = 6):
            max_sides = max(2, min(1000, int(sides or 6)))
            value = random.randint(1, max_sides)
            await ctx.send(
                embed=Embed(
                    title="🎲 Rolagem de Dado",
                    description=f"Você rolou um **d{max_sides}** e tirou **`{value}`**!",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="coinflip", description="Joga uma moeda (Cara ou Coroa)")
        async def coinflip_cmd(ctx):
            result = random.choice(["🪙 **Cara**!", "👑 **Coroa**!"])
            await ctx.send(
                embed=Embed(title="Cara ou Coroa", description=result, color=Embed.Color.GOLD)
            )

        @self.command(name="8ball", description="Faz uma pergunta para a Bola 8 Mágica")
        @describe(question="Sua pergunta")
        async def eightball_cmd(ctx, question: str):
            answers = [
                "Com certeza!",
                "Sem dúvida alguma.",
                "Tudo indica que sim.",
                "Provavelmente sim.",
                "Pergunte novamente mais tarde.",
                "Melhor não te contar agora.",
                "Não conte com isso.",
                "Minhas fontes dizem que não.",
                "Muito duvidoso.",
            ]
            embed = (
                Embed(title="🎱 Bola 8 Mágica", color=Embed.Color.PURPLE)
                .add_field("Pergunta", question, inline=False)
                .add_field("Resposta", random.choice(answers), inline=False)
            )
            await ctx.send(embed=embed)
