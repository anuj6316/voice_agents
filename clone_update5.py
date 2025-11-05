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
conversation_log = []  # Store conversation in order
conversation_lock = threading.Lock()
current_question_index = -1  # Track which question we're on

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

def transcribe_audio_background(filename, question_index):
    """Background transcription (non-blocking) that maps response to correct question."""
    try:
        print(f"📝 [Background] Starting transcription for Q{question_index + 1}...")
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
            
            # Extract candidate responses
            candidate_text = []
            for item in parsed_response.get("conversation", []):
                speaker = item.get("speaker", "")
                # Look for candidate/Speaker2 responses
                if "candidate" in speaker.lower() or speaker == "Speaker2" or speaker == "Speaker1":
                    text_content = item.get('text', '')
                    if text_content:
                        candidate_text.append(text_content)
            
            # Map response to the question
            if candidate_text:
                full_response = " ".join(candidate_text)
                
                with conversation_lock:
                    if question_index < len(conversation_log):
                        conversation_log[question_index]["response"] = full_response
                        conversation_log[question_index]["response_timestamp"] = datetime.now().strftime('%H:%M:%S')
                        
                        # Save transcript immediately after mapping
                        save_formatted_transcript()
                        
                        print(f"✅ [Background] Response mapped to Q{question_index + 1}")
                    else:
                        print(f"⚠️ [Background] Invalid question index: {question_index}")
            else:
                print(f"⚠️ [Background] No candidate speech detected")
            
        except json.JSONDecodeError as e:
            print(f"⚠️ [Background] JSON parsing failed: {e}")
            
    except Exception as e:
        print(f"⚠️ [Background] Transcription failed: {e}")


def generate_response(filename, question_index):
    """Generate conversational reply (blocking until response is ready) and speak it."""
    global active_tasks, conversation_log, current_question_index
    try:
        with tasks_lock:
            active_tasks["generate_response"] = True
        
        print("🧠 Generating AI response...")
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        # Generate the next question
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Act like a interviewer who is interviewing the candidate for ai/ml intern position. You will always ask the question in english no matter what language user is speaking. Keep your responses concise and conversational.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )

        ai_reply = response.text.strip()
        print(f"\n🤖 Interviewer: {ai_reply}\n")
        
        # Add new question to conversation log
        with conversation_lock:
            current_question_index += 1
            conversation_log.append({
                "question": ai_reply,
                "question_timestamp": datetime.now().strftime('%H:%M:%S'),
                "response": None,
                "response_timestamp": None
            })
        
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

        filename, question_index = task
        transcribe_audio_background(filename, question_index)
        audio_queue.task_done()
    
    print("🔄 Background transcription worker finished")


