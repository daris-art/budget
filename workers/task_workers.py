# workers/task_workers.py

from PyQt6.QtCore import QObject, pyqtSignal
from core.data_models import Result
from datetime import datetime
from pathlib import Path
from core.data_models import Depense

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

class AlsaceExcelImportWorker(QObject):
    finished = pyqtSignal(Result)

    def __init__(self, model, filepath: Path, new_name: str):
        super().__init__()
        self.model = model
        self.filepath = filepath
        self.new_name = new_name

    def run(self):
        try:
            import pandas as pd
            df = pd.read_excel(self.filepath)

            # Vérifie que les colonnes attendues existent
            required_cols = ["Date", "Libellé", "Débit", "Crédit"]
            for col in required_cols:
                if col not in df.columns:
                    self.finished.emit(Result.error(f"Colonne manquante: {col}"))
                    return

            # Crée le mois
            result = self.model.create_mois(self.new_name)
            if not result.is_success:
                self.finished.emit(result)
                return

            # Parcourt les lignes
            for _, row in df.iterrows():
                try:
                    date_str = pd.to_datetime(row["Date"], dayfirst=True, errors="coerce").strftime("%d/%m/%Y")
                except Exception:
                    date_str = datetime.now().strftime("%d/%m/%Y")

                libelle = str(row["Libellé"]).strip()
                debit = float(row["Débit"] or 0)
                credit = float(row["Crédit"] or 0)

                if debit == 0 and credit > 0:
                    est_credit = True
                    montant_str = str(credit)
                elif credit == 0 and debit > 0:
                    est_credit = False
                    montant_str = str(debit)
                else:
                    continue  # ligne invalide ou vide

                depense = Depense(
                    nom=libelle,
                    montant=float(montant_str),
                    date_depense=date_str,
                    categorie="Revenue" if est_credit else "Autres",
                    effectue=False,
                    emprunte=False,
                    est_fixe=False
                )
                depense.est_credit = est_credit
                depense_id = self.model._db_manager.create_depense(self.model.mois_actuel.id, depense)
                depense.id = depense_id
                self.model._depenses.append(depense)

            self.finished.emit(Result.success("Import Alsace terminé"))
        except Exception as e:
            self.finished.emit(Result.error(f"Erreur import Alsace: {e}"))
