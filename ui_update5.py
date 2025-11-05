import gradio as gr
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
SAMPLE_RATE = 16000  # Reduced for faster processing
CHANNELS = 1
CHUNK_SIZE = 1024
TRANSCRIPT_FILE = "interview_transcript.txt"
# ====================

load_dotenv()

# Global state
is_recording = False
recording = []
audio_lock = threading.Lock()
stop_threads = False
audio_queue = queue.Queue()
conversation_log = []
conversation_lock = threading.Lock()
current_question_index = -1
audio_stream = None
interview_active = False

client = genai.Client()
pygame.mixer.init()

# ========== TEXT-TO-SPEECH (OPTIMIZED) ==========
def speak_text(text):
    """Convert text to speech and play it - optimized."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_filename = fp.name
        
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_filename)
        
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.music.unload()
        os.remove(temp_filename)
        
    except Exception as e:
        print(f"TTS Error: {e}")

# ========== GEMINI LOGIC (OPTIMIZED) ==========
def transcribe_audio_background(filename, question_index):
    """Background transcription - faster parsing."""
    try:
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
        
        # Quick JSON parsing
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()
        
        try:
            parsed_response = json.loads(text)
            candidate_text = []
            
            for item in parsed_response.get("conversation", []):
                speaker = item.get("speaker", "")
                if "candidate" in speaker.lower() or speaker in ["Speaker1", "Speaker2"]:
                    text_content = item.get('text', '')
                    if text_content:
                        candidate_text.append(text_content)
            
            if candidate_text:
                full_response = " ".join(candidate_text)
                
                with conversation_lock:
                    if question_index < len(conversation_log):
                        conversation_log[question_index]["response"] = full_response
                        save_formatted_transcript()
        except:
            pass
            
    except Exception as e:
        print(f"Transcription error: {e}")
    finally:
        # Clean up audio file
        try:
            os.remove(filename)
        except:
            pass

def generate_response(filename, question_index):
    """Generate next question - optimized. Returns question text without speaking."""
    global current_question_index
    try:
        with open(filename, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Act as an interviewer for an AI/ML intern position. Ask concise, relevant questions in English. Keep responses brief and conversational.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )

        ai_reply = response.text.strip()
        
        with conversation_lock:
            current_question_index += 1
            conversation_log.append({
                "question": ai_reply,
                "response": None
            })
        
        # Return text WITHOUT speaking - speaking will happen in UI layer
        return ai_reply
    except Exception as e:
        print(f"Generation error: {e}")
        return None

# ========== AUDIO HANDLING ==========
def save_audio(audio_data):
    """Save audio chunks to WAV file."""
    if len(audio_data) == 0:
        return None

    filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    audio_data = np.concatenate(audio_data, axis=0)

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

    return filename

def audio_callback(indata, frames, time_info, status):
    """Capture mic input when recording."""
    global recording
    if is_recording:
        with audio_lock:
            recording.append(indata.copy())

# ========== BACKGROUND WORKER ==========
def background_transcription_worker():
    """Handles transcription tasks from queue."""
    global stop_threads
    while not stop_threads:
        try:
            task = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        filename, question_index = task
        transcribe_audio_background(filename, question_index)
        audio_queue.task_done()

# ========== UTILITIES ==========
def save_formatted_transcript():
    """Save conversation in readable format."""
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("AI/ML INTERVIEW TRANSCRIPT\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, entry in enumerate(conversation_log, 1):
            f.write(f"Q{i}. INTERVIEWER:\n{entry['question']}\n\n")
            
            if entry.get("response"):
                f.write(f"A{i}. CANDIDATE:\n{entry['response']}\n\n")
            else:
                f.write(f"A{i}. CANDIDATE:\n[Processing...]\n\n")
            
            f.write("-" * 60 + "\n\n")

def get_display_transcript():
    """Get formatted transcript for display."""
    with conversation_lock:
        if not conversation_log:
            return "🎤 Click 'Start Interview' to begin..."
        
        lines = []
        for i, entry in enumerate(conversation_log, 1):
            lines.append(f"### Q{i}. Interviewer:")
            lines.append(entry['question'])
            lines.append("")
            
            if entry.get("response"):
                lines.append(f"### A{i}. You:")
                lines.append(entry['response'])
            else:
                lines.append(f"### A{i}. You:")
                lines.append("*⏳ Processing your response...*")
            
            lines.append("\n---\n")
        
        return "\n".join(lines)

# ========== GRADIO FUNCTIONS ==========
def start_interview():
    """Initialize and start the interview."""
    global audio_stream, stop_threads, conversation_log, current_question_index, interview_active
    
    # Reset state
    stop_threads = False
    conversation_log = []
    current_question_index = -1
    interview_active = True
    
    # Clear old transcript
    if os.path.exists(TRANSCRIPT_FILE):
        os.remove(TRANSCRIPT_FILE)
    
    # Start background worker
    transcription_thread = threading.Thread(target=background_transcription_worker, daemon=True)
    transcription_thread.start()
    
    # Start audio stream
    audio_stream = sd.InputStream(
        channels=CHANNELS,
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        callback=audio_callback
    )
    audio_stream.start()
    
    # Get welcome message
    welcome_message = (
        "Hello! Welcome to your AI/ML internship interview. "
        "Tell me about yourself and your background in AI and machine learning."
    )
    
    with conversation_lock:
        current_question_index = 0
        conversation_log.append({
            "question": welcome_message,
            "response": None
        })
    
    # Return with text displayed - TTS will happen in .then() chain
    return (
        gr.update(visible=False),  # Start button
        gr.update(visible=True),   # Interview panel
        get_display_transcript(),
        "📝 Question displayed. Preparing audio...",
        welcome_message,  # AI question display - SHOWS FIRST
        gr.update(visible=False)   # Download panel
    )

def speak_current_question():
    """Speak the current question that's already displayed."""
    if conversation_log and current_question_index >= 0:
        speak_text(conversation_log[current_question_index]["question"])
    return "✅ Question finished. Click 'Record Answer' when ready."

