# workers/task_workers.py

from PyQt6.QtCore import QObject, pyqtSignal
from core.data_models import Result
from math import isfinite
from pathlib import Path
from core.data_models import Depense

class MonthLoadWorker(QObject):
    finished = pyqtSignal(int, Result)

    def __init__(self, model, name, request_id):
        super().__init__()
        self.model = model
        self.name = name
        self.request_id = request_id

    def run(self):
        try:
            result = self.model.read_mois(self.name)
        except Exception as e:
            result = Result.error(f"Erreur lors du chargement: {e}")
        self.finished.emit(self.request_id, result)


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

            depenses_to_import = []
            invalid_rows = []

            def parse_amount(value):
                if pd.isna(value):
                    return 0.0
                if isinstance(value, str):
                    value = value.strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
                    if not value:
                        return 0.0
                    value = value.replace(",", ".")
                amount = float(value)
                if not isfinite(amount) or amount < 0:
                    raise ValueError("montant négatif ou non fini")
                return amount

            for line_number, (_, row) in enumerate(df.iterrows(), start=2):
                # Seules les lignes entièrement vides peuvent être ignorées.
                if all(pd.isna(row[col]) or str(row[col]).strip() == "" for col in required_cols):
                    continue
                try:
                    date = pd.to_datetime(row["Date"], dayfirst=True, errors="coerce")
                    if pd.isna(date):
                        raise ValueError("date absente ou invalide")
                    if pd.isna(row["Libellé"]) or not str(row["Libellé"]).strip():
                        raise ValueError("libellé manquant")
                    debit = parse_amount(row["Débit"])
                    credit = parse_amount(row["Crédit"])
                    if (debit > 0) == (credit > 0):
                        raise ValueError("renseigner un seul montant positif : débit ou crédit")
                except (ValueError, TypeError, OverflowError) as e:
                    invalid_rows.append(f"Ligne {line_number} : {e}")
                    continue

                est_credit = credit > 0
                depenses_to_import.append(Depense(
                    nom=str(row["Libellé"]).strip(),
                    montant=credit if est_credit else debit,
                    date_depense=date.strftime("%d/%m/%Y"),
                    categorie="Revenue" if est_credit else "Autres",
                    est_credit=est_credit
                ))

            if invalid_rows:
                details = "\n".join(invalid_rows[:10])
                if len(invalid_rows) > 10:
                    details += f"\n… et {len(invalid_rows) - 10} autre(s) ligne(s)."
                self.finished.emit(Result.error(
                    f"Import annulé : {len(invalid_rows)} ligne(s) invalide(s). "
                    f"Aucune opération importée.\n{details}"
                ))
                return
            if not depenses_to_import:
                self.finished.emit(Result.error("Aucune opération valide à importer. Aucun mois créé."))
                return

            self.model._db_manager.create_mois_with_depenses_transaction(
                self.new_name, 0.0, depenses_to_import
            )
            # Le contrôleur chargera le mois dans le thread graphique après succès.
            self.finished.emit(Result.success(f"Import Alsace terminé: {len(depenses_to_import)} lignes importées"))
        except Exception as e:
            self.finished.emit(Result.error(f"Erreur import Alsace: {e}"))
