from __future__ import annotations
import logging
import json
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from core.skills.sandbox import PermissionGuard
    from core.events.bus import EventBus

class NavAPI:
    """
    Permite al plugin navegar entre pantallas de Alice.
    No recibe la instancia de Myapp — solo callables.
    
    Uso en plugin:
        self.context.nav.go("Home")
        screens = self.context.nav.screens()
    """

    def __init__(
        self,
        plugin_id: str,
        guard: PermissionGuard,
        navigate_fn: Callable[[str], None],
        get_screens_fn: Callable[[], list[str]],
        get_current_fn: Callable[[], str],
    ) -> None:
        self._id = plugin_id
        self._guard = guard
        self._navigate = navigate_fn
        self._get_screens = get_screens_fn
        self._get_current = get_current_fn

    def go(self, screen_name: str) -> None:
        """Navegar a una pantalla registrada."""
        self._guard.require(self._id, "nav.navigate")
        self._navigate(screen_name)

    def screens(self) -> list[str]:
        """Lista de pantallas disponibles."""
        self._guard.require(self._id, "nav.read_screens")
        return self._get_screens()

    def current(self) -> str:
        """Nombre de la pantalla activa."""
        self._guard.require(self._id, "nav.read_screens")
        return self._get_current()

class EventsContext:
    """API de eventos con namespace automático por plugin."""

    def __init__(self, plugin_id: str, bus: EventBus, guard: PermissionGuard):
        self._id = plugin_id
        self._bus = bus
        self._guard = guard

    def subscribe(self, event: str, handler: Callable, priority: int = 0) -> None:
        self._guard.require(self._id, "events.subscribe")
        self._bus.subscribe(event, handler, plugin_id=self._id, priority=priority)

    def emit(self, event: str, payload: Any = None) -> None:
        """Emite con namespace automático: plugin.{id}.{event}"""
        self._guard.require(self._id, "events.emit")
        self._bus.emit(f"plugin.{self._id}.{event}", payload)

    def emit_global(self, event: str, payload: Any = None) -> None:
        """Emitir evento global del sistema (permiso explícito requerido)."""
        self._guard.require(self._id, "events.emit.global")
        self._bus.emit(event, payload)

    def on(self, event: str, handler: Callable, priority: int = 0) -> None:
        """Alias de subscribe, más idiomático para plugins."""
        self.subscribe(event, handler, priority)

    def once(self, event: str, handler: Callable) -> None:
        """Suscribirse a un evento una sola vez."""
        self._guard.require(self._id, "events.subscribe")
        self._bus.once(event, handler, plugin_id=self._id)

    def unsubscribe_all(self) -> None:
        """Llamado automáticamente en on_disable por LifecycleManager."""
        self._bus.unsubscribe_all(plugin_id=self._id)

class StorageContext:
    """
    Persistencia en disco aislada por plugin.
    Cada plugin tiene su propio directorio: plugin_data/{plugin_id}/
    """

    def __init__(self, plugin_id: str, data_dir: Path, guard: PermissionGuard):
        self._id = plugin_id
        self._dir = data_dir / plugin_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._guard = guard
        self._cache: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._guard.require(self._id, "storage.write")
        if ".." in key or "/" in key or "\\" in key:
            raise ValueError(f"Clave inválida: '{key}'")
        path = self._dir / f"{key}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        self._cache[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        self._guard.require(self._id, "storage.read")
        if key in self._cache:
            return self._cache[key]
        path = self._dir / f"{key}.json"
        if path.exists():
            val = json.loads(path.read_text(encoding="utf-8"))
            self._cache[key] = val
            return val
        return default

    def delete(self, key: str) -> None:
        self._guard.require(self._id, "storage.write")
        path = self._dir / f"{key}.json"
        if path.exists():
            path.unlink()
        self._cache.pop(key, None)

    def keys(self) -> list[str]:
        self._guard.require(self._id, "storage.read")
        return [p.stem for p in self._dir.glob("*.json")]

    @property
    def plugin_dir(self) -> Path:
        """Directorio raíz del plugin (assets, etc.)."""
        return self._dir


class ServicesContext:
    """Acceso a servicios registrados por otros plugins (IPC seguro)."""
    """Registro de servicios públicos entre plugins."""

    def __init__(self, plugin_id: str, registry: dict, guard: PermissionGuard):
        self._id = plugin_id
        self._registry = registry
        self._guard = guard

    def get(self, service_id: str) -> Any:
        """Consumir un servicio publicado por otro plugin."""
        svc = self._registry.get(service_id)
        if svc is None:
            raise KeyError(f"Servicio '{service_id}' no encontrado.")
        return svc["interface"]

    def register(self, service_id: str, interface: Any) -> None:
        """Publicar un servicio para otros plugins."""
        self._registry[service_id] = {
            "provider": self._id,
            "interface": interface,
        }


class PluginContext:
    """
    Objeto único entregado a cada plugin en su constructor.
    
    APIs disponibles:
        context.nav            → navegar entre pantallas de Alice
        context.events         → suscribirse y emitir eventos
        context.local_storage  → persistencia en disco aislada
        context.services       → IPC con otros plugins
        context.logger         → logging con nombre del plugin
        context.get_asset(p)   → ruta segura a assets del plugin
    
    CONTRATO: los plugins nunca importan nada de core.* directamente.
    """

    def __init__(
        self,
        plugin_id: str,
        plugin_dir: Path,
        data_dir: Path,
        bus: EventBus,
        guard: PermissionGuard,
        service_registry: dict,
        api_version: str,
        # Callables del core — no referencias a objetos reales
        navigate_fn: Callable[[str], None],
        get_screens_fn: Callable[[], list[str]],
        get_current_fn: Callable[[], str],
    ):
        self.plugin_id   = plugin_id
        self.api_version = api_version
        self.logger      = logging.getLogger(f"plugin.{plugin_id}")

        self._plugin_dir = plugin_dir

        self.nav           = NavAPI(plugin_id, guard, navigate_fn, get_screens_fn, get_current_fn)
        self.events        = EventsContext(plugin_id, bus, guard)
        self.local_storage = StorageContext(plugin_id, data_dir, guard)
        self.services      = ServicesContext(plugin_id, service_registry, guard)

    def get_asset(self, relative: str) -> Path:
        """Ruta segura a un asset del plugin. Previene path traversal."""
        resolved = (self._plugin_dir / relative).resolve()
        if not str(resolved).startswith(str(self._plugin_dir.resolve())):
            raise PermissionError("Path traversal detectado.")
        return resolved
