# app/api/versioning.py
from __future__ import annotations
from dataclasses import dataclass
import re

CURRENT_API_VERSION = "1.0.0"


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if not m:
            raise ValueError(f"Versión inválida: '{version}'")
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def is_compatible(plugin_min: str, plugin_max: str, current: str = CURRENT_API_VERSION) -> bool:
    """
    Verificar si la API actual es compatible con los requisitos del plugin.
    
    Política de compatibilidad:
    - MAJOR diferente: INCOMPATIBLE (breaking changes)
    - MINOR actual < plugin_min.minor: INCOMPATIBLE (features faltantes)  
    - PATCH: siempre compatible (solo bugfixes)
    
    El plugin declara: "min": "1.2.0", "max": "2.x"
    """
    c = SemVer.parse(current)
    minimum = SemVer.parse(plugin_min)

    # Verificar máximo (si es "2.x", parsear como "2.0.0")
    max_str = plugin_max.replace(".x", ".0")
    maximum = SemVer.parse(max_str)

    if c.major != minimum.major:
        return False
    if c.minor < minimum.minor:
        return False
    if c.major > maximum.major:
        return False
    return True