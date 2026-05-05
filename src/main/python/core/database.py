import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
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
                enabled INTEGER DEFAULT 0,
                permissions_approved INTEGER DEFAULT 0
            )
        """)

        try:
            self.conn.execute("ALTER TABLE plugins ADD COLUMN permissions_approved INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            logger.info("Columna 'permissions_approved' ya existe en la tabla 'plugins'.")

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

    def remove_plugin(self, plugin_id: str):
        self.conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
        self.conn.commit()

    def set_permission_approval(self, plugin_id: str, approved: bool):
        self.conn.execute('''
            UPDATE plugins SET permissions_approved = ? WHERE id = ?
        ''', (approved, plugin_id))
        self.conn.commit()

    def has_permission_approval(self, plugin_id: str) -> bool:  
        cursor = self.conn.cursor()  
        cursor.execute('''  
            SELECT permissions_approved FROM plugins WHERE id = ?  
        ''', (plugin_id,))  
        result = cursor.fetchone()  
        return result[0] if result else False
