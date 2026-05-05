from PySide6.QtWidgets import QMessageBox
from ppg_runtime.application_context import PPGLifeCycle, init_lifecycle


@init_lifecycle
class Dialog(QMessageBox, PPGLifeCycle):
    plugin_id = None
    plugin_name = None
    dangerous_perms = None

    def __init__(self, **kwargs):
        super().__init__()
        self.accepted_by_user = False

    def render_(self):
        self.setIcon(QMessageBox.Warning)
        self.setWindowTitle("Permisos Peligrosos")
        self.setText(
            f"El plugin '{self.plugin_name}' requiere permisos peligrosos:")

        perm_details = "\n".join(f"• {perm}" for perm in self.dangerous_perms)
        self.setInformativeText(
            f"Permisos:\n{perm_details}\n\n¿Desea continuar?")
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)

        result = self.exec()
        self.accepted_by_user = (result == QMessageBox.Yes)
