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

            # Prépare la liste de toutes les dépenses avant la transaction
            depenses_to_import = []

            # Parcourt les lignes et prépare les objets Depense
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
                    montant = credit
                elif credit == 0 and debit > 0:
                    est_credit = False
                    montant = debit
                else:
                    continue  # ligne invalide ou vide

                depense = Depense(
                    nom=libelle,
                    montant=montant,
                    date_depense=date_str,
                    categorie="Revenue" if est_credit else "Autres",
                    effectue=False,
                    emprunte=False,
                    est_fixe=False,
                    est_credit=est_credit
                )
                depenses_to_import.append(depense)

            # Crée le mois et toutes ses dépenses en une seule transaction atomique
            mois_id = self.model._db_manager.create_mois_with_depenses_transaction(
                self.new_name, 
                0.0,  # salaire par défaut
                depenses_to_import
            )
            
            # Charge les dépenses dans le modèle
            self.model.mois_actuel = self.model._db_manager.get_mois_by_name(self.new_name)
            self.model._depenses = self.model._db_manager.get_depenses_by_mois(mois_id)

            self.finished.emit(Result.success(f"Import Alsace terminé: {len(depenses_to_import)} lignes importées"))
        except Exception as e:
            self.finished.emit(Result.error(f"Erreur import Alsace: {e}"))
