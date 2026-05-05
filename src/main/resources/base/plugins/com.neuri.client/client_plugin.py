from core.skills.base import Skill
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit

class ClientPlugin(Skill):
    def on_load(self):
        # Obtener el servicio de base de datos
        try:
            self.db_service = self.context.services.get("database")
            self.context.logger.warning(f"ClientPlugin: db_service = {self.db_service}")
            self.context.logger.info("ClientPlugin: servicio 'database' obtenido")
        except KeyError:
            self.context.logger.error("ClientPlugin: servicio 'database' no encontrado")
            self.db_service = None

    def render_(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Cliente de Base de Datos"))

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        btn_query = QPushButton("Consultar usuarios")
        btn_query.clicked.connect(self._query_users)
        layout.addWidget(btn_query)

        btn_insert = QPushButton("Insertar usuario")
        btn_insert.clicked.connect(self._insert_user)
        layout.addWidget(btn_insert)

        return widget

    def _query_users(self):
        self.context.logger.warning(f"ClientPlugin: db_service = {self.db_service}") # 2026-05-04 16:40:45,864 [plugin.com.neuri.client] WARNING — ClientPlugin: db_service = None

        if self.db_service:
            users = self.db_service.execute_query("SELECT * FROM users")
            self.result_text.setText(f"Usuarios: {users}")

    def _insert_user(self):
        if self.db_service:
            self.db_service.execute_query("INSERT INTO users (name) VALUES (?)", ("Test User",))
            self.db_service.get_connection().commit()
            self._query_users()