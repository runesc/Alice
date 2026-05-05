# app/skills/registry.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PluginStatus(str, Enum):
    DISCOVERED  = "discovered"   # manifest leído, no cargado
    LOADED      = "loaded"       # módulo importado
    ENABLED     = "enabled"      # on_enable ejecutado, UI montada
    DISABLED    = "disabled"     # on_disable ejecutado
    ERROR       = "error"        # falló en alguna fase
    INCOMPATIBLE = "incompatible" # versión API no compatible


@dataclass
class PluginRecord:
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_dir: Path
    manifest: dict[str, Any]
    status: PluginStatus = PluginStatus.DISCOVERED
    error_message: str = ""
    instance: Any = None  # PluginBase instance
    load_time_ms: float = 0.0


class PluginRegistry:
    """
    Registro central de todos los plugins descubiertos y su estado.
    También sirve como base para un marketplace futuro.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginRecord] = {}

    def register(self, record: PluginRecord) -> None:
        self._plugins[record.id] = record

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._plugins.get(plugin_id)

    def all(self) -> list[PluginRecord]:
        return list(self._plugins.values())

    def by_status(self, status: PluginStatus) -> list[PluginRecord]:
        return [r for r in self._plugins.values() if r.status == status]

    def set_status(self, plugin_id: str, status: PluginStatus, error: str = "") -> None:
        record = self._plugins.get(plugin_id)
        if record:
            record.status = status
            record.error_message = error

    def set_instance(self, plugin_id: str, instance: Any) -> None:
        record = self._plugins.get(plugin_id)
        if record:
            record.instance = instance

    def to_dict(self) -> list[dict]:
        """Serializable para mostrar en un settings panel o API HTTP futura."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "version": r.version,
                "description": r.description,
                "author": r.author,
                "status": r.status.value,
                "error": r.error_message,
                "load_time_ms": round(r.load_time_ms, 2),
            }
            for r in self._plugins.values()
        ]
    
    def remove(self, plugin_id: str) -> None:
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]