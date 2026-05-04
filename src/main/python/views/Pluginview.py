from ppg_runtime.application_context import Pydux, PPGLifeCycle, init_lifecycle
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from core.Navigable import Navigable


@init_lifecycle
class PluginView(QWidget, PPGLifeCycle, Pydux, Navigable):

    def component_will_mount(self):
        self.subscribe_to_store(self)
        self._current_plugin_id = None

    def render_(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._check_and_mount()

    def on_store_change(self, store):
        self._check_and_mount()

    def _check_and_mount(self):
        active_id = self.get_nested("active_plugin_id")

        if active_id != self._current_plugin_id:
            self._current_plugin_id = active_id
            self._mount_active_plugin()

    def _mount_active_plugin(self):
        layout = self.layout()

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if not self._current_plugin_id:
            layout.addWidget(QLabel("Ningún plugin seleccionado."))
            return

        btn_back = QPushButton("⬅ Volver al Inicio", clicked=lambda: self.navigate("Home"))

        main_app = Pydux.navigator
        plugin_instance = main_app._plugin_manager.get_instance(
            self._current_plugin_id)
        
        if not plugin_instance or not hasattr(plugin_instance, "render_"):
            layout.addWidget(
                QLabel(f"Error: El plugin '{self._current_plugin_id}' no exportó su layout."))
            layout.addWidget(btn_back)
            return

        plugin_widget = plugin_instance.render_()
        layout.addWidget(plugin_widget)
        layout.addWidget(btn_back)

