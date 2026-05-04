from ppg_runtime.application_context import Pydux, PPGLifeCycle, init_lifecycle
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QGridLayout
from core.Navigable import Navigable

@init_lifecycle
class Home(QWidget, PPGLifeCycle, Pydux, Navigable):

    def component_will_mount(self):
        self.subscribe_to_store(self)

    def render_(self):
        if self.layout() is not None:
            QWidget().setLayout(self.layout())

        layout = QVBoxLayout()
        layout.addWidget(QLabel("🚀 Launcher de Plugins Instalados"))

        grid = QGridLayout()
        plugins = self.get_nested("installed_plugins") or []

        # Dibujar un botón por cada plugin habilitado
        row, col = 0, 0
        for plugin in plugins:
            if plugin['enabled']:
                btn = QPushButton(f"Abrir {plugin['name']}")
                btn.clicked.connect(lambda checked=False, pid=plugin['id']: self.launch_plugin(pid))
                grid.addWidget(btn, row, col)
                col += 1
                if col > 2:
                    col = 0
                    row += 1

        layout.addLayout(grid)
        self.setLayout(layout)

    def launch_plugin(self, plugin_id: str):
        #print(f"Home: Lanzando plugin con ID {plugin_id}")
        # Setear el ID en el store global y navegar al contenedor
        self.update_store({"active_plugin_id": plugin_id})
        self.navigate("PluginView")