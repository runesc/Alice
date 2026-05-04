# app/skills/loader.py
from __future__ import annotations
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from ppg_runtime.application_context.utils import app_is_frozen as is_frozen
from ppg_runtime import _frozen, _source
from ppg_runtime._resources import ResourceLocator


logger = logging.getLogger(__name__)


def _project_dir():
    assert not is_frozen(), 'Only available when running from source'
    return _source.get_project_dir()


def _resource_locator():
    if is_frozen():
        resource_dirs = _frozen.get_resource_dirs()
    else:
        resource_dirs = _source.get_resource_dirs(_project_dir())
    return ResourceLocator(resource_dirs)


def get_resource(*rel_path):
    """
    Return the absolute path to the data file with the given name or
    (relative) path. When running from source, searches src/main/resources.
    Otherwise, searches your app's installation directory. If no file with
    the given name or path exists, a FileNotFoundError is raised.
    """
    return _resource_locator().locate(*rel_path)


def get_plugins_dir() -> Path:
    """
    Obtener el directorio de plugins correctamente tanto en desarrollo
    como en el ejecutable frozen por PyInstaller.

    PyInstaller expone sys.frozen = True y sys._MEIPASS cuando el ejecutable
    está corriendo. Los plugins NO van dentro del bundle — viven fuera,
    en el sistema de archivos del usuario.
    """
    return Path(get_resource('plugins'))


def get_meipass_resource(relative_path: str) -> Path:
    """
    Acceder a un recurso empaquetado DENTRO del bundle PyInstaller.
    Usar para recursos del core (iconos, templates del sistema).
    Los plugins tienen sus propios paths y NO usan esta función.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent
    return base / relative_path


class PluginLoader:
    """
    Carga módulos de plugins usando importlib de forma aislada.

    Cada plugin se carga con su propio spec y se agrega al sys.modules
    con un nombre namespaced para evitar colisiones.
    """

    def __init__(self) -> None:
        self._loaded: dict[str, ModuleType] = {}

    def load(self, plugin_id: str, plugin_dir: Path, entrypoint: str) -> type:
        """
        Cargar un plugin y retornar la clase de entrada.

        entrypoint: "module:ClassName" (ej: "plugin:MyPlugin")
        """
        module_name, class_name = entrypoint.split(":")
        namespace = f"_plugin_{plugin_id.replace('.', '_')}.{module_name}"

        # Si ya está cargado (hot reload: primero hacer unload)
        if namespace in sys.modules:
            logger.debug(f"Plugin '{plugin_id}' ya cargado en sys.modules")
            module = sys.modules[namespace]
            return getattr(module, class_name)

        module_path = plugin_dir / f"{module_name}.py"
        if not module_path.exists():
            # Intentar como paquete
            module_path = plugin_dir / module_name / "__init__.py"
        if not module_path.exists():
            raise ImportError(
                f"No se encontró '{module_name}' en '{plugin_dir}'")

        # Agregar el directorio del plugin al sys.path TEMPORALMENTE
        # para que el plugin pueda importar sus submódulos relativos
        plugin_dir_str = str(plugin_dir)
        path_added = plugin_dir_str not in sys.path
        if path_added:
            sys.path.insert(0, plugin_dir_str)

        try:
            spec = importlib.util.spec_from_file_location(
                namespace, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(
                    f"No se pudo crear spec para '{module_path}'")

            module = importlib.util.module_from_spec(spec)
            # Registrar ANTES de exec (evita import circular)
            sys.modules[namespace] = module

            spec.loader.exec_module(module)  # type: ignore[union-attr]

        except Exception:
            sys.modules.pop(namespace, None)
            raise
        finally:
            if path_added and plugin_dir_str in sys.path:
                sys.path.remove(plugin_dir_str)

        self._loaded[plugin_id] = module

        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            raise AttributeError(
                f"Clase '{class_name}' no encontrada en módulo '{module_name}'"
            )
        return plugin_class

    def unload(self, plugin_id: str) -> None:
        """
        Remover el módulo de sys.modules para permitir hot reload.

        WARNING: Referencias antiguas al módulo siguen vivas en memoria.
        El GC eventualmente las liberará, pero no es instantáneo.
        """
        module = self._loaded.pop(plugin_id, None)
        if module is None:
            return

        # Eliminar el módulo y todos sus submódulos
        prefix = module.__name__
        to_remove = [k for k in sys.modules if k ==
                     prefix or k.startswith(prefix + ".")]
        for key in to_remove:
            del sys.modules[key]
        logger.debug(
            f"Plugin '{plugin_id}' descargado de sys.modules ({len(to_remove)} módulos)")
