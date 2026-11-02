"""Azure Speech Services Integration Module.

EE 471 Mini Project #2.
Provides Speech-to-Text (Azure SpeechRecognizer) and Text-to-Speech
(Azure SpeechSynthesizer with 'en-US-JennyNeural') capabilities.
"""

import os
import time
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

# Base directory for relative file paths
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Ensure .env is loaded safely
load_dotenv(dotenv_path=ENV_PATH)

import azure.cognitiveservices.speech as speechsdk

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_speech_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Retrieve Azure Speech API credentials from environment variables."""
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")
    return speech_key, speech_region


def get_speech_config() -> Optional[speechsdk.SpeechConfig]:
    """Create and return an Azure SpeechConfig instance with speech credentials."""
    key, region = get_speech_credentials()
    if not key or not region:
        return None
    try:
        config = speechsdk.SpeechConfig(subscription=key, region=region)
        return config
    except Exception as e:
        print(f"[Azure Speech] Error initializing SpeechConfig: {e}")
        return None


def transcribe_audio_file(audio_filepath: str) -> str:
    """Transcribes microphoned audio payload from file to text using Azure SpeechRecognizer.

    Args:
        audio_filepath: Local file path to the audio payload (wav).

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If speech credentials are missing or no speech is recognized.
        RuntimeError: If Azure Speech recognition fails or is canceled.
    """
    speech_config = get_speech_config()
    if not speech_config:
        raise ValueError("Azure Speech credentials (SPEECH_KEY, SPEECH_REGION) are missing in .env.")

    audio_config = speechsdk.audio.AudioConfig(filename=str(audio_filepath))
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Perform synchronous one-shot recognition
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text

    if result.reason == speechsdk.ResultReason.NoMatch:
        raise ValueError("No speech recognized. Please speak clearly into the microphone.")

    if result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        err_msg = f"Speech recognition canceled: {cancellation.reason}"
        if cancellation.error_details:
            err_msg += f" - {cancellation.error_details}"
        raise RuntimeError(err_msg)

    raise RuntimeError(f"Unexpected recognition result: {result.reason}")


def synthesize_speech_to_file(text: str, filename: str = "librarian_reply.wav", max_retries: int = 2) -> str:
    """Synthesizes text into a .wav file in the static directory using en-US-JennyNeural.

    Includes retry capability for transient network / rate-limit timeouts.

    Args:
        text: The text message to speak.
        filename: Destination filename within the static directory.
        max_retries: Number of retry attempts on network timeout.

    Returns:
        The web-accessible relative URL of the synthesized audio file (e.g. /static/librarian_reply.wav?t=...)

    Raises:
        ValueError: If credentials are missing or text is empty.
        RuntimeError: If speech synthesis fails after retries.
    """
    if not text or not text.strip():
        raise ValueError("Cannot synthesize empty text.")

    speech_config = get_speech_config()
    if not speech_config:
        raise ValueError("Azure Speech credentials (SPEECH_KEY, SPEECH_REGION) are missing in .env.")

    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    output_filepath = STATIC_DIR / filename
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_filepath))

    last_error = "Unknown synthesis error"
    for attempt in range(max_retries + 1):
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            timestamp = int(time.time() * 1000)
            return f"/static/{filename}?t={timestamp}"

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            last_error = f"{cancellation.reason}: {cancellation.error_details}"
            if attempt < max_retries:
                time.sleep(0.5)
                continue

    raise RuntimeError(f"Speech synthesis failed: {last_error}")
