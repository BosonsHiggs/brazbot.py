"""
Suíte de testes automatizados para validação da biblioteca brazbot.py v2.0.0.
Testa:
- Importação de todos os módulos e classes públicas
- Snowflakes, Cache TTL, Permissões e Intents da API v10
- Rate Limiter preventivo (`compute_route_key`, `RateLimitBucket`, `USER_AGENT`)
- Codificação e decodificação Opus nativa via `ctypes` (`libopus`) e escalonamento de volume PCM 16-bit
- Criptografia e descriptografia RTP AEAD (`aead_aes256_gcm_rtpsize`)
- Registro de comandos híbridos, inferência de tipos de opções Slash, SubCommandGroup e Cogs nativas
- Serialização de componentes da API v10 (Embed, Button, View, Dropdown, UserSelect, Form, Poll)
"""

import asyncio
import os
import struct
import unittest

import brazbot
from brazbot import (
     USER_AGENT,
    ActionRow,
    Attachment,
    AutoModRule,
    Bot,
    Button,
    ButtonStyle,
    Cache,
    Channel,
    ChannelSelect,
    Cog,
    CommandContext,
    DiscordBot,
    Dropdown,
    DropdownOption,
    Embed,
    EventTypes,
    FFmpegAudioSource,
    File,
    Form,
    FormField,
    FunCog,
    Guild,
    GuildMusicPlayer,
    Intents,
    Member,
    ModerationCog,
    MusicCog,
    OpusDecoder,
    OpusEncoder,
    PCMAudioSource,
    Permissions,
    Poll,
    Role,
    RoleSelect,
    Snowflake,
    Soundboard,
    SubCommandGroup,
    TextChannel,
    Track,
    UDPVoiceConnection,
    UserSelect,
    UtilityCog,
    View,
    VoiceChannel,
    VoiceClient,
    VoiceState,
    Webhook,
    YTDLSource,
    describe,
    rate_limit,
    sync_slash_commands,
)
from brazbot.http import compute_route_key
from brazbot.voiceclient import PCM_FRAME_SIZE, SAMPLES_PER_FRAME, scale_pcm16_volume