def start_recording():
    """Start recording user's answer."""
    global is_recording, recording
    
    is_recording = True
    with audio_lock:
        recording = []
    
    return (
        gr.update(visible=False),  # Record button
        gr.update(visible=True),   # Stop button
        "🔴 Recording... Click 'Stop Recording' when done.",
        ""  # Clear AI question display
    )

def stop_recording():
    """Stop recording and process."""
    global is_recording, recording, current_question_index
    
    is_recording = False
    
    with audio_lock:
        filename = save_audio(recording)
        recording = []
    
    next_question = ""
    
    if filename:
        response_question_index = current_question_index
        
        # Queue transcription
        audio_queue.put((filename, response_question_index))
        
        # Generate next question (text only, no TTS yet)
        next_question = generate_response(filename, response_question_index)
        if not next_question:
            next_question = ""
    
    return (
        gr.update(visible=True),   # Record button
        gr.update(visible=False),  # Stop button
        get_display_transcript(),
        "📝 Next question displayed. Preparing audio..." if next_question else "⏳ Processing...",
        next_question  # Show AI's next question - DISPLAYS FIRST
    )

def speak_next_question():
    """Speak the next question after it's displayed."""
    if conversation_log and current_question_index >= 0:
        speak_text(conversation_log[current_question_index]["question"])
    return "✅ Question finished. Click 'Record Answer' when ready."

