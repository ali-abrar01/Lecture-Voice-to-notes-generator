"""
utils/transcriber.py
=====================
Handles audio transcription using the ElevenLabs Speech-to-Text API.
ElevenLabs provides high-accuracy transcription, great for lecture audio.
"""

import os
import requests
from dotenv import load_dotenv    # << add this import

# load variables from .env into os.environ
load_dotenv()

# ── API Configuration ─────────────────────────────────────────────────────────
# the key is defined in .env as ELEVENLABS_API_KEY
ELEVENLABS_API_KEY = os.environ.get(
    'ELEVENLABS_API_KEY',
    'YOUR_ELEVENLABS_API_KEY_HERE'
)

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe an audio file using ElevenLabs Speech-to-Text API.

    Args:
        audio_path: Path to the local audio file (wav, mp3, webm, etc.)

    Returns:
        Transcribed text as a string, or empty string on failure.
    """

    # Check that API key is configured
    if ELEVENLABS_API_KEY == 'YOUR_ELEVENLABS_API_KEY_HERE':
        raise ValueError(
            "ElevenLabs API key not configured! "
            "Set ELEVENLABS_API_KEY environment variable or update transcriber.py"
        )

    # Check file exists
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"[Transcriber] Sending file to ElevenLabs: {audio_path}")

    # ── Send audio to ElevenLabs API ──────────────────────────────────────────
    with open(audio_path, 'rb') as audio_file:
        headers = {
            'xi-api-key': ELEVENLABS_API_KEY,
        }

        # ElevenLabs STT accepts multipart/form-data
        files = {
            'file': (os.path.basename(audio_path), audio_file, _get_mime_type(audio_path)),
        }

        data = {
            'model_id': 'scribe_v1',  # ElevenLabs' transcription model
        }

        response = requests.post(
            ELEVENLABS_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120  # Large files may take time
        )

    # ── Handle response ───────────────────────────────────────────────────────
    if response.status_code == 200:
        result = response.json()
        # ElevenLabs returns the transcript under 'text'
        transcript = result.get('text', '').strip()
        print(f"[Transcriber] Success! Got {len(transcript)} characters.")
        return transcript

    elif response.status_code == 401:
        raise ValueError("ElevenLabs API key is invalid. Check your key.")

    elif response.status_code == 422:
        raise ValueError(f"ElevenLabs rejected the file: {response.text}")

    else:
        raise RuntimeError(
            f"ElevenLabs API error {response.status_code}: {response.text}"
        )


def _get_mime_type(filepath: str) -> str:
    """Return MIME type based on file extension."""
    ext = filepath.rsplit('.', 1)[-1].lower()
    mime_map = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'webm': 'audio/webm',
        'm4a': 'audio/mp4',
        'ogg': 'audio/ogg',
        'mp4': 'video/mp4',
    }
    return mime_map.get(ext, 'audio/mpeg')