class TestBrazbotLibrary(unittest.IsolatedAsyncioTestCase):
    def test_public_exports_and_user_agent(self):
        self.assertEqual(brazbot.__version__, "2.0.0")
        self.assertTrue(USER_AGENT.startswith("DiscordBot (https://github.com/BosonsHiggs/brazbot.py, 2.0.0)"))

    def test_snowflake_and_cache(self):
        sf_id = "1130837584742977697"
        self.assertTrue(Snowflake.is_valid(sf_id))
        self.assertFalse(Snowflake.is_valid("invalid"))
        dt = Snowflake.to_datetime(sf_id)
        self.assertEqual(dt.year, 2023)

        c = Cache()
        c.set("k1", "v1", ttl=10)
        self.assertEqual(c.get("k1"), "v1")
        self.assertGreater(c.get_remaining_ttl("k1"), 5.0)
        c.delete("k1")
        self.assertIsNone(c.get("k1"))

    def test_permissions_and_intents(self):
        intents_val = Intents.resolve(["GUILDS", "GUILD_VOICE_STATES", "MESSAGE_CONTENT"])
        self.assertEqual(intents_val, (1 << 0) | (1 << 7) | (1 << 15))

        p = Permissions(ban_members=True, manage_messages=True)
        self.assertTrue(p.has(ban_members=True))
        self.assertFalse(p.has(administrator=True))
        self.assertEqual(p.missing(ban_members=True, kick_members=True), ["kick_members"])

        admin_p = Permissions(administrator=True)
        self.assertTrue(admin_p.has(ban_members=True, manage_guild=True, send_polls=True))

    def test_route_key_major_parameters(self):
        k1 = compute_route_key("POST", "/channels/111111111111111111/messages/222222222222222222")
        k2 = compute_route_key("POST", "/channels/111111111111111111/messages/333333333333333333")
        k3 = compute_route_key("POST", "/channels/999999999999999999/messages/222222222222222222")
        self.assertEqual(k1, k2)
        self.assertNotEqual(k1, k3)

    def test_opus_encode_decode_and_volume_scaling(self):
        # Gera 20ms (960 amostras estéreo = 3840 bytes) de onda quadrada PCM 16-bit
        raw_pcm = struct.pack("<" + "h" * (SAMPLES_PER_FRAME * 2), *([4000, -4000] * SAMPLES_PER_FRAME))
        self.assertEqual(len(raw_pcm), PCM_FRAME_SIZE)

        scaled_half = scale_pcm16_volume(raw_pcm, 0.5)
        first_sample = struct.unpack_from("<h", scaled_half, 0)[0]
        self.assertEqual(first_sample, 2000)

        scaled_zero = scale_pcm16_volume(raw_pcm, 0.0)
        self.assertEqual(scaled_zero, b"\x00" * PCM_FRAME_SIZE)

        encoder = OpusEncoder()
        decoder = OpusDecoder()
        opus_packet = encoder.encode(raw_pcm, SAMPLES_PER_FRAME)
        self.assertGreater(len(opus_packet), 2)
        self.assertLess(len(opus_packet), 1000)

        decoded_pcm = decoder.decode(opus_packet)
        self.assertEqual(len(decoded_pcm), PCM_FRAME_SIZE)
        encoder.destroy()
        decoder.destroy()

    def test_aead_aes256_gcm_rtpsize_encryption_roundtrip(self):
        bot = Bot(token="dummy")
        ch = VoiceChannel({"id": "123456789012345678", "guild_id": "987654321098765432", "name": "General"}, bot=bot)
        vc = VoiceClient(bot, ch)
        udp = UDPVoiceConnection(vc)
        udp.ssrc = 424242
        udp.secret_key = os.urandom(32)
        udp.mode = "aead_aes256_gcm_rtpsize"

        opus_payload = b"\xf8\xff\xfe\x11\x22\x33\x44"
        encrypted_packet = udp.create_packet(opus_payload)
        self.assertGreater(len(encrypted_packet), 12 + len(opus_payload) + 4)

        parsed = udp.decrypt_packet(encrypted_packet)
        self.assertIsNotNone(parsed)
        ssrc, seq, ts, decrypted_opus = parsed
        self.assertEqual(ssrc, 424242)
        self.assertEqual(seq, 0)
        self.assertEqual(ts, 0)
        self.assertEqual(decrypted_opus, opus_payload)

    async def test_voice_state_tracking_and_member_context(self):
        bot = Bot(token="dummy", command_prefix="!")
        await bot.process_message(
            {
                "op": 0,
                "t": "GUILD_CREATE",
                "s": 1,
                "d": {
                    "id": "111",
                    "name": "Servidor Teste",
                    "channels": [{"id": "222", "name": "Palco Musical", "type": 2}],
                    "voice_states": [
                        {"user_id": "333", "channel_id": "222", "session_id": "sess_abc"}
                    ],
                },
            }
        )

        vs = bot.get_member_voice_state("111", "333")
        self.assertIsNotNone(vs)
        self.assertEqual(vs.channel.id, "222")
        self.assertEqual(vs.channel.name, "Palco Musical")

        # Cria CommandContext a partir de uma interação desse membro
        ctx = CommandContext(
            bot,
            {},
            interaction={
                "id": "999",
                "token": "tok",
                "guild_id": "111",
                "channel_id": "444",
                "member": {"user": {"id": "333", "username": "BosonUser"}, "roles": ["555"]},
                "data": {"name": "play", "options": [{"name": "url", "type": 3, "value": "test.mp3"}]},
            },
        )
        self.assertEqual(ctx.author.id, "333")
        self.assertEqual(ctx.author["id"], "333")
        self.assertEqual(ctx.author.username, "BosonUser")
        self.assertIsNotNone(ctx.author.voice)
        self.assertEqual(ctx.author.voice.channel.id, "222")
        await bot.close()

    def test_builtin_cogs_and_slash_payloads(self):
        bot = Bot(token="dummy")
        bot.add_cog(MusicCog(bot))
        bot.add_cog(ModerationCog(bot))
        bot.add_cog(UtilityCog(bot))
        bot.add_cog(FunCog(bot))

        grp = SubCommandGroup(bot, "config")
        sub = grp.subgroup("voice")

        @sub.command(name="bitrate", description="Define bitrate")
        async def set_bitrate(ctx, kbps: int):
            pass

        payloads = bot.command_handler._build_slash_command_payloads()
        names = {p["name"] for p in payloads}
        self.assertIn("play", names)
        self.assertIn("seek", names)
        self.assertIn("filter", names)
        self.assertIn("ban", names)
        self.assertIn("poll", names)
        self.assertIn("config", names)

    def test_ui_components_and_polls_serialization(self):
        poll = Poll("Qual sua linguagem favorita?", ["Python", "Rust", "Go"], duration_hours=12)
        p_dict = poll.to_dict()
        self.assertEqual(p_dict["question"]["text"], "Qual sua linguagem favorita?")
        self.assertEqual(len(p_dict["answers"]), 3)

        view = (
            View()
            .add_item(Button("Tocar", style=ButtonStyle.SUCCESS, custom_id="btn_play"))
            .add_item(Button("Pausar", style=ButtonStyle.SECONDARY, custom_id="btn_pause"))
            .add_item(UserSelect("sel_u", placeholder="Escolha um membro"))
        )
        comps = view.to_components()
        self.assertEqual(len(comps), 2)  # 1 linha para os 2 botões + 1 linha para o UserSelect

        form = Form("Cadastro", "form_cad", [FormField("Nome", "Digite seu nome", "f_nome")])
        self.assertEqual(form.to_component["type"], 9)


if __name__ == "__main__":
    unittest.main()


class TestFFmpegAudioPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_ffmpeg_pcm_and_ogg_opus_demuxer(self):
        import tempfile, wave
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b"\x10\x00\x10\x00" * (48000 // 5))  # 200ms stereo

            # 1. Modo PCM -> OpusEncoder
            src_pcm = FFmpegAudioSource(wav_path, volume=0.8, use_opus_pipe=False)
            await src_pcm.create_process()
            frame_pcm = await src_pcm.read()
            self.assertIsNotNone(frame_pcm)
            self.assertEqual(len(frame_pcm), PCM_FRAME_SIZE)
            await src_pcm.cleanup()

            # 2. Modo Ogg/Opus direto do FFmpeg -> OggOpusDemuxer -> OpusDecoder
            src_opus = FFmpegAudioSource(wav_path, use_opus_pipe=True)
            await src_opus.create_process()
            opus_pkt = await src_opus.read()
            self.assertIsNotNone(opus_pkt)
            self.assertGreater(len(opus_pkt), 2)
            dec = OpusDecoder()
            pcm_decoded = dec.decode(opus_pkt)
            self.assertEqual(len(pcm_decoded), PCM_FRAME_SIZE)
            dec.destroy()
            await src_opus.cleanup()
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
