from ppg_runtime.application_context import Pydux, PPGLifeCycle, init_lifecycle
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from core.Navigable import Navigable


@init_lifecycle
class Auth(QWidget, PPGLifeCycle, Pydux, Navigable):

    def component_will_mount(self):
        self.subscribe_to_store(self)

    def render_(self):
        layout = QVBoxLayout()

        label = QLabel("Auth Screen")
        layout.addWidget(label)

        button = QPushButton("Go to Home", clicked=lambda: self.navigate("Home"))

        layout.addWidget(button)

        self.setLayout(layout)