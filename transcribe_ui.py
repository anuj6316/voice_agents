import os
import asyncio
import threading
import gradio as gr
import pyaudio
import numpy as np
from google import genai
from google.genai import types
from google.cloud import speech
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
        self.current_user_text = ""
        self.current_ai_text = ""
        self.is_user_speaking = False
        
        # Speech-to-Text client
        try:
            self.speech_client = speech.SpeechClient()
            self.use_stt = True
        except Exception as e:
            print(f"Speech-to-Text not available: {e}")
            print("Falling back to basic audio detection")
            self.use_stt = False
        
        # Configure Gemini client
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Configure the session for audio responses
        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
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
        
        # Transcription buffer
        self.transcript_buffer = []
        self.stt_queue = queue.Queue()
        
    def transcribe_audio_stream(self):
        """Transcribe audio in real-time using Google Speech-to-Text"""
        if not self.use_stt:
            return
            
        def request_generator():
            # Send initial config
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SEND_SAMPLE_RATE,
                language_code="en-US",
                alternative_language_codes=["hi-IN", "es-ES", "fr-FR", "de-DE", "zh-CN", "ja-JP"],
                enable_automatic_punctuation=True,
            )
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
            )
            
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            
            # Stream audio chunks
            while self.is_running:
                try:
                    chunk = self.stt_queue.get(timeout=0.5)
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
                except queue.Empty:
                    continue
        
        try:
            requests = request_generator()
            responses = self.speech_client.streaming_recognize(requests)
            
            for response in responses:
                if not self.is_running:
                    break
                    
                for result in response.results:
                    if result.is_final:
                        transcript = result.alternatives[0].transcript
                        self.current_user_text = transcript
                        self.transcript_buffer.append(transcript)
                    else:
                        # Interim results
                        self.current_user_text = result.alternatives[0].transcript + "..."
                        
        except Exception as e:
            print(f"Transcription error: {e}")
    
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
                
                # Check if audio has voice activity
                audio_array = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_array).mean()
                
                if volume > 300:  # Voice activity threshold
                    self.is_user_speaking = True
                    # Send to both Gemini and STT
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                    if self.use_stt:
                        self.stt_queue.put(data)
                else:
                    if self.is_user_speaking:
                        # User stopped speaking
                        self.is_user_speaking = False
                        # Save transcript if available
                        if self.transcript_buffer:
                            full_transcript = " ".join(self.transcript_buffer)
                            self.chat_history.append(("You", full_transcript))
                            self.transcript_buffer = []
                            
            except Exception as e:
                print(f"Audio input error: {e}")
                break
    
    async def receive_audio(self):
        """Receive audio and text responses from Gemini"""
        while self.is_running:
            try:
                turn = self.session.receive()
                self.current_ai_text = ""
                
                async for response in turn:
                    # Handle audio data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                    
                    # Handle text responses from AI
                    if text := response.text:
                        self.current_ai_text += text
                
                # After turn completes, save to history
                if self.current_ai_text:
                    self.chat_history.append(("AI", self.current_ai_text))
                
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
            print("Connecting to Gemini API...")
            async with self.client.aio.live.connect(model=MODEL, config=self.config) as session:
                self.session = session
                print("Connected successfully!")
                
                # Initialize queues
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                
                # Send system message
                print("Sending system message...")
                await self.session.send(input=self.system_message, end_of_turn=True)
                print("System message sent. Ready for audio input.")
                
                # Start STT in a separate thread
                if self.use_stt:
                    stt_thread = threading.Thread(target=self.transcribe_audio_stream, daemon=True)
                    stt_thread.start()
                
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
            import traceback
            traceback.print_exc()
        finally:
            if self.audio_stream:
                self.audio_stream.close()
    
    def start(self):
        """Start the chatbot"""
        if not self.is_running:
            self.is_running = True
            self.chat_history = []
            self.current_user_text = ""
            self.current_ai_text = ""
            self.transcript_buffer = []
            self.loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self.run_session())
            
            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
            
            stt_status = " with transcription" if self.use_stt else " (transcription unavailable)"
            return f"🎙️ Listening{stt_status}... Speak now!"
        return "Already running"
    
    def stop(self):
        """Stop the chatbot"""
        if self.is_running:
            self.is_running = False
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
            return "⏹️ Stopped"
        return "Not running"
    
    def get_live_status(self):
        """Get current live transcription status"""
        if self.is_user_speaking and self.current_user_text:
            return f"🎤 You're saying: {self.current_user_text}"
        elif self.current_ai_text:
            return f"🤖 AI is responding: {self.current_ai_text}"
        elif self.is_running:
            return "👂 Listening for your voice..."
        return "Ready to start"
    
    def get_chat_history(self):
        """Get formatted chat history"""
        if not self.chat_history:
            return "No conversation yet. Start speaking!"
        
        formatted = []
        for role, msg in self.chat_history:
            emoji = "🎤" if role == "You" else "🤖"
            formatted.append(f"{emoji} **{role}:** {msg}")
        
        return "\n\n".join(formatted)


