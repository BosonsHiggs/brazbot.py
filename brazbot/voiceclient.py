import aiohttp
import asyncio
import json
import websockets
import subprocess
import socket
from subprocess import Popen, PIPE
import nacl.secret
import nacl.utils
from struct import pack

class VoiceClient:
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel
        self.token = None
        self.session_id = None
        self.endpoint = None
        self.heartbeat_interval = None
        self.ws = None
        self.guild_id = channel.guild_id
        self.ssrc = None
        self._encoder_process = None
        self._send_audio_task = None
        self.secret_key = None
        self._udp_ip = None
        self._udp_port = None
        self._data = None

    async def connect(self):
        voice_state_update = {
            "op": 4,
            "d": {
                "guild_id": str(self.channel.guild_id),
                "channel_id": str(self.channel.id),
                "self_mute": False,
                "self_deaf": False
            }
        }
        await self.bot._ws.send_json(voice_state_update)

        voice_state_update = await self.bot.wait_for(
            'VOICE_STATE_UPDATE',
            check=lambda event: event['d']['guild_id'] == self.channel.guild_id and event['d']['member']['user']['id'] == self.bot.application_id
        )
        self.session_id = voice_state_update['d']['session_id']

        voice_server_update = await self.bot.wait_for(
            'VOICE_SERVER_UPDATE',
            check=lambda event: event['d']['guild_id'] == self.channel.guild_id
        )
        self.endpoint = voice_server_update['d']['endpoint']
        self.token = voice_server_update['d']['token']

        if not self.endpoint.startswith("wss://"):
            self.endpoint = "wss://" + self.endpoint

        self.ws = await websockets.connect(f"{self.endpoint}?v=4")
        await self.identify()

    async def identify(self):
        payload = {
            "op": 0,
            "d": {
                "server_id": self.guild_id,
                "user_id": self.bot.application_id,
                "session_id": self.session_id,
                "token": self.token
            }
        }
        await self.ws.send(json.dumps(payload))

        while True:
            response = await self.ws.recv()
            response_data = json.loads(response)

            if response_data['op'] == 8:  # Opcode 8: Hello
                self.heartbeat_interval = response_data['d']['heartbeat_interval']
                asyncio.create_task(self.heartbeat())

            if response_data['op'] == 2:  # Opcode 2: Ready
                self._udp_ip = response_data['d']['ip']
                self._udp_port = response_data['d']['port']
                self.ssrc = response_data['d']['ssrc']
                try:
                    await self.select_protocol()
                except Exception as e:
                    print(f"ERROR PROTOCOL: {e}")
                break

    async def select_protocol(self):
        payload = {
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": self._udp_ip,
                    "port": self._udp_port,
                    "mode": "xsalsa20_poly1305"
                }
            }
        }
        await self.ws.send(json.dumps(payload))

        # Receive session description
        while True:
            response = await self.ws.recv()
            response_data = json.loads(response)

            if response_data['op'] == 4:  # Opcode 4: Session Description
                self.secret_key = response_data['d']['secret_key']
                self._send_audio_task = asyncio.create_task(self.send_audio_packets())
                break

    async def heartbeat(self):
        while self.heartbeat_interval is not None:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            await self.ws.send(json.dumps({"op": 3, "d": None}))

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def play(self, source_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url) as response:
                if response.status == 200:
                    ffmpeg = await self.create_ffmpeg_process()
                    async for chunk in response.content.iter_chunked(1024):
                        ffmpeg.stdin.write(chunk)
                    ffmpeg.stdin.close()
                    await ffmpeg.wait()
                    if self._encoder_process:
                        self._data = await self._encoder_process.stdout.read(3840)  # 20ms de áudio
                        self._send_audio_task = asyncio.create_task(self.send_audio_packets())

    async def create_ffmpeg_process(self):
        self._encoder_process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-i', 'pipe:0',
            '-f', 's16le',
            '-ar', '48000',
            '-ac', '2',
            'pipe:1',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        return self._encoder_process

    async def send_audio_packets(self):
        sequence_number = 0
        timestamp = 0

        print(00000000)
        print(f"\n\n\nself._data: {self._data}\n\n\n")
        while self._data is not None:
            print(10000000)
            
            if not self._data:
                break
            data = self._data 

            header = bytearray(12)
            header[0] = 0x80
            header[1] = 0x78
            header[2:4] = pack('>H', sequence_number)  # Sequence number
            header[4:8] = pack('>I', timestamp)  # Timestamp
            header[8:12] = pack('>I', self.ssrc)  # SSRC

            packet = self.encrypt_packet(header, data)
            await self.ws.send(packet)

            sequence_number += 1
            timestamp += 960  # 48kHz / 50fps = 960

            await asyncio.sleep(0.02)

        await self.set_speaking(False)

    def encrypt_packet(self, header, data):
        nonce = bytearray(24)
        nonce[:12] = header
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        encrypted = box.encrypt(bytes(data), bytes(nonce)).ciphertext
        return header + encrypted

    async def set_speaking(self, speaking):
        payload = {
            "op": 5,
            "d": {
                "speaking": int(speaking),
                "delay": 0,
                "ssrc": self.ssrc
            }
        }
        await self.ws.send(json.dumps(payload))

    async def stop(self):
        if self._encoder_process:
            self._encoder_process.terminate()
            self._encoder_process = None
        if self._send_audio_task:
            self._send_audio_task.cancel()
            self._send_audio_task = None
