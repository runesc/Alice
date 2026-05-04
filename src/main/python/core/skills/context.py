from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from core.skills.sandbox import PermissionGuard
    from core.events.bus import EventBus
    from core.ui.bridge import UIBridge


class UIContext:
    """Proxy con permisos para acciones UI."""

    def __init__(self, plugin_id: str, bridge: UIBridge, guard: PermissionGuard):
        self._id = plugin_id
        self._bridge = bridge
        self._guard = guard

    def register_sidebar(self, widget_factory: Callable, title: str, icon: str = "") -> str:
        self._guard.require(self._id, "ui.sidebar")
        return self._bridge.add_sidebar(self._id, widget_factory, title, icon)

    def register_tab(self, widget_factory: Callable, title: str) -> str:
        self._guard.require(self._id, "ui.tab")
        return self._bridge.add_tab(self._id, widget_factory, title)

    def register_toolbar_action(self, action_factory: Callable, tooltip: str) -> str:
        self._guard.require(self._id, "ui.toolbar")
        return self._bridge.add_toolbar_action(self._id, action_factory, tooltip)

    def show_dialog(self, dialog_factory: Callable) -> Any:
        self._guard.require(self._id, "ui.dialog")
        return self._bridge.show_plugin_dialog(self._id, dialog_factory)

    def unregister_all(self) -> None:
        """Llamado automáticamente en on_disable."""
        self._bridge.remove_plugin_slots(self._id)


class EventsContext:
    """API de eventos con namespace automático."""

    def __init__(self, plugin_id: str, bus: EventBus, guard: PermissionGuard):
        self._id = plugin_id
        self._bus = bus
        self._guard = guard

    def subscribe(self, event: str, handler: Callable, priority: int = 0) -> None:
        self._guard.require(self._id, "events.subscribe")
        self._bus.subscribe(event, handler, plugin_id=self._id, priority=priority)

    def emit(self, event: str, payload: Any = None) -> None:
        self._guard.require(self._id, "events.emit")
        namespaced = f"plugin.{self._id}.{event}"
        self._bus.emit(namespaced, payload)

    def emit_global(self, event: str, payload: Any = None) -> None:
        """Emitir a eventos del sistema (requiere permiso explícito)."""
        self._guard.require(self._id, "events.emit.global")
        self._bus.emit(event, payload)

    def unsubscribe_all(self) -> None:
        self._bus.unsubscribe_all(plugin_id=self._id)


class StorageContext:
    """Storage aislado por plugin. Nunca accede a datos de otros plugins."""

    def __init__(self, plugin_id: str, data_dir: Path, guard: PermissionGuard):
        self._id = plugin_id
        self._dir = data_dir / plugin_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._guard = guard
        self._cache: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._guard.require(self._id, "storage.write")
        import json
        path = self._dir / f"{key}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        self._cache[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        self._guard.require(self._id, "storage.read")
        if key in self._cache:
            return self._cache[key]
        import json
        path = self._dir / f"{key}.json"
        if path.exists():
            v = json.loads(path.read_text(encoding="utf-8"))
            self._cache[key] = v
            return v
        return default

    def delete(self, key: str) -> None:
        self._guard.require(self._id, "storage.write")
        path = self._dir / f"{key}.json"
        if path.exists():
            path.unlink()
        self._cache.pop(key, None)

    @property
    def plugin_dir(self) -> Path:
        """Directorio raíz de assets del plugin (solo lectura)."""
        return self._dir


class ServicesContext:
    """Acceso a servicios registrados por otros plugins (IPC seguro)."""

    def __init__(self, plugin_id: str, registry: dict, guard: PermissionGuard):
        self._id = plugin_id
        self._registry = registry
        self._guard = guard

    def get_service(self, service_id: str) -> Any:
        """Obtener un servicio público registrado por otro plugin."""
        svc = self._registry.get(service_id)
        if svc is None:
            raise KeyError(f"Service '{service_id}' not found")
        return svc["interface"]  # Solo se expone la interfaz, nunca el objeto real

    def register_service(self, service_id: str, interface: Any) -> None:
        """Publicar un servicio para que otros plugins lo consuman."""
        self._registry[service_id] = {
            "provider": self._id,
            "interface": interface,
        }


class PluginContext:
    """
    Contexto completo entregado a cada plugin.
    Encapsula toda la API del framework — los plugins nunca
    importan nada del core directamente.
    """

    def __init__(
        self,
        plugin_id: str,
        plugin_dir: Path,
        data_dir: Path,
        bus: EventBus,
        bridge: UIBridge,
        guard: PermissionGuard,
        service_registry: dict,
        api_version: str,
    ):
        self.plugin_id = plugin_id
        self.api_version = api_version

        self.ui       = UIContext(plugin_id, bridge, guard)
        self.events   = EventsContext(plugin_id, bus, guard)
        self.storage  = StorageContext(plugin_id, data_dir, guard)
        self.services = ServicesContext(plugin_id, service_registry, guard)
        self.logger   = logging.getLogger(f"plugin.{plugin_id}")

        # Paths útiles (solo lectura desde el plugin)
        self._plugin_dir = plugin_dir

    def get_asset_path(self, relative: str) -> Path:
        """Ruta segura a assets del plugin."""
        path = (self._plugin_dir / relative).resolve()
        if not str(path).startswith(str(self._plugin_dir.resolve())):
            raise PermissionError("Path traversal detectado")
        return path