def end_interview():
    """End the interview."""
    global is_recording, recording, stop_threads, audio_stream, interview_active
    
    interview_active = False
    is_recording = False
    
    # Save final recording if any
    if len(recording) > 0:
        with audio_lock:
            filename = save_audio(recording)
            recording = []
        if filename and current_question_index >= 0:
            audio_queue.put((filename, current_question_index))
    
    # Stop threads
    stop_threads = True
    
    # Wait for completion
    time.sleep(1)
    audio_queue.join()
    
    # Save final transcript
    with conversation_lock:
        save_formatted_transcript()
    
    # Stop audio stream
    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
    
    return (
        gr.update(visible=True),   # Start button
        gr.update(visible=False),  # Interview panel
        get_display_transcript(),
        f"✅ Interview completed! Transcript saved to {TRANSCRIPT_FILE}",
        "",  # Clear AI question box
        gr.update(visible=True),  # Download panel
        TRANSCRIPT_FILE  # Set file for download
    )

def update_display():
    """Auto-update display."""
    if interview_active:
        return get_display_transcript(), "🎤 Ready to record your answer."
    return gr.update(), gr.update()

# ========== GRADIO UI ==========
def create_interface():
    with gr.Blocks(title="AI Interview", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎙️ AI/ML Internship Interview
        ### An intelligent interview system powered by Gemini AI
        """)
        
        # Start panel
        with gr.Column(visible=True) as start_panel:
            gr.Markdown("""
            ### 📋 Instructions:
            1. Click **Start Interview** to begin
            2. Listen to the question
            3. Click **Record Answer** and speak your response
            4. Click **Stop Recording** when finished
            5. Wait for the next question
            6. Click **End Interview** when done
            """)
            start_btn = gr.Button("🚀 Start Interview", variant="primary", size="lg", scale=2)
        
        # Interview panel
        with gr.Column(visible=False) as interview_panel:
            # AI Question Display Box
            ai_question_box = gr.Textbox(
                label="🤖 AI Interviewer is asking:",
                value="",
                interactive=False,
                lines=3,
                max_lines=5
            )
            
            status_box = gr.Textbox(
                label="Status",
                value="Ready...",
                interactive=False,
                lines=2
            )
            
            with gr.Row():
                record_btn = gr.Button("🎤 Record Answer", variant="primary", size="lg", visible=True)
                stop_btn = gr.Button("⏹️ Stop Recording", variant="stop", size="lg", visible=False)
                refresh_btn = gr.Button("🔄 Refresh", size="sm")
            
            end_btn = gr.Button("🛑 End Interview", variant="secondary", size="sm")
            
            transcript_box = gr.Markdown(
                value="Transcript will appear here...",
                label="Interview Transcript"
            )
        
        # Download panel
        with gr.Column(visible=False) as download_panel:
            gr.Markdown("### ✅ Interview Complete!")
            gr.Markdown("You can download your interview transcript below:")
            download_file = gr.File(label="📄 Download Transcript", value=None)
            restart_btn = gr.Button("🔄 Start New Interview", variant="primary")
        
        # Button actions
        start_btn.click(
            start_interview,
            outputs=[start_panel, interview_panel, transcript_box, status_box, ai_question_box, download_panel]
        ).then(
            # FIRST: Display text, THEN: Speak it
            fn=speak_current_question,
            outputs=[status_box]
        )
        
        record_btn.click(
            start_recording,
            outputs=[record_btn, stop_btn, status_box, ai_question_box]
        )
        
        stop_btn.click(
            stop_recording,
            outputs=[record_btn, stop_btn, transcript_box, status_box, ai_question_box]
        ).then(
            # FIRST: Display next question, THEN: Speak it
            fn=speak_next_question,
            outputs=[status_box]
        )
        
        end_btn.click(
            end_interview,
            outputs=[start_panel, interview_panel, transcript_box, status_box, ai_question_box, download_panel, download_file]
        )
        
        restart_btn.click(
            lambda: (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)),
            outputs=[start_panel, interview_panel, download_panel]
        )
        
        refresh_btn.click(
            update_display,
            outputs=[transcript_box, status_box]
        )
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True, server_name="0.0.0.0", server_port=7860)