# ========== UTILITIES ==========
def save_formatted_transcript():
    """Save conversation in a clean, readable format."""
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("INTERVIEW TRANSCRIPT\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, entry in enumerate(conversation_log, 1):
            # Write the question
            q_time = entry.get("question_timestamp", "")
            f.write(f"Q{i}. [{q_time}] INTERVIEWER:\n")
            f.write(f"{entry['question']}\n\n")
            
            # Write the response if available
            if entry.get("response"):
                r_time = entry.get("response_timestamp", "")
                f.write(f"A{i}. [{r_time}] CANDIDATE:\n")
                f.write(f"{entry['response']}\n\n")
            else:
                f.write(f"A{i}. CANDIDATE:\n")
                f.write(f"[Transcription in progress...]\n\n")
            
            f.write("-" * 80 + "\n\n")


def welcome_candidate():
    """Welcome the candidate at the start of the interview."""
    global conversation_log, current_question_index
    
    welcome_message = (
        "Hello! Welcome to your AI/ML internship interview. "
        "I'm excited to learn more about you today. "
        "Let's begin with a quick introduction. "
        "Could you please tell me about yourself and your background in AI and machine learning?"
    )
    
    print("\n" + "=" * 80)
    print("🎯 INTERVIEW STARTING")
    print("=" * 80)
    print(f"\n🤖 Interviewer: {welcome_message}\n")
    
    # Add to conversation log as first question
    with conversation_lock:
        current_question_index = 0
        conversation_log.append({
            "question": welcome_message,
            "question_timestamp": datetime.now().strftime('%H:%M:%S'),
            "response": None,
            "response_timestamp": None
        })
    
    # Speak the welcome message
    print("🔊 Playing welcome message...")
    speak_text(welcome_message)
    
    return welcome_message


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
    global is_muted, recording, stop_threads, shutdown_requested, conversation_log, current_question_index

    print("\n" + "=" * 80)
    print("🎙️  AI/ML INTERNSHIP INTERVIEW SYSTEM")
    print("=" * 80)
    print("\n📋 Instructions:")
    print("   • Type 'm' to toggle mute/unmute (pause/resume recording)")
    print("   • Type 'q' to quit the interview")
    print("   • Transcription runs in background - interview continues smoothly")
    print("   • Responses auto-map to correct questions when transcription completes")
    print("\n" + "=" * 80 + "\n")
    
    # Clear previous transcript
    if os.path.exists(TRANSCRIPT_FILE):
        os.remove(TRANSCRIPT_FILE)
    
    # Start background transcription worker
    transcription_thread = threading.Thread(target=background_transcription_worker, daemon=True)
    transcription_thread.start()
    
    # Welcome the candidate and get the initial question
    welcome_candidate()

    try:
        with sd.InputStream(channels=CHANNELS, samplerate=SAMPLE_RATE,
                            blocksize=CHUNK_SIZE, callback=audio_callback):

            is_muted = False
            print("\n🎤 Recording started... Please introduce yourself.\n")

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
                        print("🔇 Muted: Processing your response...")
                        is_muted = True

                        # Save audio
                        with lock:
                            filename = save_audio(recording)
                            recording = []

                        if filename:
                            # Get the current question index for this response
                            response_question_index = current_question_index
                            
                            # Queue transcription in background (non-blocking)
                            print(f"📤 Queued transcription for Q{response_question_index + 1} (running in background)")
                            audio_queue.put((filename, response_question_index))
                            
                            # Generate next question immediately (doesn't wait for transcription)
                            print("🧠 Generating next question (transcription continues in background)...")
                            response_text = generate_response(filename, response_question_index)

                            if response_text:
                                print("🎤 Auto-unmuted: You can answer the question now.")
                                print("💡 Your previous response is being transcribed in the background.\n")
                                with lock:
                                    recording = []
                                is_muted = False

                elif cmd == "q":
                    print("\n🛑 Ending interview. Waiting for all tasks to complete...")
                    shutdown_requested = True
                    stop_threads = True
                    
                    # Save any remaining recording
                    if not is_muted:
                        with lock:
                            filename = save_audio(recording)
                            recording = []
                        if filename and current_question_index >= 0:
                            print(f"📤 Queuing final transcription for Q{current_question_index + 1}")
                            audio_queue.put((filename, current_question_index))
                    
                    # Wait for all tasks
                    wait_for_active_tasks()
                    
                    # Save final transcript
                    with conversation_lock:
                        save_formatted_transcript()
                    print(f"\n✅ Interview completed! Transcript saved to: {TRANSCRIPT_FILE}")
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
            if filename and current_question_index >= 0:
                print(f"📤 Queuing final transcription for Q{current_question_index + 1}")
                audio_queue.put((filename, current_question_index))
        
        # Wait for all tasks to complete
        wait_for_active_tasks()
        
        # Save final transcript
        with conversation_lock:
            save_formatted_transcript()
        print(f"✅ Safe shutdown completed! Transcript saved to: {TRANSCRIPT_FILE}")
    
    finally:
        print("\n" + "=" * 80)
        print("👋 Thank you for participating in the interview!")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()