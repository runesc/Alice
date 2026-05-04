
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.skills.context import PluginContext


class PluginBase(ABC):
    """
    Clase base que todo plugin debe extender.

    Contratos de lifecycle:
      - on_install  : Una sola vez al instalar por primera vez
      - on_load     : Cada arranque. Registrar recursos, NO hacer I/O pesado
      - on_enable   : Plugin activado por el usuario. Montar UI, suscribir eventos
      - on_disable  : Plugin desactivado. Desmontar UI, liberar listeners
      - on_unload   : App cerrando o plugin siendo descargado
      - on_update   : Migración entre versiones del plugin

    REGLAS ESTRICTAS:
      - Nunca capturar excepciones del core sin re-lanzarlas
      - Nunca guardar referencias al objeto app o main_window
      - Usar siempre self.context.* para acceder a servicios
      - on_load debe completar en < 500ms
    """

    def __init__(self, context: PluginContext) -> None:
        self._context = context
        self._enabled = False

    @property
    def context(self) -> PluginContext:
        return self._context

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # --- Lifecycle hooks (todos opcionales salvo on_load) ---

    def on_install(self) -> None:
        """
        Ejecutado una sola vez al instalar el plugin.
        Ideal para: crear tablas en DB, inicializar storage, migrar datos.
        """

    @abstractmethod
    def on_load(self) -> None:
        """
        Ejecutado cada vez que la app arranca y el plugin está habilitado.
        Registrar comandos, shortcuts, providers — NO montar UI aquí.
        """

    def on_enable(self) -> None:
        """
        Plugin habilitado por el usuario.
        Montar UI (tabs, sidebars), suscribir eventos.
        """
        self._enabled = True

    def on_disable(self) -> None:
        """
        Plugin deshabilitado. Desmontar todo lo montado en on_enable.
        El EventBus limpia automáticamente listeners con el plugin_id.
        """
        self._enabled = False

    def on_unload(self) -> None:
        """
        App cerrando o plugin siendo removido.
        Guardar estado, liberar recursos externos (conexiones, threads).
        """

    def on_update(self, old_version: str, new_version: str) -> None:
        """
        Llamado cuando el plugin se actualiza de old_version a new_version.
        Correr migraciones de datos aquí.
        """
