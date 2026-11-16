import datetime
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from core.database import DatabaseManager
from core.services import ImportExportService


class ImportExportServiceExcelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = DatabaseManager(Path(self.tmp.name) / "budget.db")
        self.service = ImportExportService(self.db)

    def test_imports_operation_date_header(self):
        path = Path(self.tmp.name) / "operations.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Libellé", "Date d'opération", "Débit euros", "Crédit euros"])
        sheet.append(["Achat", datetime.datetime(2026, 1, 2), 15, None])
        workbook.save(path)
        workbook.close()

        result = self.service.import_from_excel(path, "Import")

        self.assertTrue(result.is_success, result.error)
        month = self.db.get_mois_by_name("Import")
        expenses = self.db.get_depenses_by_mois(month.id)
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].date_depense, "02/01/2026")

    def test_imports_date_header(self):
        path = Path(self.tmp.name) / "operations.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Libellé", "Date", "Débit euros", "Crédit euros"])
        sheet.append(["Achat", datetime.datetime(2026, 1, 2), 15, None])
        workbook.save(path)
        workbook.close()

        result = self.service.import_from_excel(path, "Import")

        self.assertTrue(result.is_success, result.error)
        month = self.db.get_mois_by_name("Import")
        expenses = self.db.get_depenses_by_mois(month.id)
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].date_depense, "02/01/2026")


if __name__ == "__main__":
    unittest.main()
