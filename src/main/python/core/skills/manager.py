# app/skills/manager.py
from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from core.skills.base import PluginBase
from core.skills.context import PluginContext
from core.skills.dependency import DependencyResolver
from core.skills.lifecycle import LifecycleManager, plugin_guard
from core.skills.loader import PluginLoader, get_plugins_dir
from core.skills.manifest import ManifestLoader
from core.skills.registry import PluginRecord, PluginRegistry, PluginStatus
from core.skills.sandbox import PermissionGuard
from core.api.versioning import is_compatible, CURRENT_API_VERSION
from core.events.bus import EventBus
from core.ui.bridge import UIBridge

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Orquestador central del sistema de plugins.

    Responsabilidades:
    - Descubrir, validar y cargar plugins del filesystem
    - Mantener el registro de estado
    - Gestionar el ciclo de vida con aislamiento de errores
    - Proveer acceso a instancias para el sistema de UI (settings, marketplace)
    """

    def __init__(
        self,
        event_bus: EventBus,
        ui_bridge: UIBridge,
        data_dir: Path,
    ) -> None:
        self._bus = event_bus
        self._bridge = ui_bridge
        self._data_dir = data_dir
        self._plugins_dir = get_plugins_dir()

        self._registry = PluginRegistry()
        self._loader = PluginLoader()
        self._guard = PermissionGuard()
        self._resolver = DependencyResolver(data_dir / "cache" / "packages")
        self._lifecycle = LifecycleManager(self)
        self._manifest_loader = ManifestLoader()
        self._service_registry: dict[str, Any] = {}

        self._instances: dict[str, PluginBase] = {}

    # ------------------------------------------------------------------ #
    # Discovery                                                            #
    # ------------------------------------------------------------------ #

    def discover(self) -> list[PluginRecord]:
        """
        Escanear el directorio de plugins y registrar los válidos.
        Retorna la lista de records descubiertos (sin cargar aún).
        """
        discovered = []
        for plugin_dir in sorted(self._plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = self._manifest_loader.load(manifest_path)
                record = PluginRecord(
                    id=manifest["id"],
                    name=manifest["name"],
                    version=manifest["version"],
                    description=manifest.get("description", ""),
                    author=manifest.get("author", {}).get("name", ""),
                    plugin_dir=plugin_dir,
                    manifest=manifest,
                )
                self._registry.register(record)
                discovered.append(record)
                logger.info(
                    f"Plugin descubierto: '{record.id}' v{record.version}")
            except Exception as e:
                logger.error(f"Manifest inválido en '{plugin_dir.name}': {e}")
        return discovered

    # ------------------------------------------------------------------ #
    # Loading pipeline                                                     #
    # ------------------------------------------------------------------ #

    def load_all(self) -> None:
        """Cargar todos los plugins descubiertos en orden de dependencias."""
        from core.skills.dependency import topological_sort
        records = self._registry.all()
        ordered = topological_sort(records)

        for record in ordered:
            self.load_plugin(record.id)

    def load_plugin(self, plugin_id: str) -> bool:
        record = self._registry.get(plugin_id)
        if record is None:
            logger.error(f"Plugin '{plugin_id}' no registrado")
            return False

        # Verificar compatibilidad de API
        compat = record.manifest.get("api_compatibility", {})
        if not is_compatible(
            compat.get("min", "1.0.0"),
            compat.get("max", f"{CURRENT_API_VERSION.split('.')[0]}.x"),
        ):
            logger.error(
                f"Plugin '{plugin_id}' incompatible con API v{CURRENT_API_VERSION}"
            )
            self._registry.set_status(plugin_id, PluginStatus.INCOMPATIBLE)
            return False

        # Resolver dependencias Python
        try:
            self._resolver.ensure_dependencies(
                plugin_id,
                record.plugin_dir,
                record.manifest.get("dependencies", {}).get("python", []),
            )
        except Exception as e:
            logger.error(
                f"No se pudo resolver dependencias de '{plugin_id}': {e}")
            self._registry.set_status(plugin_id, PluginStatus.ERROR, str(e))
            return False

        # Registrar permisos
        permissions = record.manifest.get("permissions", [])
        self._guard.register_plugin(plugin_id, permissions)

        # Importar módulo
        try:
            t0 = time.monotonic()
            plugin_class = self._loader.load(
                plugin_id,
                record.plugin_dir,
                record.manifest["entrypoint"],
            )
            load_ms = (time.monotonic() - t0) * 1000
            record.load_time_ms = load_ms
        except Exception as e:
            logger.exception(f"Error importando módulo de '{plugin_id}'")
            self._registry.set_status(plugin_id, PluginStatus.ERROR, str(e))
            return False

        # Crear contexto y instanciar
        context = PluginContext(
            plugin_id=plugin_id,
            plugin_dir=record.plugin_dir,
            data_dir=self._data_dir,
            bus=self._bus,
            bridge=self._bridge,
            guard=self._guard,
            service_registry=self._service_registry,
            api_version=CURRENT_API_VERSION,
        )

        try:
            instance = plugin_class(context)
        except Exception as e:
            logger.exception(f"Error instanciando '{plugin_id}'")
            self._registry.set_status(plugin_id, PluginStatus.ERROR, str(e))
            return False

        self._instances[plugin_id] = instance
        self._registry.set_instance(plugin_id, instance)
        self._registry.set_status(plugin_id, PluginStatus.LOADED)

        # Ejecutar on_load
        success = self._lifecycle.load_plugin(plugin_id)
        if success:
            self._registry.set_status(plugin_id, PluginStatus.LOADED)
            logger.info(f"Plugin '{plugin_id}' cargado en {load_ms:.1f}ms")
        return success

    def enable_plugin(self, plugin_id: str) -> bool:
        success = self._lifecycle.enable_plugin(plugin_id)
        if success:
            self._registry.set_status(plugin_id, PluginStatus.ENABLED)
            self._bus.emit("core.plugin.enabled", {"plugin_id": plugin_id})
        return success

    def disable_plugin(self, plugin_id: str) -> None:
        self._lifecycle.disable_plugin(plugin_id)
        self._registry.set_status(plugin_id, PluginStatus.DISABLED)
        self._bus.emit("core.plugin.disabled", {"plugin_id": plugin_id})

    def get_instance(self, plugin_id: str) -> PluginBase | None:
        return self._instances.get(plugin_id)

    def get_registry(self) -> PluginRegistry:
        return self._registry
