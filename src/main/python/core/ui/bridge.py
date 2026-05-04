# app/ui/bridge.py  (versión adaptada para PPG)
from __future__ import annotations
import logging
from typing import Callable, Any
from PySide6.QtWidgets import QWidget, QDockWidget, QDialog, QTabWidget
from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtGui import QAction

logger = logging.getLogger(__name__)


class UIBridge(QObject):
    """
    UIBridge adaptado para PPG.
    
    PROBLEMA PPG ESPECÍFICO: render_() puede ser llamado múltiples veces
    por Pydux cuando el store cambia. El UIBridge rastrea qué widgets
    ya montó para NO duplicarlos en cada re-render.
    """

    def __init__(self, main_window: QObject) -> None:
        super().__init__()
        self._window = main_window
        self._plugin_slots: dict[str, list[Any]] = {}
        # Rastrear tabs por slot_id para evitar duplicados en re-render
        self._mounted_tabs: dict[str, bool] = {}

    def add_sidebar(
        self,
        plugin_id: str,
        widget_factory: Callable[[], QWidget],
        title: str,
        icon: str = "",
    ) -> str:
        slot_id = f"{plugin_id}::sidebar::{title}"
        if slot_id in self._mounted_tabs:
            return slot_id  # Ya montado, no duplicar

        try:
            widget = widget_factory()
            dock = QDockWidget(title, self._window)
            dock.setObjectName(slot_id)
            dock.setWidget(widget)
            dock.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetMovable |
                QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            self._window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
            self._register_slot(plugin_id, dock)
            self._mounted_tabs[slot_id] = True
            logger.debug(f"Sidebar '{title}' montado por plugin '{plugin_id}'")
        except Exception:
            logger.exception(f"Error montando sidebar de '{plugin_id}'")
        return slot_id

    def add_tab(
        self,
        plugin_id: str,
        widget_factory: Callable[[], QWidget],
        title: str,
    ) -> str:
        slot_id = f"{plugin_id}::tab::{title}"
        if slot_id in self._mounted_tabs:
            return slot_id  # Protección contra re-renders de PPG

        try:
            # central_tabs se crea en render_() — puede no existir aún
            # en la primera llamada si on_enable ocurre antes que render_
            tab_widget: QTabWidget = getattr(self._window, "central_tabs", None)
            if tab_widget is None:
                logger.warning(f"central_tabs aún no existe, tab '{title}' postergado")
                return slot_id

            widget = widget_factory()
            tab_widget.addTab(widget, title)
            self._register_slot(plugin_id, (tab_widget, widget))
            self._mounted_tabs[slot_id] = True
        except Exception:
            logger.exception(f"Error montando tab de '{plugin_id}'")
        return slot_id

    def add_toolbar_action(
        self,
        plugin_id: str,
        action_factory: Callable[[], QAction],
        tooltip: str,
    ) -> str:
        slot_id = f"{plugin_id}::toolbar::{tooltip}"
        if slot_id in self._mounted_tabs:
            return slot_id

        try:
            toolbar = getattr(self._window, "plugin_toolbar", None)
            if toolbar is None:
                return slot_id
            action = action_factory()
            action.setToolTip(tooltip)
            toolbar.addAction(action)
            self._register_slot(plugin_id, action)
            self._mounted_tabs[slot_id] = True
        except Exception:
            logger.exception(f"Error añadiendo toolbar action de '{plugin_id}'")
        return slot_id

    def remove_plugin_slots(self, plugin_id: str) -> None:
        for slot in self._plugin_slots.pop(plugin_id, []):
            if isinstance(slot, QDockWidget):
                self._window.removeDockWidget(slot)
                slot.deleteLater()
            elif isinstance(slot, QAction):
                tb = getattr(self._window, "plugin_toolbar", None)
                if tb:
                    tb.removeAction(slot)
            elif isinstance(slot, tuple):
                tab_widget, widget = slot
                idx = tab_widget.indexOf(widget)
                if idx >= 0:
                    tab_widget.removeTab(idx)

        # Limpiar cache de slots montados de este plugin
        to_clear = [k for k in self._mounted_tabs if k.startswith(f"{plugin_id}::")]
        for k in to_clear:
            del self._mounted_tabs[k]

    def _register_slot(self, plugin_id: str, slot: Any) -> None:
        self._plugin_slots.setdefault(plugin_id, []).append(slot)