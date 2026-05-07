from ppg_runtime.application_context import Pydux, PPGLifeCycle, init_lifecycle
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QGridLayout
from core.Navigable import Navigable
from core.AIKit.asr import SpeechAPI
import logging

logger = logging.getLogger(__name__)

@init_lifecycle
class Home(QWidget, PPGLifeCycle, Pydux, Navigable):

    def component_will_mount(self):
        self.subscribe_to_store(self)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                elif item.layout() is not None:
                    self.clear_layout(item.layout())

    def render_(self):
        if self.layout() is not None:
            self.clear_layout(self.layout())
            layout = self.layout()
        else:
            layout = QVBoxLayout()
            self.setLayout(layout)

        layout.addWidget(QLabel("🚀 Launcher de Plugins Instalados"))

        grid = QGridLayout()
        plugins = self.get_nested("installed_plugins") or []

        row, col = 0, 0
        for plugin in plugins:
            if plugin['enabled']:
                btn = QPushButton(f"Abrir {plugin['name']}")
                # Usar default argument en lambda para capturar el valor actual de pid
                btn.clicked.connect(lambda checked=False, pid=plugin['id']: self.launch_plugin(pid))
                grid.addWidget(btn, row, col)
                col += 1
                if col > 2:
                    col = 0
                    row += 1

        layout.addLayout(grid)

        asr_ready = self.store.get("asr_ready", False)
        is_listening = self.store.get("is_listening", False)
        
        btn_text = "🛑 Detener" if is_listening else "🎙️ Escuchar"
        if not asr_ready: btn_text = "Cargando ASR..."

        btn_mic = QPushButton(btn_text)
        btn_mic.setEnabled(asr_ready)
        btn_mic.clicked.connect(self.toggle_voice)
        
        layout.addWidget(btn_mic)

    def toggle_voice(self):
        import threading # Asegúrate de tener el import
        ctx: SpeechAPI = self.store.get("speech_api") 
        currently_listening = self.store.get("is_listening", False)

        if not ctx:
            logger.error("No se encontró SpeechAPI en el Store")
            return

        if currently_listening:
            ctx.stop_stream()
            self.update_store({"is_listening": False})
        else:
            # 1. Actualizamos el estado primero
            self.update_store({"is_listening": True})
            
            # 2. Ejecutamos el reconocimiento en un hilo separado
            # para NO bloquear el renderizado del botón "Detener"
            threading.Thread(
                target=ctx.recognize_stream, 
                kwargs={'callback': self.on_speech_recognized},
                daemon=True
            ).start()

    def on_speech_recognized(self, text):
        print(f"Escuché: {text}")

    def launch_plugin(self, plugin_id: str):
        self.update_store({"active_plugin_id": plugin_id})
        self.navigate("PluginView")