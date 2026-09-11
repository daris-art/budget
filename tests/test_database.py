import tempfile
import unittest
from pathlib import Path

from core.database import DatabaseManager
from core.data_models import Depense


class DatabaseManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'budget.db'
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_and_get_mois(self):
        mois_id = self.db.create_mois('TestMonth', 1234.5)
        self.assertIsInstance(mois_id, int)
        mois = self.db.get_mois_by_id(mois_id)
        self.assertIsNotNone(mois)
        self.assertEqual(mois.nom, 'TestMonth')

    def test_create_and_get_depense(self):
        mois_id = self.db.create_mois('M2', 0)
        dep = Depense(nom='Test', montant=10.0, categorie='Autres', date_depense='01/01/2026')
        dep_id = self.db.create_depense(mois_id, dep)
        self.assertIsInstance(dep_id, int)
        deps = self.db.get_depenses_by_mois(mois_id)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].nom, 'Test')

    def test_update_and_delete_depense(self):
        mois_id = self.db.create_mois('M3', 0)
        dep = Depense(nom='ToUpdate', montant=5.0, categorie='Autres', date_depense='02/02/2026')
        dep_id = self.db.create_depense(mois_id, dep)
        dep.id = dep_id
        dep.nom = 'Updated'
        dep.montant = 7.5
        self.db.update_depense(dep)
        deps = self.db.get_depenses_by_mois(mois_id)
        self.assertEqual(deps[0].nom, 'Updated')

        # delete
        self.db.delete_depense(dep_id)
        deps_after = self.db.get_depenses_by_mois(mois_id)
        self.assertEqual(len(deps_after), 0)

    def test_duplicate_mois(self):
        src_id = self.db.create_mois('Src', 500)
        self.db.create_depense(src_id, Depense(nom='A', montant=1.0, categorie='X', date_depense='01/01/2026'))
        result = self.db.duplicate_mois(src_id, 'Copy')
        self.assertTrue(result.is_success)
        mois_list = self.db.get_all_mois()
        names = [m.nom for m in mois_list]
        self.assertIn('Copy', names)

    def test_import_new_mois(self):
        deps = [Depense(nom='I1', montant=2.0, categorie='Y', date_depense='03/03/2026')]
        new_id = self.db.import_new_mois('Imported', 1000.0, deps)
        self.assertIsInstance(new_id, int)
        deps_loaded = self.db.get_depenses_by_mois(new_id)
        self.assertEqual(len(deps_loaded), 1)

    def test_config_save_and_get(self):
        self.db.save_config('foo', 'bar')
        self.assertEqual(self.db.get_config('foo'), 'bar')


if __name__ == '__main__':
    unittest.main()
