from __future__ import annotations
import importlib
import importlib.metadata
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class DependencyResolver:
    """
    Resuelve dependencias Python de plugins.

    Estrategia recomendada para producción:
    1. Venv compartido para plugins (más simple, riesgo de conflictos)
    2. Un venv por plugin (máximo aislamiento, más lento y pesado)
    3. Wheels embebidos dentro del plugin (portable, sin internet)

    Esta implementación usa la opción 3 (wheels embebidos) + fallback pip,
    que es la más adecuada para apps distribuidas con PyInstaller.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def ensure_dependencies(
        self, plugin_id: str, plugin_dir: Path, requirements: list[dict]
    ) -> None:
        """
        Verificar que todas las dependencias Python del plugin estén disponibles.
        Instala las faltantes en el directorio del plugin o en el cache global.
        """
        if not requirements:
            return

        plugin_lib_dir = plugin_dir / "lib"
        plugin_lib_dir.mkdir(exist_ok=True)

        # Añadir lib/ del plugin al path ANTES de verificar
        lib_str = str(plugin_lib_dir)
        if lib_str not in sys.path:
            sys.path.insert(0, lib_str)

        for req in requirements:
            package = req["package"]
            version_spec = req.get("version", "")
            self._ensure_package(plugin_id, package,
                                 version_spec, plugin_lib_dir)

    def _ensure_package(
        self, plugin_id: str, package: str, version_spec: str, target_dir: Path
    ) -> None:
        # Verificar si ya está disponible
        try:
            dist = importlib.metadata.distribution(package)
            installed_version = dist.metadata["Version"]
            if self._version_satisfies(installed_version, version_spec):
                logger.info(
                    f"'{package}' is loaded (v{installed_version})")
                return
        except importlib.metadata.PackageNotFoundError:
            pass

        # Buscar wheel embebido dentro del plugin
        wheels_dir = target_dir.parent / "wheels"
        if wheels_dir.exists():
            wheel = self._find_wheel(wheels_dir, package)
            if wheel:
                self._install_wheel(wheel, target_dir)
                return

        # Fallback: instalar con pip en el directorio del plugin
        logger.info(
            f"Instalando '{package}{version_spec}' para plugin '{plugin_id}'")
        try:
            subprocess.check_call(
                [
                    sys.executable, "-m", "pip", "install",
                    f"{package}{version_spec}",
                    "--target", str(target_dir),
                    "--quiet",
                    "--no-deps",  # Las deps transitivas deben estar en el manifest
                ],
                timeout=60,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"No se pudo instalar '{package}' para plugin '{plugin_id}': {e}"
            ) from e

    def _find_wheel(self, wheels_dir: Path, package: str) -> Path | None:
        for whl in wheels_dir.glob("*.whl"):
            if whl.name.lower().startswith(package.lower().replace("-", "_")):
                return whl
        return None

    def _install_wheel(self, wheel: Path, target: Path) -> None:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", str(wheel),
             "--target", str(target), "--quiet"],
            timeout=30,
        )

    @staticmethod
    def _version_satisfies(installed: str, spec: str) -> bool:
        if not spec:
            return True
        from packaging.specifiers import SpecifierSet
        try:
            return installed in SpecifierSet(spec)
        except Exception:
            return True  # Si no podemos parsear, asumimos OK


def topological_sort(records: list) -> list:
    """
    Ordenar plugins por sus dependencias (DAG).
    Un plugin con dependencia D se carga DESPUÉS de D.
    """
    id_to_record = {r.id: r for r in records}
    visited: set[str] = set()
    result: list = []

    def visit(record) -> None:
        if record.id in visited:
            return
        visited.add(record.id)
        for dep in record.manifest.get("dependencies", {}).get("plugins", []):
            dep_id = dep["id"]
            if dep_id in id_to_record:
                visit(id_to_record[dep_id])
        result.append(record)

    for r in records:
        visit(r)
    return result
