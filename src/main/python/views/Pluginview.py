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

        btn_back = QPushButton("⬅ Volver al Inicio")
        btn_back.clicked.connect(lambda: self.navigate("Home"))
        layout.addWidget(btn_back)

        main_app = Pydux.navigator
        plugin_instance = main_app._plugin_manager.get_instance(
            self._current_plugin_id)

        if plugin_instance and hasattr(plugin_instance, "get_main_widget"):
            plugin_widget = plugin_instance.get_main_widget()
            layout.addWidget(plugin_widget)
        else:
            layout.addWidget(
                QLabel(f"Error: El plugin '{self._current_plugin_id}' no exportó su layout."))
