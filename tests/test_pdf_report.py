import tempfile
import unittest
from pathlib import Path

from core.database import DatabaseManager
from core.data_models import Depense, Result
from core.model import BudgetModel
from core.services import ImportExportService


class FakeBitcoinAPIService:
    def get_price(self):
        return Result.success(data=123.45)


class PdfReportExportTests(unittest.TestCase):
    def test_export_month_report_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db = DatabaseManager(Path(tmp_dir) / 'budget.db')
            mois_id = db.create_mois('Janvier 2026', 2500.0)
            db.create_depense(mois_id, Depense(
                nom='Loyer', montant=800.0, categorie='Logement', date_depense='01/01/2026',
                est_credit=False, effectue=True, emprunte=False, est_fixe=True
            ))
            db.create_depense(mois_id, Depense(
                nom='Salaire', montant=2500.0, categorie='Revenue', date_depense='28/01/2026',
                est_credit=True, effectue=True, emprunte=False, est_fixe=False
            ))

            service = ImportExportService(db)
            output = Path(tmp_dir) / 'rapport.pdf'

            result = service.export_month_report_pdf(mois_id, output)

            self.assertTrue(result.is_success, result.error)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)

    def test_export_month_report_pdf_sorted_by_amount(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db = DatabaseManager(Path(tmp_dir) / 'budget.db')
            mois_id = db.create_mois('Fev 2026', 2000.0)
            db.create_depense(mois_id, Depense(nom='A', montant=10.0, categorie='X', date_depense='01/02/2026'))
            db.create_depense(mois_id, Depense(nom='B', montant=5.0, categorie='Y', date_depense='02/02/2026'))

            service = ImportExportService(db)
            output = Path(tmp_dir) / 'rapport_sorted.pdf'

            result = service.export_month_report_pdf_sorted_by_amount(mois_id, output)

            self.assertTrue(result.is_success, result.error)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)

    def test_model_get_bitcoin_price_uses_api_service(self):
        model = BudgetModel(None, None, None, FakeBitcoinAPIService())

        result = model.get_bitcoin_price()

        self.assertTrue(result.is_success)
        self.assertEqual(result.data, 123.45)


if __name__ == '__main__':
    unittest.main()
