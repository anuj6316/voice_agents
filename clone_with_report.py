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

# ====== CONFIG ======
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
TRANSCRIPT_FILE = "conversation.txt"
PERFORMANCE_LOG = "performance_report.txt"
PERFORMANCE_JSON = "performance_data.json"
# ====================

load_dotenv()

# Global state
is_muted = True
recording = []
lock = threading.Lock()
stop_threads = False
audio_queue = queue.Queue()
performance_data = []
session_start_time = None

client = genai.Client()

# ========== PERFORMANCE TRACKING ==========

class PerformanceTracker:
    """Track timing for various operations."""
    
    def __init__(self):
        self.data = {
            'session_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'audio_file': None,
            'audio_save_time': 0,
            'audio_duration': 0,
            'audio_size_kb': 0,
            'transcription_start': None,
            'transcription_end': None,
            'transcription_duration': 0,
            'response_start': None,
            'response_end': None,
            'response_duration': 0,
            'response_first_chunk_time': 0,
            'response_chunk_count': 0,
            'total_processing_time': 0,
            'transcription_success': False,
            'response_success': False,
            'errors': []
        }
    
    def set_audio_info(self, filename, save_time, duration, size_kb):
        self.data['audio_file'] = filename
        self.data['audio_save_time'] = save_time
        self.data['audio_duration'] = duration
        self.data['audio_size_kb'] = size_kb
    
    def start_transcription(self):
        self.data['transcription_start'] = time.time()
    
    def end_transcription(self, success=True):
        self.data['transcription_end'] = time.time()
        self.data['transcription_duration'] = self.data['transcription_end'] - self.data['transcription_start']
        self.data['transcription_success'] = success
    
    def start_response(self):
        self.data['response_start'] = time.time()
    
    def mark_first_chunk(self):
        if self.data['response_first_chunk_time'] == 0:
            self.data['response_first_chunk_time'] = time.time() - self.data['response_start']
    
    def increment_chunk(self):
        self.data['response_chunk_count'] += 1
    
    def end_response(self, success=True):
        self.data['response_end'] = time.time()
        self.data['response_duration'] = self.data['response_end'] - self.data['response_start']
        self.data['response_success'] = success
        self.data['total_processing_time'] = max(
            self.data['transcription_duration'],
            self.data['response_duration']
        )
    
    def add_error(self, error_msg):
        self.data['errors'].append(error_msg)
    
    def get_summary(self):
        return self.data.copy()


