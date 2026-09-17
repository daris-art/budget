import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook
from core.database import DatabaseManager
from workers.task_workers import AlsaceExcelImportWorker


class AlsaceImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = DatabaseManager(Path(self.tmp.name) / 'budget.db')
        self.model = SimpleNamespace(_db_manager=self.db, mois_actuel=None, _depenses=[])

    def run_import(self, rows, headers=None):
        path = Path(self.tmp.name) / 'releve.xlsx'
        wb = Workbook()
        sheet = wb.active
        sheet.append(headers or ['Date', 'Libellé', 'Débit', 'Crédit'])
        for row in rows:
            sheet.append(row)
        wb.save(path)
        wb.close()
        results = []
        worker = AlsaceExcelImportWorker(self.model, path, 'Import')
        worker.finished.connect(results.append)
        worker.run()
        self.assertEqual(len(results), 1)
        return results[0]

    def test_blank_opposite_amounts_import_both_operations(self):
        result = self.run_import([
            ['01/01/2026', 'Achat', 20, None],
            [None, None, None, None],
            ['02/01/2026', 'Salaire', None, '1\u202f234,56'],
        ])
        self.assertTrue(result.is_success, result.error)
        month = self.db.get_mois_by_name('Import')
        deps = self.db.get_depenses_by_mois(month.id)
        self.assertEqual([(d.nom, d.montant, d.est_credit) for d in deps],
                         [('Achat', 20, False), ('Salaire', 1234.56, True)])
        self.assertIsNone(self.model.mois_actuel)
        self.assertEqual(self.model._depenses, [])

    def test_empty_file_creates_no_month(self):
        result = self.run_import([])
        self.assertFalse(result.is_success)
        self.assertIn('Aucune opération', result.error)
        self.assertEqual(self.db.get_all_mois(), [])

    def test_invalid_amounts_cancel_entire_import(self):
        for debit, credit in [('incorrect', None), ('inf', None), (-1, None), (10, 10), (0, 0)]:
            with self.subTest(debit=debit, credit=credit):
                result = self.run_import([
                    ['01/01/2026', 'Valide', 20, None],
                    ['02/01/2026', 'Invalide', debit, credit],
                ])
                self.assertFalse(result.is_success)
                self.assertIn('Ligne 3', result.error)
                self.assertEqual(self.db.get_all_mois(), [])

    def test_invalid_date_or_label_is_reported(self):
        for date, label in [('31/02/2026', 'Achat'), (None, 'Achat'), ('01/01/2026', None)]:
            with self.subTest(date=date, label=label):
                result = self.run_import([[date, label, 20, None]])
                self.assertFalse(result.is_success)
                self.assertIn('Ligne 2', result.error)
                self.assertEqual(self.db.get_all_mois(), [])

    def test_missing_column_creates_no_month(self):
        result = self.run_import([], headers=['Date', 'Libellé', 'Débit'])
        self.assertFalse(result.is_success)
        self.assertIn('Colonne manquante', result.error)
        self.assertEqual(self.db.get_all_mois(), [])

    def test_duplicate_month_preserves_existing_data(self):
        original_id = self.db.create_mois('Import', 123)
        result = self.run_import([['01/01/2026', 'Achat', 20, None]])
        self.assertFalse(result.is_success)
        self.assertEqual(len(self.db.get_all_mois()), 1)
        self.assertEqual(self.db.get_mois_by_id(original_id).salaire, 123)
        self.assertEqual(self.db.get_depenses_by_mois(original_id), [])
