import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from core.database import DatabaseManager
from core.data_models import Depense
from core.validation import DataValidator
from core.services import ImportExportService, BitcoinAPIService
from core.model import BudgetModel


class ModelFilteringTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'budget.db'
        self.db = DatabaseManager(self.db_path)
        self.validator = DataValidator()
        self.import_service = ImportExportService(self.db)
        self.api_service = BitcoinAPIService()
        self.model = BudgetModel(self.db, self.validator, self.import_service, self.api_service)

        # create a month and some expenses
        self.mois_id = self.db.create_mois('FilterMonth', 1000.0)
        self.db.create_depense(self.mois_id, Depense(nom='Cafe', montant=2.5, categorie='Loisirs', date_depense='01/01/2026'))
        self.db.create_depense(self.mois_id, Depense(nom='Supermarché', montant=50.0, categorie='Alimentation', date_depense='05/01/2026'))
        self.db.create_depense(self.mois_id, Depense(nom='Loyer', montant=700.0, categorie='Logement', date_depense='01/01/2026', est_fixe=True))
        self.db.create_depense(self.mois_id, Depense(nom='Salaire', montant=2000.0, categorie='Revenue', date_depense='28/01/2026', est_credit=True))

        # load into model
        self.model.load_mois('FilterMonth')

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_search_text_filter(self):
        self.model.filter_depenses('cafe', '', '', '', '')
        data = self.model.get_display_data()
        self.assertEqual(len(data.depenses), 1)
        self.assertEqual(data.depenses[0].nom.lower(), 'cafe')

    def test_date_filter_exact_day(self):
        # search day 01/01 (partial day+month)
        self.model.filter_depenses('', '01/01/2026', '', '', '')
        data = self.model.get_display_data()
        # expects Cafe and Loyer (both 01/01/2026)
        self.assertEqual(len(data.depenses), 2)

    def test_amount_range_filter(self):
        # find expenses between 10 and 800 (should include Supermarché and Loyer)
        self.model.filter_depenses('', '', '', '10', '800')
        data = self.model.get_display_data()
        noms = sorted([d.nom for d in data.depenses])
        self.assertEqual(noms, ['Loyer', 'Supermarché'])

    def test_combined_filters(self):
        # text+amount filter that matches none
        self.model.filter_depenses('loyer', '', '', '0', '100')
        data = self.model.get_display_data()
        self.assertEqual(len(data.depenses), 0)


if __name__ == '__main__':
    unittest.main()
