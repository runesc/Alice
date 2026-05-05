import sys
import logging
from pathlib import Path
from ppg_runtime.application_context.PySide6 import ApplicationContext
from ppg_runtime.application_context import PPGLifeCycle, Pydux, init_lifecycle
from ppg_runtime.application_context.devtools.reloader import hot_reloading
from ppg_runtime.application_context.utils import app_is_frozen
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget
)
from models.screen import Activities, Activity
from views.Home import Home
from views.Auth import Auth
from views.Pluginview import PluginView
from core.Navigable import Navigable

from core.events.bus import EventBus
from core.skills.manager import PluginManager
from core.database import PluginDB

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    filename="debug.log",
    filemode="w"
)
logger = logging.getLogger(__name__)


@init_lifecycle
@hot_reloading
class Myapp(QMainWindow, PPGLifeCycle, Pydux, Navigable):
    prev_screen_idx: int = -1

    def component_will_mount(self):
        self.subscribe_to_store(self)
        self.activity_instances = {}
        Pydux.navigator = self

        data_dir = Path(self.get_resource('plugin_data'))
        self.plugin_db = PluginDB(data_dir / "plugins.sqlite3")

        self.set_schema({
            "activities": Activities,
            "plugins_loaded": bool,
            "active_plugin_count": int,
            "plugin_errors": list,
            "installed_plugins": list,
            "active_plugin_id": str | None
        })

        self.update_store({
            "activities": Activities(
                idx=0,
                screens=[
                    Activity(name="Auth", component=Auth),
                    Activity(name="Home", component=Home),
                    Activity(name="PluginView", component=PluginView)
                ]
            ),
            "plugins_loaded": False,
            "active_plugin_count": 0,
            "plugin_errors": [],
            "installed_plugins": self.plugin_db.get_all_plugins(),
            "active_plugin_id": None
        })

        self._event_bus = EventBus()

        self._plugin_manager = PluginManager(
            event_bus=self._event_bus,
            data_dir=data_dir,
            navigate_fn=lambda name: self.navigate(name),
            get_screens_fn=lambda: [
                a["name"]
                for a in self.store["activities"]["screens"]
            ],
            get_current_fn=lambda: (
                self.store["activities"]["screens"]
                [self.store["activities"]["idx"]]["name"]
            ),
        )


        for record in self._plugin_manager.discover():
            self.plugin_db.upsert_plugin(
                record.id, record.name, record.version)

        self.update_store({
            "installed_plugins": self.plugin_db.get_all_plugins()
        })

        active_count = 0
        try:
            self._plugin_manager.load_all()
            for p in self.store["installed_plugins"]:
                if p["enabled"]:
                    if self._plugin_manager.enable_plugin(p["id"]):
                        active_count += 1

            self.update_store({
                "plugins_loaded": True,
                "active_plugin_count": active_count
            })
        except Exception:
            logger.exception("Error durante la carga de plugins")
            self.update_store({"plugins_loaded": False})

        self._event_bus.subscribe(
            "core.plugin.enabled",
            self._on_plugin_enabled,
            plugin_id="core",
            priority=100,
        )
        self._event_bus.subscribe(
            "core.plugin.disabled",
            self._on_plugin_disabled,
            plugin_id="core",
            priority=100,
        )

    def render_(self):

        if hasattr(self, "stack"):
            return

        self.stack = QStackedWidget()
        activities: Activities = self.store["activities"]

        for activity in activities['screens']:
            if activity['name'] not in self.activity_instances:
                self.activity_instances[activity['name']
                                        ] = activity['component']()

            widget_instance = self.activity_instances[activity['name']]

            if self.stack.indexOf(widget_instance) == -1:
                self.stack.addWidget(widget_instance)

        self.setCentralWidget(self.stack)

        self.navigate("Auth")

    def on_store_change(self, state):
        """
        Un solo método on_store_change para manejar TODAS las reacciones de la MainWindow.
        """
        try:
            active_count = getattr(state, "active_plugin_count", 0)
            self.setWindowTitle(
                f"Myfirstapp — {active_count} plugin(s) activos")
        except AttributeError:
            pass

        if not hasattr(self, "stack"):
            return

        activities: Activities = state.model_dump()['activities']
        current_idx = activities['idx']

        if current_idx != self.prev_screen_idx:
            self.stack.setCurrentIndex(current_idx)
            self.prev_screen_idx = current_idx

    def responsive_UI(self):
        self.setMinimumSize(640, 480)

    def _on_plugin_enabled(self, event: str, payload: dict):
        """Llamado por EventBus cuando un plugin se habilita."""
        from core.skills.registry import PluginStatus
        count = len(
            self._plugin_manager.get_registry().by_status(PluginStatus.ENABLED)
        )
        self.update_store({"active_plugin_count": count})

    def _on_plugin_disabled(self, event: str, payload: dict):
        """Llamado por EventBus cuando un plugin se deshabilita."""
        self._on_plugin_enabled(event, payload)

    def reload_plugin(self, plugin_id: str):
        """Recargar un plugin sin reiniciar la app (solo en desarrollo)."""
        if not app_is_frozen():
            self._plugin_manager.disable_plugin(plugin_id)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(150, lambda: (
                self._plugin_manager.load_plugin(plugin_id),
                self._plugin_manager.enable_plugin(plugin_id),
            ))


if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Myapp()
    if not app_is_frozen():
        window._init_hot_reload_system(__file__)
    window.show()
    exec_func = getattr(appctxt.app, 'exec', appctxt.app.exec_)
    sys.exit(exec_func())
