"""
Ferramenta de Linha de Comando (CLI) oficial da biblioteca brazbot.py (`brazbot`).
Comandos disponíveis:
- `brazbot version`: Exibe a versão da biblioteca e da API suportada
- `brazbot doctor`: Diagnostica o ambiente de produção (Python, aiohttp, PyNaCl, cryptography, yt-dlp, FFmpeg, libopus)
- `brazbot init <diretorio>`: Gera a estrutura limpa de um novo projeto de bot pronto para produção
"""

import argparse
import ctypes.util
import os
import shutil
import sys
from typing import List, Optional

from brazbot.http import API_VERSION, LIBRARY_VERSION

STARTER_BOT_TEMPLATE = '''import asyncio
import os
from dotenv import load_dotenv

from brazbot.bot import Bot
from brazbot.cogs_builtin import FunCog, ModerationCog, MusicCog, UtilityCog

load_dotenv()

INTENTS = ["GUILDS", "GUILD_VOICE_STATES", "GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_MEMBERS"]


class ProductionBot(Bot):
    async def setup_hook(self):
        # Adiciona as Cogs nativas de Música, Moderação, Utilidades e Diversão
        self.add_cog(MusicCog(self))
        self.add_cog(ModerationCog(self))
        self.add_cog(UtilityCog(self))
        self.add_cog(FunCog(self))

    async def on_ready(self, data):
        print(f"✅ Bot online como {data.get('user', {}).get('username')} (App ID: {self.application_id})")
        guild_id = os.getenv("DISCORD_GUILD_ID")
        await self.command_handler.sync_commands(guild_id=guild_id)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Defina a variável de ambiente DISCORD_TOKEN no arquivo .env")
    bot = ProductionBot(token=token, command_prefix="!", intents=INTENTS)
    bot.run()
'''


def cmd_doctor() -> int:
    print(f"🔍 Diagnóstico de Ambiente brazbot.py v{LIBRARY_VERSION} (Discord API v{API_VERSION})\n")
    print(f"  • Python: {sys.version.split()[0]} ({sys.executable})")

    packages = [
        ("aiohttp", "aiohttp"),
        ("PyNaCl", "nacl"),
        ("cryptography", "cryptography"),
        ("yt-dlp", "yt_dlp"),
        ("python-dotenv", "dotenv"),
    ]
    for label, mod_name in packages:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "instalado")
            print(f"  ✅ {label}: {ver}")
        except ImportError:
            print(f"  ⚠️  {label}: NÃO INSTALADO (instale com: pip install -U {label})")

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"  ✅ FFmpeg: encontrado em {ffmpeg_path}")
    else:
        print("  ⚠️  FFmpeg: NÃO ENCONTRADO no PATH (necessário para reprodução de música/voz)")

    opus_lib = ctypes.util.find_library("opus") or (
        "/usr/lib/x86_64-linux-gnu/libopus.so.0"
        if os.path.exists("/usr/lib/x86_64-linux-gnu/libopus.so.0")
        else None
    )
    if opus_lib:
        print(f"  ✅ libopus: encontrado ({opus_lib})")
    else:
        print("  ℹ️  libopus: via fallback automático FFmpeg Ogg/Opus")

    return 0


def cmd_init(target_dir: str) -> int:
    os.makedirs(target_dir, exist_ok=True)
    bot_file = os.path.join(target_dir, "bot.py")
    env_file = os.path.join(target_dir, ".env.example")

    with open(bot_file, "w", encoding="utf-8") as fp:
        fp.write(STARTER_BOT_TEMPLATE)

    with open(env_file, "w", encoding="utf-8") as fp:
        fp.write("DISCORD_TOKEN=seu_token_aqui\nDISCORD_GUILD_ID=\n")

    print(f"✅ Projeto criado com sucesso em: {os.path.abspath(target_dir)}")
    print("   1. Copie `.env.example` para `.env` e preencha `DISCORD_TOKEN`")
    print("   2. Execute `python bot.py`")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brazbot",
        description=f"CLI oficial da biblioteca brazbot.py v{LIBRARY_VERSION} (Discord API v{API_VERSION})",
    )
    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("version", help="Exibe a versão da biblioteca")
    sub.add_parser("doctor", help="Verifica dependências de produção, FFmpeg e Opus")

    init_parser = sub.add_parser("init", help="Cria um novo projeto de bot pronto para produção")
    init_parser.add_argument("directory", nargs="?", default="meu_bot", help="Diretório do projeto")

    args = parser.parse_args(argv)
    if args.subcommand == "version":
        print(f"brazbot.py v{LIBRARY_VERSION} (Discord API v{API_VERSION} / Voice Gateway v8)")
        return 0
    if args.subcommand == "doctor":
        return cmd_doctor()
    if args.subcommand == "init":
        return cmd_init(args.directory)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
