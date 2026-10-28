"""
Exemplo Completo de Produção (brazbot.py v2.0.0 — Discord API v10 & Voice Gateway v8).
Demonstra o uso integrado de:
- Cogs nativas prontas para uso (MusicCog, ModerationCog, UtilityCog, FunCog)
- Enquetes nativas da API v10 (`Poll`)
- AutoModeração (`AutoModRule`)
- Soundboard (`Soundboard`)
- Menus de seleção avançados (`UserSelect`, `RoleSelect`, `ChannelSelect`)
- Comandos de Menu de Contexto (`@bot.user_command`, `@bot.message_command`)
"""

import os
from brazbot import (
    AutoModRule,
    Bot,
    ChannelSelect,
    Embed,
    FunCog,
    Member,
    ModerationCog,
    MusicCog,
    Poll,
    RoleSelect,
    UserSelect,
    UtilityCog,
    View,
    describe,
    has_permissions,
)

INTENTS = [
    "GUILDS",
    "GUILD_MEMBERS",
    "GUILD_MODERATION",
    "GUILD_VOICE_STATES",
    "GUILD_MESSAGES",
    "MESSAGE_CONTENT",
    "GUILD_MESSAGE_REACTIONS",
    "GUILD_MESSAGE_POLLS",
]


class MeuBotProducao(Bot):
    async def setup_hook(self):
        # Carrega pacotes completos de comandos para criação rápida de bots
        self.add_cog(MusicCog(self))
        self.add_cog(ModerationCog(self))
        self.add_cog(UtilityCog(self))
        self.add_cog(FunCog(self))

    async def on_ready(self, data):
        print(f"🚀 Bot conectado como {data.get('user', {}).get('username')} (ID: {self.application_id})")
        guild_id = os.getenv("DISCORD_GUILD_ID")
        await self.command_handler.sync_commands(guild_id=guild_id)


bot = MeuBotProducao(
    token=os.getenv("DISCORD_TOKEN", "SEU_TOKEN"),
    command_prefix="!",
    intents=INTENTS,
)


@bot.command(name="painel_selecao", description="Envia menus de seleção de Usuário, Cargo e Canal (API v10)")
async def painel_selecao(ctx):
    await ctx.defer()
    view = (
        View(bot)
        .add_item(UserSelect("sel_user", placeholder="Selecione um usuário..."))
        .add_item(RoleSelect("sel_role", placeholder="Selecione um cargo..."))
        .add_item(ChannelSelect("sel_chan", placeholder="Selecione um canal de voz...", channel_types=[2]))
    )
    await ctx.send("Selecione nos menus abaixo:", components=view)


@bot.command(name="automod_filtro", description="Cria uma regra de AutoMod para bloquear palavras proibidas")
@has_permissions(manage_guild=True)
@describe(palavras="Palavras separadas por vírgula")
async def automod_filtro(ctx, palavras: str):
    await ctx.defer()
    lista = [p.strip() for p in palavras.split(",") if p.strip()]
    regra = await AutoModRule.create_keyword_rule(
        bot,
        ctx.guild_id,
        name="Filtro Brazbot",
        keywords=lista,
        timeout_seconds=60,
    )
    await ctx.send(
        embed=Embed(
            title="🛡️ Regra AutoMod Criada",
            description=f"Regra **{regra.name}** (`{regra.id}`) ativa com {len(lista)} palavra(s).",
            color=Embed.Color.GREEN,
        )
    )


@bot.user_command(name="Ver Perfil")
async def ver_perfil_context_menu(ctx):
    target_id = ctx.interaction["data"]["target_id"]
    member = await Member.from_user_id(bot, target_id, ctx.guild_id)
    await ctx.send(
        embed=Embed(
            title=f"Perfil de {member.display_name}",
            description=f"ID: `{member.id}`\nMenção: {member.mention}",
            color=Embed.Color.BLURPLE,
        ).set_thumbnail(member.avatar_url),
        ephemeral=True,
    )


if __name__ == "__main__":
    bot.run()
