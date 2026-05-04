# app/skills/manifest.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

# Requiere: pip install jsonschema
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "id", "name", "version", "entrypoint", "api_compatibility"],
    "properties": {
        "schema_version": {"type": "string"},
        "id": {"type": "string", "pattern": r"^[a-z0-9]+(\.[a-z0-9\-]+)+$"},
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "entrypoint": {"type": "string", "pattern": r"^[\w\.]+:[\w]+$"},
        "permissions": {"type": "array", "items": {"type": "string"}},
        "api_compatibility": {
            "type": "object",
            "required": ["min", "max"],
            "properties": {
                "min": {"type": "string"},
                "max": {"type": "string"},
            },
        },
    },
}


class ManifestLoader:
    def load(self, path: Path) -> dict[str, Any]:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido en manifest: {e}") from e

        if HAS_JSONSCHEMA:
            try:
                jsonschema.validate(manifest, MANIFEST_SCHEMA)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Manifest no cumple schema: {e.message}") from e

        return manifest