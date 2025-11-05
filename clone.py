import sounddevice as sd
import numpy as np
import wave
import threading
from datetime import datetime
 
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
 
is_muted = False
recording = []
lock = threading.Lock()
 
# transcribing audio with gemini
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
load_dotenv()
def transcribe_audio(filename):
    with open(filename, 'rb') as f:
        audio_bytes = f.read()

    client = genai.Client()
    response = client.models.generate_content(
      model='gemini-2.5-flash',
      contents=[
        'Describe this audio clip',
        types.Part.from_bytes(
          data=audio_bytes,
          mime_type='audio/wav',
        )
      ]
    )

    print(response.text)
def generating_response(filename):
    with open(filename, 'rb') as f:
        audio_bytes = f.read()

    client = genai.Client()
    response = client.models.generate_content(
      model='gemini-2.5-flash',
      contents=[
        'generate appropriate response for the given audio',
        types.Part.from_bytes(
          data=audio_bytes,
          mime_type='audio/wav',
        )
      ]
    )

    print(response.text)
 
def save_audio(audio_data):
    if len(audio_data) == 0:
        return
    filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    audio_data = np.concatenate(audio_data, axis=0)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    t1 = datetime.now()
    transcribe_audio(filename)
    t2 = datetime.now()
    print(f"💾 Saved: {filename}\nResponse Time: {t2-t1}")

 
 
def audio_callback(indata, frames, time, status):
    global recording, is_muted
    if not is_muted:
        with lock:
            recording.append(indata.copy())
 
 
def main():
    global is_muted, recording
    print("🎙️ Type 'm' to toggle mute/unmute. Type 'q' to quit.")
    with sd.InputStream(channels=CHANNELS, samplerate=SAMPLE_RATE,
                        blocksize=CHUNK_SIZE, callback=audio_callback):
        while True:
            cmd = input("> ").strip().lower()
            if cmd == 'm':
                if is_muted:
                    print("🎤 unmuted: Recording started...")
                    with lock:
                        recording = []
                    is_muted = False
                else:
                    print("🔇 Muted: Saving audio...")
                    is_muted = True
                    with lock:
                        save_audio(recording)
                        recording = []
            elif cmd == 'q':
                print("🛑 Exiting...")
                if not is_muted:
                    save_audio(recording)
                break
 
 
if __name__ == "__main__":
    main()
 
 