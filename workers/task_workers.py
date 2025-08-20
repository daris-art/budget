# workers/task_workers.py

from PyQt6.QtCore import QObject, pyqtSignal
from core.data_models import Result

class BitcoinPriceWorker(QObject):
    finished = pyqtSignal(Result)

    def __init__(self, model):
        super().__init__()
        self.model = model

    def run(self):
        result = self.model.get_bitcoin_price()
        self.finished.emit(result)

class ExcelImportWorker(QObject):
    finished = pyqtSignal(Result)

    def __init__(self, model, filepath, new_name):
        super().__init__()
        self.model = model
        self.filepath = filepath
        self.new_name = new_name

    def run(self):
        try:
            result = self.model.import_from_excel(self.filepath, self.new_name)
        except Exception as e:
            result = Result.error(f"Erreur critique dans le worker: {e}")
        self.finished.emit(result)