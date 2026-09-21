"""En-tête fixe aligné sur la géométrie réelle des colonnes d'opérations."""
from PyQt6.QtCore import QEvent, QPoint, QTimer, Qt
from PyQt6.QtWidgets import QLabel, QWidget


class ExpenseHeader(QWidget):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.labels = []
        for title in ('N°', 'Type', 'Nom', 'Montant (€)', 'Date', 'Catégorie',
                      'Payé', 'Prêt', 'Fixe', 'Actions'):
            label = QLabel(f'<b>{title}</b>', self)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.hide()
            self.labels.append(label)
        self.setFixedHeight(max(label.sizeHint().height() for label in self.labels) + 8)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.sync_columns)

    def watch(self, widget):
        widget.installEventFilter(self)
        self.schedule_sync()

    def schedule_sync(self, *_):
        self._timer.start(0)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move,
                            QEvent.Type.LayoutRequest, QEvent.Type.Show,
                            QEvent.Type.Hide):
            self.schedule_sync()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_sync()

    def sync_columns(self):
        rows = self.view.expense_rows
        if not rows:
            for label in self.labels:
                label.hide()
            return
        row = rows[0]
        grid = row.layout()
        grid.activate()
        origin = self.mapFromGlobal(row.mapToGlobal(QPoint(0, 0)))
        for column, label in enumerate(self.labels):
            cell = grid.cellRect(0, column)
            label.setGeometry(origin.x() + cell.x(), 0, cell.width(), self.height())
            label.show()
