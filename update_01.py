import os
import asyncio
import base64
import io
import traceback
import pyaudio
import argparse
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()
# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
 
# Gemini model configuration
MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025"
 
# Initialize PyAudio
pya = pyaudio.PyAudio()
 
class VoiceChatbot:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None
        
        # Configure Gemini client
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Configure the session
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            ),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=25600,
                sliding_window=types.SlidingWindow(target_tokens=12800),
            ),
        )
        
        # Initial system message
        self.system_message = """You are a helpful and friendly AI assistant. Always respond in the same language that the user is speaking. 

Language matching rules:
- If the user writes in Hindi, respond completely in Hindi
- If the user writes in English, respond in English
- If the user writes in any other language, respond in that language
- Match the user's language naturally and maintain it throughout your response
- Be concise and conversational in your responses

Your primary goal is to mirror the user's language choice to ensure comfortable and natural communication."""
        
    async def listen_audio(self):
        """Capture audio from microphone and send to Gemini"""
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
            
        print("Listening... (Press Ctrl+C to stop)")
        
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
    
    async def receive_audio(self):
        """Receive audio responses from Gemini"""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(f"\nAI: {text}", end="", flush=True)
            
            # Handle interruptions
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
    
    async def play_audio(self):
        """Play audio responses from Gemini"""
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)
    
    async def send_text(self):
        """Send text messages to Gemini"""
        # Send initial system message
        await self.session.send(input=self.system_message, end_of_turn=True)
        
        while True:
            text = await asyncio.to_thread(input, "\nYou (text or 'q' to quit): ")
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)
    
    async def send_realtime(self):
        """Send real-time audio to Gemini"""
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)
    
    async def run(self):
        """Main function to run the voice chatbot"""
        try:
            async with (
                self.client.aio.live.connect(model=MODEL, config=self.config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                
                # Initialize queues
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                
                # Create tasks
                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                
                # Wait for text input task to complete (user quits)
                await send_text_task
                raise asyncio.CancelledError("User requested exit")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
        finally:
            if self.audio_stream:
                self.audio_stream.close()
            print("\nChatbot session ended.")
 
def main():
    parser = argparse.ArgumentParser(description="Voice Chatbot with Google Gemini Live API")
    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Gemini API key (or set GEMINI_API_KEY environment variable)"
    )
    args = parser.parse_args()
    
    # Set API key if provided
    if args.key:
        os.environ["GEMINI_API_KEY"] = args.key
    
    # Check if API key is available
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: Gemini API key not found.")
        print("Please set GEMINI_API_KEY environment variable or use --key argument.")
        return
    
    # Run the chatbot
    chatbot = VoiceChatbot()
    try:
        asyncio.run(chatbot.run())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
 
if __name__ == "__main__":
    main()
 