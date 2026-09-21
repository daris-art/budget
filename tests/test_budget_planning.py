import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_PLATFORMTHEME', '')

from PyQt6.QtWidgets import QApplication
from core.budget_planning import analyze_budget
from core.data_models import Depense
from core.database import DatabaseManager
from core.model import BudgetModel
from ui.budget_planning import BudgetPlanningDialog


class BudgetPlanningTests(unittest.TestCase):
    def test_savings_are_not_counted_twice(self):
        operations = [Depense(montant=2000, est_credit=True),
                      Depense(montant=1000, categorie='Logement'),
                      Depense(montant=200, categorie='Épargne', effectue=True),
                      Depense(montant=100, categorie='Épargne')]
        result = analyze_budget(operations, 500)
        self.assertEqual(result['spending'], 1000)
        self.assertEqual(result['savings_paid'], 200)
        self.assertEqual(result['savings_planned'], 100)
        self.assertEqual(result['savings_missing'], 200)
        self.assertEqual(result['available'], 500)
        self.assertEqual(analyze_budget(operations, 100)['available'], 700)

    def test_empty_month_deficit_and_decimal_amounts(self):
        self.assertEqual(analyze_budget([], 100)['available'], -100)
        result = analyze_budget([Depense(montant=0.1), Depense(montant=0.2)])
        self.assertEqual(str(result['spending']), '0.3')
        self.assertEqual(str(result['available']), '-0.3')

    def test_month_specific_persistence_and_unfiltered_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = DatabaseManager(Path(tmp) / 'budget.db')
            first = db.create_mois('Premier', 0)
            second = db.create_mois('Second', 0)
            model = BudgetModel(db, None, None, None)
            model.mois_actuel = db.get_mois_by_id(first)
            model._depenses = [Depense(montant=42)]
            model._displayed_depenses = []
            self.assertEqual(len(model.get_planning_expenses()), 1)
            plan = {'savings_goal': 150, 'limits': {'Loisirs': 50}}
            model.save_budget_plan(plan)
            model._db_manager = DatabaseManager(db.db_path)
            self.assertEqual(model.get_budget_plan(), plan)
            model.mois_actuel = db.get_mois_by_id(second)
            self.assertEqual(model.get_budget_plan()['savings_goal'], 0)

    def test_dialog_updates_limits_and_saves(self):
        app = QApplication.instance() or QApplication([])
        saved = []
        dialog = BudgetPlanningDialog('Test', [Depense(montant=75, categorie='Loisirs')],
                                      ['Loisirs'], {}, saved.append)
        dialog.limits['Loisirs'].setValue(50)
        self.assertIn('Dépassement : 25.00', dialog.table.item(0, 3).text())
        dialog.goal.setValue(100)
        self.assertIn('175.00 € manquants', dialog.summary.text())
        dialog.save()
        self.assertEqual(saved[0]['savings_goal'], 100)
        self.assertEqual(saved[0]['limits']['Loisirs'], 50)
        dialog.close()
