import pyaudio
import json
import wave
import vosk
import threading
from typing import Optional
from pathlib import Path
from core.skills.loader import get_resource
from functools import wraps
import logging
import webrtcvad
import numpy as np

logger = logging.getLogger(__name__)


def ensure_initialized(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._model is None or self._recognizer is None:
            raise RuntimeError(
                f"Vosk model not initialized. Call initialize_model() before '{func.__name__}'."
            )
        return func(self, *args, **kwargs)
    return wrapper


class SpeechAPI:
    def __init__(self, lang: str, sample_rate: int = 16000):
        self._lang = lang
        self._sample_rate = sample_rate
        self._model: Optional[vosk.Model] = None
        self._recognizer: Optional[vosk.KaldiRecognizer] = None
        self._model_lock = threading.Lock()

        self._listening = False
        self._audio_stream: Optional[pyaudio.Stream] = None
        self._pa: Optional[pyaudio.PyAudio] = None
        self._vad = None

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        # Esto le dice a Pydantic: "Trátame como una instancia de mi propia clase"
        return core_schema.is_instance_schema(cls)

    def initialize_model(self, model_name: str) -> None:
        """Initialize Vosk model."""
        if self._model is not None:
            return

        model_path_obj = Path(get_resource("models/asr")) / model_name
        logger.warning(f"Attempting to load Vosk model from: {model_path_obj}")

        if not model_path_obj.exists():
            raise FileNotFoundError(f"Vosk model not found: {model_path_obj}")

        self._model = vosk.Model(str(model_path_obj))
        self._recognizer = vosk.KaldiRecognizer(self._model, self._sample_rate)
        self._vad = webrtcvad.Vad()
        self._vad.set_mode(3)  # Modo agresivo para detección de voz

    @ensure_initialized
    def recognize_from_file(self, audio_path: str) -> Optional[str]:
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}")

        with wave.open(str(audio_path), "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                raise ValueError(
                    "Audio file must be WAV format mono PCM 16kHz")

            data = wf.readframes(wf.getnframes())

        if self._recognizer.AcceptWaveform(data):
            result = json.loads(self._recognizer.Result())
            return result.get('text', '')
        else:
            result = json.loads(self._recognizer.FinalResult())
            return result.get('text', '')

    @ensure_initialized
    def recognize_in_background(self, callback):
        """
            Continuously listen to the microphone and call the callback with recognized text.

        Args:
            callback (function): A function that takes a single string argument, which is the recognized text.
        """
        if self._listening:
            return
        self._listening = True

        CHUNK_DURATION_MS = 30
        CHUNK_SIZE = int(self._sample_rate * CHUNK_DURATION_MS / 1000)
        # User silence segment in milliseconds (default 1000)
        INACTIVITY_TIME_MS = 1000
        INACTIVITY_CHUNKS = int(INACTIVITY_TIME_MS / CHUNK_DURATION_MS)
        self._is_awake = False
        self._WAKE_WORD = "prueba"

        def _listen():
            self._pa = pyaudio.PyAudio()
            self._audio_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=4000
            )

            inactive_chunks = 0

            try:
                while self._listening:
                    data = self._audio_stream.read(2000, exception_on_overflow=False)

                    # --- ESCENARIO VAD FUTURO ---
                    # Aquí es donde insertarás la lógica: if self.vad.is_speech(data):
                    """
				    Convert audio task:
				    Recived: 16-bit PCM wav format audio (buffer size = 512, samples: 1024)
				    Expected: 16-bit PCM wav format audio (buffer size = 480, samples: 960)
			        """
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    resampled_audio = np.resize(audio_array, CHUNK_SIZE)
                    converted_audio = resampled_audio.tobytes()

                    # Caso 1: Silencio (VAD negativo)
                    if not self._vad.is_speech(converted_audio, self._sample_rate):
                        inactive_chunks += 1
                        if inactive_chunks >= INACTIVITY_CHUNKS:
                            self._recognizer.Reset()
                            inactive_chunks = 0
                        continue

                    # Caso 2: Se detecta voz
                    inactive_chunks = 0
                    is_final = self._recognizer.AcceptWaveform(converted_audio)
                    res_json = json.loads(self._recognizer.Result() if is_final else self._recognizer.PartialResult())
                    text = res_json.get('text' if is_final else 'partial', '').lower()

                    if not text:
                        continue

                    # Lógica de despertar o procesar
                    if not self._is_awake and self._WAKE_WORD in text:
                        self._is_awake = True
                        logger.info("Wake word detected, starting recognition...")
                        self._recognizer.Reset()
                    elif self._is_awake:
                        callback(text)

            finally:
                self._cleanup_audio()

        threading.Thread(target=_listen, daemon=True).start()

    def stop_stream(self):
        """Detiene la escucha de forma segura."""
        self._listening = False

    def _cleanup_audio(self):
        """Cierra los recursos de hardware."""
        if self._audio_stream:
            self._audio_stream.stop_stream()
            self._audio_stream.close()
            self._audio_stream = None
        if self._pa:
            self._pa.terminate()
            self._pa = None

    def reset_recognizer(self):
        """Reinicia el reconocedor para limpiar su estado."""
        with self._model_lock:
            if self._model is not None:
                self._recognizer = vosk.KaldiRecognizer(
                    self._model, self._sample_rate)

    def cleanup(self):
        """Limpia todos los recursos."""
        self.stop_stream()
        self._cleanup_audio()
        with self._model_lock:
            self._model = None
            self._recognizer = None
