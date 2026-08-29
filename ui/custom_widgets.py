# ui/custom_widgets.py

from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtCore import Qt

class NoScrollComboBox(QComboBox):
    """
    Une QComboBox personnalisée qui ignore les événements de la molette
    tout en restant utilisable au clavier et au Tab.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()