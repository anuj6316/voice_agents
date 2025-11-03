import os
import io
import torch
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from silero_vad import VADIterator

# Load environment variables
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Load Silero VAD model
model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
vad_iterator = VADIterator(model)

# Audio settings
SAMPLE_RATE = 16000
BLOCK_SIZE = int(SAMPLE_RATE * 0.25)  # 0.25s chunks

def transcribe_audio_bytes(audio_bytes: bytes):
    """Send captured audio to Google Gemini for transcription"""
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[types.Part.from_bytes(audio_bytes, mime_type="audio/wav")]
    )
    return response.text

def listen_and_transcribe():
    """Continuously listen, detect speech, and transcribe"""
    print("🎙️ Speak into your microphone (Ctrl+C to exit)...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        audio_buffer = []
        speaking = False

        while True:
            # Read audio from mic
            chunk, _ = stream.read(BLOCK_SIZE)
            chunk = torch.from_numpy(chunk.squeeze())

            # Run through VAD
            speech_dict = vad_iterator(chunk, SAMPLE_RATE)

            if vad_iterator.triggered:
                speaking = True
                audio_buffer.append(chunk)
            elif speaking:
                # Speech just ended — process it
                print("🤫 Silence detected. Processing...")

                speech_tensor = torch.cat(audio_buffer)
                vad_iterator.reset_states()
                speaking = False
                audio_buffer = []

                # Save as WAV bytes
                buf = io.BytesIO()
                sf.write(buf, speech_tensor.numpy(), SAMPLE_RATE, format="WAV")
                buf.seek(0)

                # Transcribe
                try:
                    text = transcribe_audio_bytes(buf.read())
                    print(f"🧑 You said: {text}\n")
                except Exception as e:
                    print(f"⚠️ Transcription error: {e}")

if __name__ == "__main__":
    listen_and_transcribe()
import os
import io
import torch
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from silero_vad import VADIterator

# Load environment variables
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Load Silero VAD model
model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False
)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
vad_iterator = VADIterator(model)

# Audio settings
SAMPLE_RATE = 16000
BLOCK_SIZE = int(SAMPLE_RATE * 0.25)  # 0.25s chunks

def transcribe_audio_bytes(audio_bytes: bytes):
    """Send captured audio to Google Gemini for transcription"""
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[types.Part.from_bytes(audio_bytes, mime_type="audio/wav")]
    )
    return response.text

def listen_and_transcribe():
    """Continuously listen, detect speech, and transcribe (safe 512-sample version)"""
    print("🎙️ Speak into your microphone (Ctrl+C to exit)...")

    import numpy as np
    ring_buffer = np.zeros(0, dtype=np.float32)
    speaking = False
    audio_buffer = []

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            # Read mic data (variable chunk size)
            audio_chunk, _ = stream.read(1024)
            audio_chunk = audio_chunk.squeeze()

            # Append to ring buffer
            ring_buffer = np.concatenate((ring_buffer, audio_chunk))

            # Process in exact 512-sample frames
            while len(ring_buffer) >= 512:
                frame = ring_buffer[:512]
                ring_buffer = ring_buffer[512:]

                frame_torch = torch.from_numpy(frame)

                # Feed into Silero-VAD
                speech_dict = vad_iterator(frame_torch, SAMPLE_RATE)

                if vad_iterator.triggered:
                    if not speaking:
                        print("🗣️ Speech started...")
                        speaking = True
                    audio_buffer.append(frame_torch)

                elif speaking:
                    # Speech just ended
                    print("🤫 Silence detected. Processing...")

                    speech_tensor = torch.cat(audio_buffer)
                    vad_iterator.reset_states()
                    speaking = False
                    audio_buffer = []

                    # Save as WAV bytes
                    buf = io.BytesIO()
                    sf.write(buf, speech_tensor.numpy(), SAMPLE_RATE, format="WAV")
                    buf.seek(0)

                    # Transcribe
                    try:
                        text = transcribe_audio_bytes(buf.read())
                        print(f"🧑 You said: {text}\n")
                    except Exception as e:
                        print(f"⚠️ Transcription error: {e}")

if __name__ == "__main__":
    listen_and_transcribe()
