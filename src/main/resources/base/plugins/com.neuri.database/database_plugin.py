from core.skills.base import Skill
import sqlite3
from pathlib import Path

class DatabasePlugin(Skill):
    def on_load(self):
        # Inicializar base de datos
        db_path = self.context.local_storage.plugin_dir / "data.db"

        self.context.logger.info(f"DatabasePlugin: inicializando base de datos en {db_path}")

        self._conn = sqlite3.connect(db_path)
        self._conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")

        # Registrar el servicio de base de datos
        self.context.services.register("database", self)
        self.context.logger.info("DatabasePlugin: servicio 'database' registrado")

    def get_connection(self):
        """Método del servicio que otros plugins pueden usar"""
        return self._conn

    def execute_query(self, query: str, params=()):
        """Otro método del servicio"""
        cursor = self._conn.execute(query, params)
        return cursor.fetchall()

    def on_unload(self):
        if hasattr(self, '_conn'):
            self._conn.close()