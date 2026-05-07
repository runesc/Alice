from __future__ import annotations
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    NAV_NAVIGATE     = "nav.navigate"
    NAV_READ_SCREENS = "nav.read_screens"
    STORAGE_READ     = "storage.read"
    STORAGE_WRITE    = "storage.write"
    EVENTS_SUBSCRIBE = "events.subscribe"
    EVENTS_EMIT      = "events.emit"
    EVENTS_EMIT_GLOBAL = "events.emit.global"
    NETWORK_HTTP     = "network.http"
    NETWORK_WS       = "network.ws"
    SHELL_EXEC       = "shell.exec" #! Muy peligroso, usar con extremo cuidado, requiere validación manual del usuario
    FS_READ          = "fs.read"
    FS_WRITE         = "fs.write"
    SPEECH_MODEL_LOAD = "speech.model.load"
    SPEECH_RECOGNIZE = "speech.recognize"


# Permisos que requieren aprobación explícita del usuario (como Android)
DANGEROUS_PERMISSIONS = {
    Permission.SHELL_EXEC,
    Permission.FS_WRITE,
    Permission.NETWORK_HTTP,
    Permission.NETWORK_WS,
    Permission.EVENTS_EMIT_GLOBAL,
}


class PermissionError(Exception):
    pass


class PermissionGuard:
    """
    Verifica que un plugin tenga el permiso declarado en su manifest.
    
    Limitaciones importantes de este modelo de seguridad:
    - NO es un sandbox de OS (no usa seccomp/AppArmor)
    - Protege contra plugins INVOLUNTARIAMENTE maliciosos
    - Un plugin malintencionado que bypasee el PluginContext
      puede aún acceder a módulos de Python directamente
    - Para seguridad real, considerar subprocesos + IPC
    """

    def __init__(self) -> None:
        self._plugin_permissions: dict[str, set[str]] = {}

    def register_plugin(self, plugin_id: str, permissions: list[str]) -> None:
        self._plugin_permissions[plugin_id] = set(permissions)

    def require(self, plugin_id: str, permission: str) -> None:
        granted = self._plugin_permissions.get(plugin_id, set())
        if permission not in granted:
            msg = (
                f"Plugin '{plugin_id}' requiere permiso '{permission}' "
                f"no declarado en su manifest."
            )
            logger.error(msg)
            raise PermissionError(msg)

    def has(self, plugin_id: str, permission: str) -> bool:
        return permission in self._plugin_permissions.get(plugin_id, set())

    def get_dangerous_permissions(self, plugin_id: str) -> set[str]:
        granted = self._plugin_permissions.get(plugin_id, set())
        return {p for p in granted if p in DANGEROUS_PERMISSIONS}