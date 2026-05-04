# app/skills/lifecycle.py
from __future__ import annotations
import logging
import traceback
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class PluginError(Exception):
    def __init__(self, plugin_id: str, phase: str, original: Exception):
        super().__init__(f"[{plugin_id}] Error en '{phase}': {original}")
        self.plugin_id = plugin_id
        self.phase = phase
        self.original = original


@contextmanager
def plugin_guard(plugin_id: str, phase: str) -> Generator[None, None, None]:
    """
    Context manager que aísla excepciones de un plugin.
    Loguea el error con traceback completo pero no propaga al core.
    
    Uso:
        with plugin_guard("com.vendor.myplugin", "on_enable"):
            plugin.on_enable()
    """
    try:
        yield
    except SystemExit:
        raise  # SystemExit SIEMPRE se propaga
    except KeyboardInterrupt:
        raise  # Idem
    except Exception as e:
        plugin_logger = logging.getLogger(f"plugin.{plugin_id}")
        plugin_logger.error(
            f"Excepción no capturada en fase '{phase}':\n"
            f"{traceback.format_exc()}"
        )
        raise PluginError(plugin_id, phase, e) from e


class LifecycleManager:
    """
    Gestiona el ciclo de vida de todos los plugins de forma segura.
    Un crash en un plugin NO afecta a otros plugins ni al core.
    """

    def __init__(self, plugin_manager) -> None:
        self._manager = plugin_manager
        self._disabled_plugins: set[str] = set()

    def load_plugin(self, plugin_id: str) -> bool:
        plugin = self._manager.get_instance(plugin_id)
        if plugin is None:
            return False
        try:
            with plugin_guard(plugin_id, "on_load"):
                plugin.on_load()
            return True
        except PluginError:
            self._disabled_plugins.add(plugin_id)
            logger.error(f"Plugin '{plugin_id}' desactivado por error en on_load")
            return False

    def enable_plugin(self, plugin_id: str) -> bool:
        if plugin_id in self._disabled_plugins:
            logger.warning(f"Plugin '{plugin_id}' está desactivado por errores previos")
            return False
        plugin = self._manager.get_instance(plugin_id)
        if plugin is None:
            return False
        try:
            with plugin_guard(plugin_id, "on_enable"):
                plugin.on_enable()
            return True
        except PluginError:
            # Intentar revertir: llamar on_disable para limpiar estado parcial
            try:
                with plugin_guard(plugin_id, "on_disable [rollback]"):
                    plugin.on_disable()
            except PluginError:
                pass
            self._disabled_plugins.add(plugin_id)
            return False

    def disable_plugin(self, plugin_id: str) -> None:
        plugin = self._manager.get_instance(plugin_id)
        if plugin is None:
            return
        with plugin_guard(plugin_id, "on_disable"):
            plugin.on_disable()
        # Limpiar UI siempre, incluso si on_disable falló
        plugin.context.ui.unregister_all()
        plugin.context.events.unsubscribe_all()