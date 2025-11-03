import os
import asyncio
import base64
import traceback
import pyaudio

from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
load_dotenv()
# Audio setup
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
MODEL = "models/gemini-2.5-flash"

# Initialize Google Gemini client
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GOOGLE_API_KEY"),
)

CONFIG = types.LiveConnectConfig(
    response_modalities=["TEXT"],
    media_resolution="MEDIA_RESOLUTION_LOW",
    # Enable transcription mode by using text output modality
)

pya = pyaudio.PyAudio()


class LiveTranscriber:
    def __init__(self):
        self.session = None
        self.audio_queue = None

    async def listen_audio(self):
        """Continuously read audio from microphone and stream it."""
        mic_info = pya.get_default_input_device_info()
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        while True:
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE, exception_on_overflow=False)
            await self.audio_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def send_audio(self):
        """Send audio chunks to Gemini Live API."""
        while True:
            chunk = await self.audio_queue.get()
            await self.session.send(input=chunk)

    async def receive_transcripts(self):
        """Continuously receive transcription text responses."""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if response.text:
                    print(response.text, end="", flush=True)

    async def run(self):
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                self.audio_queue = asyncio.Queue(maxsize=5)

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.listen_audio())
                    tg.create_task(self.send_audio())
                    tg.create_task(self.receive_transcripts())

        except Exception as e:
            print("Error:", e)
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(LiveTranscriber().run())