# Create chatbot instance
chatbot = VoiceChatbot()


# Gradio Interface
def create_ui():
    with gr.Blocks(theme=gr.themes.Soft(), title="Voice Chatbot", css="""
        .live-box { background-color: #f0f8ff !important; border: 2px solid #4CAF50 !important; }
    """) as app:
        gr.Markdown(
            """
            # 🎙️ Voice Chatbot with Real-Time Transcription
            ### Powered by Google Gemini + Speech-to-Text
            Talk naturally and see what you're saying in real-time!
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                status_box = gr.Textbox(
                    label="📡 Connection Status",
                    value="Ready to start",
                    interactive=False,
                    lines=2
                )
                
                live_transcript = gr.Textbox(
                    label="🔴 LIVE - What's happening right now",
                    value="Not active",
                    interactive=False,
                    lines=4,
                    elem_classes="live-box"
                )
                
                with gr.Row():
                    start_btn = gr.Button("🎙️ Start Voice Chat", variant="primary", size="lg")
                    stop_btn = gr.Button("⏹️ Stop", variant="stop", size="lg")
                
                gr.Markdown(
                    """
                    ### 📋 Instructions:
                    1. **Click "Start Voice Chat"** to begin
                    2. **Speak clearly** in any language (English, Hindi, etc.)
                    3. **Watch the live box** - your words appear in real-time!
                    4. **AI responds** in the same language
                    5. **Click "Stop"** when finished
                    
                    **💡 Tips:** 
                    - Speak naturally with pauses
                    - Wait for AI to finish responding
                    - Install `google-cloud-speech` for transcription
                    
                    **⚙️ Setup for transcription:**
                    ```bash
                    pip install google-cloud-speech
                    export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
                    ```
                    """
                )
        
        with gr.Row():
            chat_display = gr.Textbox(
                label="📝 Full Conversation History",
                lines=15,
                max_lines=20,
                interactive=False,
                placeholder="Your conversation will appear here..."
            )
        
        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
            clear_btn = gr.Button("🗑️ Clear History", size="sm", variant="secondary")
        
        # Button actions
        def start_and_update():
            status = chatbot.start()
            history = chatbot.get_chat_history()
            live = chatbot.get_live_status()
            return status, history, live
        
        def stop_and_update():
            status = chatbot.stop()
            history = chatbot.get_chat_history()
            live = "Not active"
            return status, history, live
        
        def refresh_all():
            history = chatbot.get_chat_history()
            live = chatbot.get_live_status()
            return history, live
        
        def clear_history():
            chatbot.chat_history = []
            return "History cleared", "Ready to start"
        
        start_btn.click(
            fn=start_and_update,
            outputs=[status_box, chat_display, live_transcript]
        )
        
        stop_btn.click(
            fn=stop_and_update,
            outputs=[status_box, chat_display, live_transcript]
        )
        
        refresh_btn.click(
            fn=refresh_all,
            outputs=[chat_display, live_transcript]
        )
        
        clear_btn.click(
            fn=clear_history,
            outputs=[chat_display, live_transcript]
        )
        
        # Try auto-refresh
        try:
            timer = gr.Timer(value=0.5)
            timer.tick(
                fn=refresh_all,
                outputs=[chat_display, live_transcript]
            )
        except:
            pass
    
    return app


def main():
    # Check if API key is available
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: Gemini API key not found.")
        print("Please set GEMINI_API_KEY environment variable.")
        return
    
    print("\n" + "="*60)
    print("🎙️  Voice Chatbot with Real-Time Transcription")
    print("="*60)
    print("\n📝 For real-time transcription, install:")
    print("   pip install google-cloud-speech")
    print("\n🔑 And set up Google Cloud credentials:")
    print("   export GOOGLE_APPLICATION_CREDENTIALS='path/to/key.json'")
    print("\n" + "="*60 + "\n")
    
    # Launch Gradio app
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )


if __name__ == "__main__":
    main()