def save_performance_report(tracker_data):
    """Save detailed performance report to files."""
    global performance_data
    performance_data.append(tracker_data)
    
    # Save JSON for machine-readable data
    with open(PERFORMANCE_JSON, 'w') as f:
        json.dump(performance_data, f, indent=2)
    
    # Generate human-readable report
    with open(PERFORMANCE_LOG, 'a') as f:
        f.write("=" * 80 + "\n")
        f.write(f"SESSION: {tracker_data['session_id']}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # Audio Information
        f.write("📁 AUDIO INFORMATION:\n")
        f.write(f"  File: {tracker_data['audio_file']}\n")
        f.write(f"  Duration: {tracker_data['audio_duration']:.2f} seconds\n")
        f.write(f"  File Size: {tracker_data['audio_size_kb']:.2f} KB\n")
        f.write(f"  Save Time: {tracker_data['audio_save_time']*1000:.2f} ms\n\n")
        
        # Transcription Performance
        f.write("📝 TRANSCRIPTION PERFORMANCE:\n")
        f.write(f"  Status: {'✓ Success' if tracker_data['transcription_success'] else '✗ Failed'}\n")
        if tracker_data['transcription_duration'] > 0:
            f.write(f"  Duration: {tracker_data['transcription_duration']:.3f} seconds\n")
            f.write(f"  Processing Speed: {tracker_data['audio_duration']/tracker_data['transcription_duration']:.2f}x realtime\n")
        f.write("\n")
        
        # Response Generation Performance
        f.write("🤖 RESPONSE GENERATION PERFORMANCE:\n")
        f.write(f"  Status: {'✓ Success' if tracker_data['response_success'] else '✗ Failed'}\n")
        if tracker_data['response_duration'] > 0:
            f.write(f"  Total Duration: {tracker_data['response_duration']:.3f} seconds\n")
            f.write(f"  Time to First Chunk: {tracker_data['response_first_chunk_time']*1000:.2f} ms\n")
            f.write(f"  Number of Chunks: {tracker_data['response_chunk_count']}\n")
            if tracker_data['response_chunk_count'] > 0:
                avg_chunk_time = tracker_data['response_duration'] / tracker_data['response_chunk_count']
                f.write(f"  Average Chunk Time: {avg_chunk_time*1000:.2f} ms\n")
        f.write("\n")
        
        # Overall Performance
        f.write("⚡ OVERALL PERFORMANCE:\n")
        f.write(f"  Total Processing Time: {tracker_data['total_processing_time']:.3f} seconds\n")
        f.write(f"  Parallel Processing: {'Yes (Transcription ran in background)' if tracker_data['transcription_success'] and tracker_data['response_success'] else 'N/A'}\n")
        
        # Efficiency Metrics
        if tracker_data['audio_duration'] > 0:
            efficiency = tracker_data['audio_duration'] / tracker_data['total_processing_time']
            f.write(f"  Processing Efficiency: {efficiency:.2f}x realtime\n")
        
        # Errors
        if tracker_data['errors']:
            f.write("\n⚠️  ERRORS:\n")
            for error in tracker_data['errors']:
                f.write(f"  - {error}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
    
    # Print summary to console
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Audio Duration: {tracker_data['audio_duration']:.2f}s")
    print(f"Transcription: {tracker_data['transcription_duration']:.2f}s")
    print(f"Response Generation: {tracker_data['response_duration']:.2f}s")
    print(f"Time to First Chunk: {tracker_data['response_first_chunk_time']*1000:.0f}ms")
    print(f"Total Processing: {tracker_data['total_processing_time']:.2f}s")
    print("=" * 60 + "\n")


# ========== GEMINI LOGIC ==========

def transcribe_audio_background(filename, tracker):
    """Background transcription (non-blocking) - runs in parallel."""
    tracker.start_transcription()
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
        tracker.end_transcription(success=True)
        append_to_log("USER (transcribed)", text)
        print(f"\n🗣️ [Transcription complete in {tracker.data['transcription_duration']:.2f}s]: {text}")
    except Exception as e:
        tracker.end_transcription(success=False)
        tracker.add_error(f"Transcription failed: {str(e)}")
        print(f"\n⚠️ Background transcription failed: {e}")


def generate_response_stream(filename, tracker):
    """Generate conversational reply with streaming (blocking until complete)."""
    tracker.start_response()
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
                tracker.mark_first_chunk()
                tracker.increment_chunk()
                print(chunk.text, end="", flush=True)
                full_response += chunk.text
        
        print("\n")  # New line after complete response
        
        tracker.end_response(success=True)
        
        if full_response:
            append_to_log("GEMINI", full_response.strip())
        
        return full_response.strip() if full_response else None
        
    except Exception as e:
        tracker.end_response(success=False)
        tracker.add_error(f"Response generation failed: {str(e)}")
        print(f"\n❌ Gemini response failed: {e}")
        return None


# ========== AUDIO HANDLING ==========
def save_audio(audio_data):
    """Save audio chunks to a WAV file and return timing info."""
    if len(audio_data) == 0:
        return None, 0, 0, 0

    start_time = time.time()
    filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    audio_data = np.concatenate(audio_data, axis=0)

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

    save_time = time.time() - start_time
    
    # Calculate audio duration and file size
    audio_duration = len(audio_data) / SAMPLE_RATE
    file_size_kb = os.path.getsize(filename) / 1024

    print(f"💾 Saved: {filename} ({file_size_kb:.2f} KB, {audio_duration:.2f}s) in {save_time*1000:.2f}ms")
    return filename, save_time, audio_duration, file_size_kb


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
            filename, tracker = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        transcribe_audio_background(filename, tracker)
        audio_queue.task_done()


# ========== UTILITIES ==========
def append_to_log(speaker, text):
    """Append conversation text to a local file."""
    with open(TRANSCRIPT_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {speaker}: {text}\n")


def generate_aggregate_report():
    """Generate aggregate statistics from all sessions."""
    if not performance_data:
        return
    
    with open(PERFORMANCE_LOG, 'a') as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write("📈 AGGREGATE STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        
        total_sessions = len(performance_data)
        successful_transcriptions = sum(1 for d in performance_data if d['transcription_success'])
        successful_responses = sum(1 for d in performance_data if d['response_success'])
        
        avg_transcription_time = np.mean([d['transcription_duration'] for d in performance_data if d['transcription_duration'] > 0])
        avg_response_time = np.mean([d['response_duration'] for d in performance_data if d['response_duration'] > 0])
        avg_first_chunk_time = np.mean([d['response_first_chunk_time'] for d in performance_data if d['response_first_chunk_time'] > 0])
        
        f.write(f"Total Sessions: {total_sessions}\n")
        f.write(f"Successful Transcriptions: {successful_transcriptions}/{total_sessions} ({successful_transcriptions/total_sessions*100:.1f}%)\n")
        f.write(f"Successful Responses: {successful_responses}/{total_sessions} ({successful_responses/total_sessions*100:.1f}%)\n\n")
        
        f.write(f"Average Transcription Time: {avg_transcription_time:.3f}s\n")
        f.write(f"Average Response Time: {avg_response_time:.3f}s\n")
        f.write(f"Average Time to First Chunk: {avg_first_chunk_time*1000:.2f}ms\n\n")
        
        f.write("=" * 80 + "\n\n")


# ========== MAIN LOOP ==========
def main():
    global is_muted, recording, stop_threads, session_start_time

    session_start_time = time.time()
    
    print("🎙️ Type 'm' to toggle mute/unmute. Type 'q' to quit.")
    print(f"📊 Performance logs will be saved to: {PERFORMANCE_LOG}")
    print(f"📊 Performance data will be saved to: {PERFORMANCE_JSON}\n")
    
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

                    # Create performance tracker for this session
                    tracker = PerformanceTracker()

                    # Save audio
                    with lock:
                        filename, save_time, duration, size_kb = save_audio(recording)
                        recording = []

                    if filename:
                        tracker.set_audio_info(filename, save_time, duration, size_kb)
                        
                        # Start background transcription (non-blocking)
                        audio_queue.put((filename, tracker))
                        print("📝 Transcription started in background...")

                        # Generate streaming response (blocking - suspends program)
                        print("🧠 Generating response (streaming)...")
                        response_text = generate_response_stream(filename, tracker)

                        # Save performance report
                        save_performance_report(tracker.get_summary())

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
                    with lock:
                        filename, save_time, duration, size_kb = save_audio(recording)
                    if filename:
                        tracker = PerformanceTracker()
                        tracker.set_audio_info(filename, save_time, duration, size_kb)
                        audio_queue.put((filename, tracker))
                
                # Generate aggregate report
                time.sleep(2)  # Wait for background tasks to complete
                generate_aggregate_report()
                print(f"\n📊 Performance reports saved to:\n  - {PERFORMANCE_LOG}\n  - {PERFORMANCE_JSON}")
                break


if __name__ == "__main__":
    main()