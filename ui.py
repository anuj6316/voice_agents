import os
import asyncio
import threading
import gradio as gr
import pyaudio
import numpy as np
from google import genai
from google.genai import types
from dotenv import load_dotenv
import queue

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
        self.is_running = False
        self.loop = None
        self.chat_history = []
        
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
        
        # System message
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
        
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        
        while self.is_running:
            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            except Exception as e:
                print(f"Audio input error: {e}")
                break
    
    async def receive_audio(self):
        """Receive audio responses from Gemini"""
        while self.is_running:
            try:
                turn = self.session.receive()
                response_text = ""
                async for response in turn:
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        continue
                    if text := response.text:
                        response_text += text
                
                if response_text:
                    self.chat_history.append(("AI", response_text))
                
                # Handle interruptions
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
            except Exception as e:
                if self.is_running:
                    print(f"Receive error: {e}")
                break
    
    async def play_audio(self):
        """Play audio responses from Gemini"""
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        
        while self.is_running:
            try:
                bytestream = await asyncio.wait_for(
                    self.audio_in_queue.get(),
                    timeout=1.0
                )
                await asyncio.to_thread(stream.write, bytestream)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Playback error: {e}")
                break
        
        stream.close()
    
    async def send_realtime(self):
        """Send real-time audio to Gemini"""
        while self.is_running:
            try:
                msg = await asyncio.wait_for(self.out_queue.get(), timeout=1.0)
                await self.session.send(input=msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Send error: {e}")
                break
    
    async def run_session(self):
        """Main function to run the voice chatbot session"""
        try:
            async with self.client.aio.live.connect(model=MODEL, config=self.config) as session:
                self.session = session
                
                # Initialize queues
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                
                # Send system message
                await self.session.send(input=self.system_message, end_of_turn=True)
                
                # Create tasks
                tasks = [
                    asyncio.create_task(self.send_realtime()),
                    asyncio.create_task(self.listen_audio()),
                    asyncio.create_task(self.receive_audio()),
                    asyncio.create_task(self.play_audio()),
                ]
                
                # Wait for all tasks
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            print(f"Session error: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.close()
    
    def start(self):
        """Start the chatbot"""
        if not self.is_running:
            self.is_running = True
            self.loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self.run_session())
            
            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
            return "🎙️ Listening... Speak now!"
        return "Already running"
    
    def stop(self):
        """Stop the chatbot"""
        if self.is_running:
            self.is_running = False
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
            return "⏹️ Stopped"
        return "Not running"
    
    def get_chat_history(self):
        """Get formatted chat history"""
        return "\n\n".join([f"**{role}:** {msg}" for role, msg in self.chat_history])


# Create chatbot instance
chatbot = VoiceChatbot()


# Gradio Interface
def create_ui():
    with gr.Blocks(theme=gr.themes.Soft(), title="Voice Chatbot") as app:
        gr.Markdown(
            """
            # 🎙️ Voice Chatbot
            ### Powered by Google Gemini
            Talk naturally and the AI will respond in your language!
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                status_box = gr.Textbox(
                    label="Status",
                    value="Ready to start",
                    interactive=False,
                    lines=2
                )
                
                with gr.Row():
                    start_btn = gr.Button("🎙️ Start Voice Chat", variant="primary", size="lg")
                    stop_btn = gr.Button("⏹️ Stop", variant="stop", size="lg")
                
                gr.Markdown(
                    """
                    ### Instructions:
                    1. Click **Start Voice Chat** to begin
                    2. Speak naturally in any language
                    3. AI will respond in the same language
                    4. Click **Stop** when done
                    
                    **Tip:** Make sure your microphone is connected and permissions are granted.
                    """
                )
        
        with gr.Row():
            chat_display = gr.Textbox(
                label="Conversation History",
                lines=15,
                max_lines=20,
                interactive=False,
                placeholder="Your conversation will appear here..."
            )
        
        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh Chat", size="sm")
        
        # Button actions with chat history update
        def start_and_update():
            status = chatbot.start()
            history = chatbot.get_chat_history()
            return status, history
        
        def stop_and_update():
            status = chatbot.stop()
            history = chatbot.get_chat_history()
            return status, history
        
        start_btn.click(
            fn=start_and_update,
            outputs=[status_box, chat_display]
        )
        
        stop_btn.click(
            fn=stop_and_update,
            outputs=[status_box, chat_display]
        )
        
        # Manual refresh button
        refresh_btn = gr.Button("🔄 Refresh Chat", size="sm")
        refresh_btn.click(
            fn=chatbot.get_chat_history,
            outputs=chat_display
        )
    
    return app


def main():
    # Check if API key is available
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: Gemini API key not found.")
        print("Please set GEMINI_API_KEY environment variable.")
        return
    
    # Launch Gradio app
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )


if __name__ == "__main__":
    main()