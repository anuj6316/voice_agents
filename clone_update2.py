import sounddevice as sd
import numpy as np
import wave
import threading
import queue
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os
import time

# ====== CONFIG ======
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
TRANSCRIPT_FILE = "conversation.txt"
# ====================

load_dotenv()

# Global state
is_muted = True
recording = []
lock = threading.Lock()
stop_threads = False
audio_queue = queue.Queue()

client = genai.Client()

# ========== GEMINI LOGIC ==========

def transcribe_audio_background(filename):
    """Background transcription (non-blocking) - runs in parallel."""
    try:
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe this user audio clearly.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )
        text = response.text.strip()
        append_to_log("USER (transcribed)", text)
        print(f"\n🗣️ [Transcription complete]: {text}")
    except Exception as e:
        print(f"\n⚠️ Background transcription failed: {e}")


def generate_response_stream(filename):
    """Generate conversational reply with streaming (blocking until complete)."""
    try:
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        # Stream the response
        response = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=[
                "Listen to the user audio and generate an appropriate, natural response.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )

        print("\n🤖 Gemini: ", end="", flush=True)
        full_response = ""
        
        for chunk in response:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                full_response += chunk.text
        
        print("\n")  # New line after complete response
        
        if full_response:
            append_to_log("GEMINI", full_response.strip())
        
        return full_response.strip() if full_response else None
        
    except Exception as e:
        print(f"\n❌ Gemini response failed: {e}")
        return None


# ========== AUDIO HANDLING ==========
def save_audio(audio_data):
    """Save audio chunks to a WAV file."""
    if len(audio_data) == 0:
        return None

    filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    audio_data = np.concatenate(audio_data, axis=0)

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

    print(f"💾 Saved: {filename}")
    return filename


def audio_callback(indata, frames, time, status):
    """Capture mic input when unmuted."""
    global recording
    if not is_muted:
        with lock:
            recording.append(indata.copy())


# ========== BACKGROUND THREAD ==========
def background_transcription_worker():
    """Handles transcription tasks from the queue asynchronously."""
    while not stop_threads:
        try:
            filename = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        transcribe_audio_background(filename)
        audio_queue.task_done()


# ========== UTILITIES ==========
def append_to_log(speaker, text):
    """Append conversation text to a local file."""
    with open(TRANSCRIPT_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {speaker}: {text}\n")


# ========== MAIN LOOP ==========
def main():
    global is_muted, recording, stop_threads

    print("🎙️ Type 'm' to toggle mute/unmute. Type 'q' to quit.")
    transcription_thread = threading.Thread(target=background_transcription_worker, daemon=True)
    transcription_thread.start()

    with sd.InputStream(channels=CHANNELS, samplerate=SAMPLE_RATE,
                        blocksize=CHUNK_SIZE, callback=audio_callback):

        is_muted = False
        print("🎤 Listening... Speak now.")

        while True:
            cmd = input("> ").strip().lower()

            if cmd == "m":
                if is_muted:
                    print("🎤 Unmuted: Ready to record again...")
                    with lock:
                        recording = []
                    is_muted = False

                else:
                    print("🔇 Muted: Saving audio...")
                    is_muted = True

                    # Save audio
                    with lock:
                        filename = save_audio(recording)
                        recording = []

                    if filename:
                        # Start background transcription (non-blocking)
                        audio_queue.put(filename)
                        print("📝 Transcription started in background...")

                        # Generate streaming response (blocking - suspends program)
                        print("🧠 Generating response (streaming)...")
                        response_text = generate_response_stream(filename)

                        # After response completes, automatically unmute
                        if response_text:
                            print("🎤 Auto-unmuted: You can speak again.\n")
                            with lock:
                                recording = []
                            is_muted = False

            elif cmd == "q":
                print("🛑 Exiting gracefully...")
                stop_threads = True
                if not is_muted:
                    filename = save_audio(recording)
                    if filename:
                        audio_queue.put(filename)
                break


if __name__ == "__main__":
    main()