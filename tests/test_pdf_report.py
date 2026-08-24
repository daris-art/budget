import tempfile
import unittest
from pathlib import Path

from core.database import DatabaseManager
from core.data_models import Depense
from core.services import ImportExportService


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


if __name__ == '__main__':
    unittest.main()
