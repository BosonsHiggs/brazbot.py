import aiohttp
import asyncio
import json
import websockets
import subprocess
from subprocess import PIPE
import nacl.secret
import nacl.utils
from struct import pack
import logging
import socket

logging.basicConfig(level=logging.DEBUG)

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
        self.bitrate = 64000  # Default bitrate in bits per second (64 kbps)
        self.udp_socket = None
        self.external_ip = None
        self.external_port = None

    async def connect(self):
        await self._update_voice_state()
        await self._handle_voice_server_update()
        await self._connect_to_websocket()
        await self.identify()
        await self.update_bitrate()

    async def update_bitrate(self):
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"https://discord.com/api/v10/channels/{self.channel.id}") as response:
                if response.status == 200:
                    data = await response.json()
                    self.bitrate = data.get('bitrate', self.bitrate)
                    logging.debug(f"Channel bitrate: {self.bitrate}")
                else:
                    logging.error(f"Failed to get channel info: {response.status}")

    async def _update_voice_state(self):
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
            check=self._check_voice_state_update
        )
        
        if 'd' in voice_state_update:
            self.session_id = voice_state_update['d']['session_id']
        else:
            raise Exception("Failed to update voice state")

    async def _handle_voice_server_update(self):
        voice_server_update = await self.bot.wait_for(
            'VOICE_SERVER_UPDATE',
            check=self._check_voice_server_update
        )

        if 'd' in voice_server_update:
            self.endpoint = voice_server_update['d']['endpoint']
            self.token = voice_server_update['d']['token']
        else:
            raise Exception("Failed to handle voice server update")

        if not self.endpoint.startswith("wss://"):
            self.endpoint = "wss://" + self.endpoint

    async def _connect_to_websocket(self):
        self.ws = await websockets.connect(f"{self.endpoint}?v=4")

    def _check_voice_state_update(self, event):
        if 'user_id' in event['d']:
            return event['d']['guild_id'] == self.channel.guild_id and event['d']['user_id'] == self.bot.application_id
        elif 'member' in event['d']:
            return event['d']['guild_id'] == self.channel.guild_id and event['d']['member']['user']['id'] == self.bot.application_id
        return False

    def _check_voice_server_update(self, event):
        return 'd' in event and event['d']['guild_id'] == self.channel.guild_id

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

            if response_data['op'] == 5:
                self.ssrc = response_data['d']['ssrc']

            if response_data['op'] == 8:  # Opcode 8: Hello
                self.heartbeat_interval = response_data['d']['heartbeat_interval']
                asyncio.create_task(self.heartbeat())

            if response_data['op'] == 2:  # Opcode 2: Ready
                self._udp_ip = response_data['d']['ip']
                self._udp_port = response_data['d']['port']
                self.ssrc = response_data['d']['ssrc']
                await self.setup_udp_connection()
                break

    async def select_protocol(self):
        payload = {
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": self.external_ip,
                    "port": self.external_port,
                    "mode": "xsalsa20_poly1305"  # Escolha do modo
                }
            }
        }
        await self.ws.send(json.dumps(payload))

        while True:
            response = await self.ws.recv()
            response_data = json.loads(response)
            if response_data['op'] == 4:  # Opcode 4: Session Description
                self.secret_key = response_data['d']['secret_key']
                break

    async def heartbeat(self):
        try:
            while self.heartbeat_interval is not None:
                await asyncio.sleep(self.heartbeat_interval / 1000)
                await self.ws.send(json.dumps({"op": 3, "d": None}))
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"Heartbeat error: {e}. Attempting to reconnect.")
            await self.resume()

    async def reconnect(self, new_session=False):
        logging.debug("Reconectando...")
        await self.disconnect()
        if new_session:
            self.session_id = None
            await self.connect()
        else:
            await self.resume()

    async def resume(self):
        logging.debug("Tentando retomar a sessão")
        try:
            await self._connect_to_websocket()
            payload = {
                "op": 7,
                "d": {
                    "server_id": str(self.guild_id),
                    "session_id": str(self.session_id),
                    "token": self.token
                }
            }
            await self.ws.send(json.dumps(payload))

            while True:
                response = await self.ws.recv()
                response_data = json.loads(response)

                if response_data['op'] == 9:  # Opcode 9: Resumed
                    logging.info("Sessão retomada com sucesso.")
                    break
                elif response_data['op'] == 8:  # Opcode 8: Hello
                    self.heartbeat_interval = response_data['d']['heartbeat_interval']
                    asyncio.create_task(self.heartbeat())
                    break
                elif response_data['op'] == 4:
                    # Handle Session Description if needed
                    pass
                else:
                    logging.error(f"Erro ao retomar a sessão: {response_data}")
                    await self.reconnect(new_session=True)
                    break
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"ConnectionClosedError: {e}. Tentando reconectar.")
            await self.reconnect(new_session=True)
        except Exception as e:
            logging.error(f"Erro durante retomar sessão: {e}")
            await self.reconnect(new_session=True)

    async def disconnect(self):
        if self.heartbeat_interval:
            self.heartbeat_interval = None

        if self.ws:
            await self.ws.close()
            self.ws = None

    async def play(self, source_url):
        logging.debug("play 1")
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url) as response:
                logging.debug("play 2")
                if response.status == 200:
                    logging.debug("play 3")
                    try:
                        logging.debug("Creating ffmpeg process")
                        ffmpeg_process = await self.create_ffmpeg_process()
                        logging.debug(f"play 3: {ffmpeg_process}")

                        if ffmpeg_process is None:
                            logging.error("Process creation failed")
                            return
                        logging.debug("play 4")
                        self._encoder_process = ffmpeg_process  # Ensure _encoder_process is set
                        logging.debug(f"play 5: {self._encoder_process}")

                        async for chunk in response.content.iter_chunked(1024):
                            logging.debug("play 6")
                            if ffmpeg_process.stdin is not None:
                                logging.debug("play 7")
                                ffmpeg_process.stdin.write(chunk)
                                logging.debug("play 8")
                            else:
                                raise Exception("ffmpeg_process.stdin is None")
                        logging.debug("play 9")
                        ffmpeg_process.stdin.close()
                        logging.debug("play 10")
                        #await self._read_process_output(ffmpeg_process, "ffmpeg")
                        logging.debug("play 11")
                        if self._encoder_process:
                            logging.debug("play 12")
                            self._send_audio_task = asyncio.create_task(self.send_audio_packets())
                            logging.debug("play 13")
                    except Exception as e:
                        logging.error(f"Error in play: {e}")
                else:
                    logging.error(f"Failed to fetch audio from URL: {response.status}")

    async def create_ffmpeg_process(self):
        try:
            logging.debug("create_ffmpeg_process 1")
            ffmpeg_process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i', 'pipe:0',  # Entrada de áudio a partir do pipe
                '-f', 's16le',
                '-ar', '48000',
                '-ac', '2',
                '-b:a', str(self.bitrate),  # Configure the bitrate
                'pipe:1',  # Saída de áudio para pipe
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                bufsize=0  # Setting bufsize to 0 as required
            )
            logging.debug(f"create_ffmpeg_process 2: {ffmpeg_process}")
            logging.debug(f"ffmpeg process created with PID: {ffmpeg_process.pid}")
            return ffmpeg_process

        except Exception as e:
            logging.error(f"Failed to create ffmpeg process: {e}")
            return None

    async def _read_process_output(self, process, name):
        logging.debug(f"Reading stdout for process: {name}")
        if process.stdout is not None:
            while True:
                line = await process.stdout.read(1024)
                if not line:
                    break
                try:
                    logging.debug(f"{name} stdout: {line}")
                except Exception as e:
                    logging.error(f"Error reading {name} stdout: {e}")

        if process.stderr is not None:
            logging.debug(f"Reading stderr for process: {name}")
            while True:
                line = await process.stderr.read(1024)
                if not line:
                    break
                try:
                    logging.debug(f"{name} stderr: {line.decode('utf-8', errors='replace')}")
                except Exception as e:
                    logging.error(f"Error reading {name} stderr: {e}")

    async def send_audio_packets(self):
        sequence_number = 0
        timestamp = 0
        await self.set_speaking(True)
        while self._encoder_process is not None:
            try:
                data = await self._encoder_process.stdout.read(3840)  # 20ms de áudio
                if not data:
                    stderr_output = await self._encoder_process.stderr.read()
                    logging.debug(f"ffmpeg stderr: {stderr_output.decode()}")
                    break
                logging.debug(f"Sending audio packet with sequence number: {sequence_number}")

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

            except websockets.exceptions.ConnectionClosedError as e:
                if e.code == 4006:
                    logging.error("Error 4006: Session is no longer valid. Attempting to reconnect.")
                    await self.resume()
                else:
                    logging.error(f"ConnectionClosedError: {e}")
                break
            except Exception as e:
                logging.error(f"Error while sending audio packets: {e}")
                break

        await self.send_silence()
        await self.set_speaking(False)

    async def send_silence(self):
        silence_frame = b'\xF8\xFF\xFE' * 5
        for _ in range(5):
            try:
                header = bytearray(12)
                header[0] = 0x80
                header[1] = 0x78
                header[2:4] = pack('>H', 0)  # Sequence number
                header[4:8] = pack('>I', 0)  # Timestamp
                header[8:12] = pack('>I', self.ssrc)  # SSRC

                packet = self.encrypt_packet(header, silence_frame)
                await self.ws.send(packet)
                await asyncio.sleep(0.02)
            except Exception as e:
                logging.error(f"Error while sending silence: {e}")

    async def setup_udp_connection(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setblocking(False)
        self.udp_socket.sendto(b'\x01\x00\x00\x00' + pack('>I', self.ssrc), (self._udp_ip, self._udp_port))
        
        def parse_ip_and_port(response):
            ip = response[8:72].split(b'\x00', 1)[0].decode('ascii')
            port = int.from_bytes(response[72:74], 'big')
            return ip, port
        
        response = await asyncio.get_event_loop().sock_recv(self.udp_socket, 1024)
        self.external_ip, self.external_port = parse_ip_and_port(response)
        await self.select_protocol()

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

