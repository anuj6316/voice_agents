import asyncio
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import google, silero

load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# ✅ Initialize STT correctly
if GOOGLE_KEY:
    print("🎤 Using Google Speech-to-Text")
    # os.environ["GOOGLE_API_KEY"] = GOOGLE_KEY
    stt = google.STT()  # No need to pass api_key anymore
else:
    raise ValueError("❌ No GOOGLE_API_KEY found in .env")

# ✅ LiveKit Agent
class Transcriber(Agent):
    async def on_start(self, session: AgentSession):
        print("🎙️ Listening... (Ctrl+C to stop)")
        mic_source = silero.MicrophoneSource()  # Captures live mic input
        
        async for chunk in mic_source.stream():
            try:
                text = await stt.transcribe(chunk.audio, mime_type="audio/wav")
                if text and text.strip():
                    print(f"🗣️ {text}")
            except Exception as e:
                print(f"⚠️ STT error: {e}")

async def main():
    agent = Transcriber()
    await agents.run(agent)

if __name__ == "__main__":
    asyncio.run(main())
