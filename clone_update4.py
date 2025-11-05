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
import json
from prompt import prompt_template
from gtts import gTTS
import pygame
import tempfile

# ====== CONFIG ======
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
TRANSCRIPT_FILE = "english_latin_spanish.txt"
# ====================

load_dotenv()

# Global state
is_muted = True
recording = []
lock = threading.Lock()
stop_threads = False
audio_queue = queue.Queue()
shutdown_requested = False
active_tasks = {"generate_response": False, "tts": False}
tasks_lock = threading.Lock()

client = genai.Client()

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# ========== TEXT-TO-SPEECH ==========

def speak_text(text):
    """Convert text to speech and play it."""
    global active_tasks
    try:
        with tasks_lock:
            active_tasks["tts"] = True
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_filename = fp.name
        
        # Generate speech
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_filename)
        
        # Play the audio
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        # Clean up
        pygame.mixer.music.unload()
        os.remove(temp_filename)
        
        print("🔊 Speech playback completed")
        
    except Exception as e:
        print(f"⚠️ Text-to-speech failed: {e}")
    finally:
        with tasks_lock:
            active_tasks["tts"] = False

# ========== GEMINI LOGIC ==========

def transcribe_audio_background(filename, ai_question):
    """Background transcription (non-blocking) with formatted output."""
    try:
        print("📝 Starting transcription...")
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt_template,
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )
        
        text = response.text.strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text.split("```json")[1].split("```")[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1].split("```")[0].strip()
            
            parsed_response = json.loads(text)
            
            # Format output
            output = f"\n{'='*60}\n"
            output += f"AI: {ai_question}\n"
            output += f"{'-'*60}\n"
            output += "CANDIDATE (transcribed):\n"
            
            # Extract candidate responses
            for item in parsed_response.get("conversation", []):
                if item.get("speaker") == "Candidate":
                    output += f"  {item.get('text', '')}\n"
            
            output += f"\nRESPONSE: {json.dumps(parsed_response.get('conversation', []), ensure_ascii=False, indent=2)}\n"
            
            # Add background notes if any
            if parsed_response.get("background_notes"):
                output += f"\nBACKGROUND RESPONSE: {json.dumps(parsed_response.get('background_notes', []), ensure_ascii=False, indent=2)}\n"
            
            output += f"{'='*60}\n"
            
            # print(output)
            append_to_log("TRANSCRIPTION", output)
            print("✅ Transcription completed")
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            print(f"Raw response: {text}")
            append_to_log("USER (transcribed - raw)", text)
            
    except Exception as e:
        print(f"⚠️ Background transcription failed: {e}")


def generate_response(filename, previous_ai_question=None):
    """Generate conversational reply (blocking until response is ready) and speak it."""
    global active_tasks
    try:
        with tasks_lock:
            active_tasks["generate_response"] = True
        
        print("🧠 Generating AI response...")
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        # We block here — this suspends program until Gemini replies
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Act like a interviewer who is interviewing the candidate for ai/ml intern position. You will always ask the question in english no matter what language user is speaking. Keep your responses concise and conversational.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )

        ai_reply = response.text.strip()
        print(f"\n🤖 Gemini: {ai_reply}\n")
        # append_to_log("GEMINI", ai_reply)
        
        # Speak the AI response
        print("🔊 Playing AI response...")
        speak_text(ai_reply)
        
        print("✅ AI response completed")
        return ai_reply
    except Exception as e:
        print(f"❌ Gemini response failed: {e}")
        return None
    finally:
        with tasks_lock:
            active_tasks["generate_response"] = False


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
    global stop_threads
    while not stop_threads:
        try:
            task = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        filename, ai_question = task
        transcribe_audio_background(filename, ai_question)
        audio_queue.task_done()
    
    print("🔄 Background transcription worker finished")


