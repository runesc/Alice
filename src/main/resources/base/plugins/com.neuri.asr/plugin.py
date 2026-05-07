from core.skills.base import Skill
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
import wave
import pyaudio
import threading
from pathlib import Path

class VoicePlugin(Skill):

    def on_load(self):
        self.context.logger.info("VoicePlugin cargado")
        self._is_recording = False
        self._filename = "recording.wav"
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._recording_thread = None
        self._frames = []

    def on_enable(self):
        self.context.speech.initialize_model("es")

    def on_disable(self):
        # Detener grabación si está activa
        if self._is_recording:
            self._stop_recording()

        # Limpiar recursos
        self.context.speech.cleanup()
        if hasattr(self, '_audio'):
            self._audio.terminate()
        super().on_disable()

    def render_(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._result_label = QLabel("Resultado: ")
        self._text_area = QTextEdit()
        self._text_area.setMaximumHeight(100)

        self._record_btn = QPushButton("🎤 Grabar")
        self._record_btn.clicked.connect(self._toggle_recording)

        self._process_btn = QPushButton("📝 Procesar Audio")
        self._process_btn.clicked.connect(self._process_audio_file)

        layout.addWidget(QLabel(f"Plugin: {self.context.plugin_id}"))
        layout.addWidget(self._record_btn)
        layout.addWidget(self._process_btn)
        layout.addWidget(self._result_label)
        layout.addWidget(self._text_area)

        return widget

    def _toggle_recording(self):
        if not self._is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self._is_recording = True
        self._record_btn.setText("⏹️ Detener")
        self._record_btn.setStyleSheet("background-color: red;")

        # Limpiar frames anteriores
        self._frames = []

        # Iniciar grabación en hilo separado
        self._recording_thread = threading.Thread(target=self._record_audio)
        self._recording_thread.daemon = True
        self._recording_thread.start()

        self.context.logger.info("Iniciando grabación...")

    def _record_audio(self):
        """Grabar audio en un hilo separado para no bloquear la UI."""
        try:
            # Configuración para Vosk: 16kHz, mono, 16-bit
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )

            while self._is_recording:
                try:
                    data = self._stream.read(1024, exception_on_overflow=False)
                    self._frames.append(data)
                except Exception as e:
                    self.context.logger.error(f"Error leyendo audio: {e}")
                    break

        except Exception as e:
            self.context.logger.error(f"Error en stream de audio: {e}")
        finally:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

    def _stop_recording(self):
        self._is_recording = False
        self._record_btn.setText("🎤 Grabar")
        self._record_btn.setStyleSheet("")

        # Esperar a que termine el hilo de grabación
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=1.0)

        # Guardar archivo WAV
        if self._frames:
            self._save_wav_file()

        # Procesar audio grabado
        audio_file = str(self.context.local_storage.plugin_dir / self._filename)
        try:
            text = self.context.speech.recognize_file(audio_file)
            self._result_label.setText(f"Reconocido: {text}")
            self._text_area.append(text)
            self.context.logger.info(f"Texto reconocido: {text}")
        except Exception as e:
            self.context.logger.error(f"Error en reconocimiento: {e}")

    def _save_wav_file(self):
        """Guardar los frames grabados como archivo WAV."""
        try:
            audio_file = self.context.local_storage.plugin_dir / self._filename

            with wave.open(str(audio_file), 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)  # 16kHz
                wf.writeframes(b''.join(self._frames))

            self.context.logger.info(f"Audio guardado en: {audio_file}")

        except Exception as e:
            self.context.logger.error(f"Error guardando archivo WAV: {e}")

    def _process_audio_file(self):
        # Ejemplo procesando un archivo existente
        audio_file = str(self.context.local_storage.plugin_dir / "test.wav")
        try:
            text = self.context.speech.recognize_file(audio_file)
            self._text_area.append(f"Archivo procesado: {text}")
        except Exception as e:
            self.context.logger.error(f"Error procesando archivo: {e}")