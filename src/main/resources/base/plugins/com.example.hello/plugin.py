# src/main/resources/base/plugins/com.example.hello/plugin.py
from core.skills.base import Skill
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class HelloPlugin(Skill):

    def on_load(self):
        self.context.logger.info("HelloPlugin cargado")
        self._count = self.context.local_storage.get("count", 0) or 0

    def on_enable(self):
        super().on_enable()
        # Suscribirse a eventos de otros plugins o del sistema
        self.context.events.on(
            "core.plugin.enabled",
            self._on_any_plugin_enabled
        )

    def on_disable(self):
        # Guardar estado antes de que LifecycleManager limpie eventos
        self.context.local_storage.set("count", self._count)
        super().on_disable()

    def render_(self) -> QWidget:
        """
        Llamado por PluginView cuando este plugin está activo.
        Debe retornar un QWidget nuevo cada vez que se llama.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._label = QLabel(f"Count: {self._count}")
        
        btn_inc = QPushButton("Increment")
        btn_inc.clicked.connect(self._increment)

        # Usar nav API — navegar de vuelta a Home
        btn_home = QPushButton("← Volver a Home")
        btn_home.clicked.connect(lambda: self.context.nav.go("Home"))

        layout.addWidget(QLabel(f"Plugin: {self.context.plugin_id}"))
        layout.addWidget(self._label)
        layout.addWidget(btn_inc)
        layout.addWidget(btn_home)

        return widget

    def _increment(self):
        self._count += 1
        self._label.setText(f"Count: {self._count}")
        # Persistir inmediatamente
        self.context.local_storage.set("count", self._count)
        # Notificar a otros plugins via eventos
        self.context.events.emit("count_changed", {"value": self._count})

    def _on_any_plugin_enabled(self, event: str, payload: dict):
        self.context.logger.debug(f"Otro plugin se habilitó: {payload}")