# ========== UTILITIES ==========
def append_to_log(speaker, text):
    """Append conversation text to a local file."""
    with open(TRANSCRIPT_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {speaker}:\n{text}\n")


# ========== MAIN LOOP ==========
def wait_for_active_tasks():
    """Wait for all active tasks to complete."""
    print("\n⏳ Waiting for active tasks to complete...")
    
    # Wait for active generation/TTS tasks
    while True:
        with tasks_lock:
            if not any(active_tasks.values()):
                break
        print("⏳ Tasks still running (Generate Response: {}, TTS: {})...".format(
            active_tasks["generate_response"], active_tasks["tts"]))
        time.sleep(0.5)
    
    # Wait for queue to be empty
    print("⏳ Waiting for transcription queue to empty...")
    audio_queue.join()
    print("✅ All tasks completed!")


def main():
    global is_muted, recording, stop_threads, shutdown_requested

    print("🎙️ Type 'm' to toggle mute/unmute. Type 'q' to quit.")
    print("⚠️  Note: Program will wait for all tasks to complete before exiting.\n")
    
    transcription_thread = threading.Thread(target=background_transcription_worker, daemon=True)
    transcription_thread.start()

    current_ai_question = "Initial greeting/question"

    try:
        with sd.InputStream(channels=CHANNELS, samplerate=SAMPLE_RATE,
                            blocksize=CHUNK_SIZE, callback=audio_callback):

            is_muted = False
            print("🎤 Listening... Best of luck for Your interview.")

            while True:
                if shutdown_requested:
                    # Check if we can exit
                    with tasks_lock:
                        if not any(active_tasks.values()) and audio_queue.empty():
                            break
                    print("⏳ Still waiting for tasks to complete...")
                    time.sleep(1)
                    continue

                try:
                    cmd = input("> ").strip().lower()
                except EOFError:
                    # Handle Ctrl+D
                    if not shutdown_requested:
                        print("\n⚠️  Exit requested. Waiting for tasks to complete...")
                        shutdown_requested = True
                    continue

                if cmd == "m":
                    if shutdown_requested:
                        print("⚠️  Shutdown in progress, please wait...")
                        continue
                        
                    if is_muted:
                        print("🎤 Unmuted: Ready to record again...")
                        with lock:
                            recording = []
                        is_muted = False

                    else:
                        print("🔇 Muted: Saving audio...")
                        is_muted = True

                        # Save and push to background transcription queue
                        with lock:
                            filename = save_audio(recording)
                            recording = []

                        if filename:
                            # Add filename and current AI question to queue
                            audio_queue.put((filename, current_ai_question))

                            # Suspend main thread for response
                            print("🧠 Generating response (please wait)...")
                            response_text = generate_response(filename, current_ai_question)

                            # Update current AI question for next transcription
                            if response_text:
                                current_ai_question = response_text
                                print("🎤 Auto-unmuted: You can speak again.\n")
                                with lock:
                                    recording = []
                                is_muted = False

                elif cmd == "q":
                    print("🛑 Exit requested. Waiting for all tasks to complete...")
                    shutdown_requested = True
                    stop_threads = True
                    
                    if not is_muted:
                        with lock:
                            filename = save_audio(recording)
                            recording = []
                        if filename:
                            audio_queue.put((filename, current_ai_question))
                    
                    # Wait for all tasks
                    wait_for_active_tasks()
                    break

    except KeyboardInterrupt:
        print("\n⚠️  Keyboard interrupt detected! Waiting for tasks to complete...")
        shutdown_requested = True
        stop_threads = True
        
        # Save any remaining recording
        if not is_muted:
            with lock:
                filename = save_audio(recording)
                recording = []
            if filename:
                audio_queue.put((filename, current_ai_question))
        
        # Wait for all tasks to complete
        wait_for_active_tasks()
        print("✅ Safe shutdown completed!")
    
    finally:
        print("👋 Program exited gracefully.")


if __name__ == "__main__":
    main()