# ui/custom_widgets.py

from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QWheelEvent

class NoScrollComboBox(QComboBox):
    """
    Une QComboBox personnalisée qui ignore les événements de la molette.
    """
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()