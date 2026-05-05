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
        self.setWindowTitle("Required Permissions")
        self.setText(
            f"The plugin '{self.plugin_name}' requires permissions:")

        perm_details = "\n".join(f"• {perm}" for perm in self.dangerous_perms)
        self.setInformativeText(
            f"Requested Permissions:\n{perm_details}\n\nDo you want to continue?\n\nAccepting will allow this plugin to access to restricted features, which may involve risks. Only accept if you trust the plugin and understand why it needs these permissions.")
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)

        result = self.exec()
        self.accepted_by_user = (result == QMessageBox.Yes)
