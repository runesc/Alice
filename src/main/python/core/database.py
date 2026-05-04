import sqlite3
from pathlib import Path

class PluginDB:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                name TEXT,
                version TEXT,
                enabled INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def get_all_plugins(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM plugins")
        return [dict(row) for row in cursor.fetchall()]

    def upsert_plugin(self, plugin_id: str, name: str, version: str, enabled: int = 1):
        self.conn.execute("""
            INSERT INTO plugins (id, name, version, enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                version=excluded.version
        """, (plugin_id, name, version, enabled))
        self.conn.commit()