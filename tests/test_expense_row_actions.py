"""Régressions des actions de ligne, avec une base temporaire."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_PLATFORMTHEME', '')

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtGui import QShortcut
from core.database import DatabaseManager
from core.data_models import Depense
from core.model import BudgetModel
from core.services import BitcoinAPIService, ImportExportService
from core.validation import DataValidator
from controller import BudgetController
from view import BudgetView


class ExpenseRowActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DatabaseManager(Path(self.tmp.name) / 'budget.db')
        self.month_id = self.db.create_mois('Test', 0)
        self.ids = [self.db.create_depense(self.month_id, Depense(
            nom=name, montant=10, date_depense='01/01/2026'
        )) for name in ('A', 'B', 'C', 'D')]
        self.model = BudgetModel(self.db, DataValidator(), ImportExportService(self.db), BitcoinAPIService())
        self.controller = BudgetController(self.model)
        self.view = BudgetView(self.controller)
        self.controller.set_view(self.view)
        self.view.show_error_message = Mock()
        self.view.ask_confirmation = Mock(return_value=True)
        self.model.load_mois('Test')

    def tearDown(self):
        self.controller._update_timer.stop()
        self.view.close()
        self.view.deleteLater()
        self.tmp.cleanup()

    def widget(self, row, column):
        return self.view.expense_rows[row].layout().itemAtPosition(0, column).widget()

    def stored(self):
        return {dep.id: dep for dep in self.db.get_depenses_by_mois(self.month_id)}

    def test_all_editable_fields_target_remaining_operation(self):
        self.controller.handle_remove_expense_by_id(self.ids[0])
        for column, value in ((2, 'B modifiée'), (3, '25'), (4, '02/01/2026')):
            field = self.widget(0, column)
            field.setText(value)
            field.editingFinished.emit()
        category = self.widget(0, 5)
        category.setCurrentText('Loisirs')
        category.activated.emit(category.currentIndex())
        for column in (6, 7, 8):
            self.widget(0, column).setChecked(True)
        deps = self.stored()
        b = deps[self.ids[1]]
        self.assertEqual((b.nom, b.montant, b.date_depense, b.categorie),
                         ('B modifiée', 25, '02/01/2026', 'Loisirs'))
        self.assertTrue(b.effectue and b.emprunte and b.est_fixe)
        self.assertEqual(deps[self.ids[2]].nom, 'C')
        self.assertEqual(deps[self.ids[2]].montant, 10)
        self.view.show_error_message.assert_not_called()

    def test_toggle_and_delete_after_multiple_deletions(self):
        self.controller.handle_remove_expenses_by_ids(self.ids[:2])
        self.widget(0, 1).click()
        deps = self.stored()
        self.assertTrue(deps[self.ids[2]].est_credit)
        self.assertFalse(deps[self.ids[3]].est_credit)
        self.widget(0, 9).click()
        self.assertEqual(list(self.stored()), [self.ids[3]])
        self.widget(0, 1).click()
        self.assertTrue(self.stored()[self.ids[3]].est_credit)
        self.view.show_error_message.assert_not_called()

    def test_late_signal_from_deleted_row_is_ignored(self):
        old_field = self.widget(0, 2)
        self.controller.handle_remove_expense_by_id(self.ids[0])
        old_field.editingFinished.emit()
        self.view.show_error_message.assert_not_called()
        self.assertEqual([d.nom for d in self.stored().values()], ['B', 'C', 'D'])

    def test_toggle_synchronizes_category_and_survives_editing(self):
        self.controller.handle_remove_expense_by_id(self.ids[0])
        target_id = self.ids[1]
        for expected_credit, expected_category in ((True, 'Revenue'), (False, 'Autres')):
            with self.subTest(est_credit=expected_credit):
                self.widget(0, 1).click()
                self.assertEqual(self.widget(0, 5).currentText(), expected_category)
                self.assertEqual(self.view.expense_rows[0].est_credit, expected_credit)
                self.widget(0, 3).setText('25' if expected_credit else '30')
                self.widget(0, 3).editingFinished.emit()
                stored = self.stored()[target_id]
                self.assertEqual(stored.est_credit, expected_credit)
                self.assertEqual(stored.categorie, expected_category)
                self.assertEqual(stored.montant, 25 if expected_credit else 30)
                self.assertEqual(self.widget(0, 1).text(), '🟢' if expected_credit else '🔴')
        self.view.show_error_message.assert_not_called()

    def test_selected_operation_stays_selected_after_deletion(self):
        self.view._select_row(2, True)
        self.view.selected_row_indices = [2]
        self.view.last_selected_index = 2
        self.controller.handle_remove_expense_by_id(self.ids[0])
        self.assertEqual(self.view.selected_row_indices, [1])
        self.assertEqual(self.view.last_selected_index, 1)
        self.view._delete_selected_expenses()
        self.assertEqual(list(self.stored()), [self.ids[1], self.ids[3]])

    def test_actions_after_deletion_in_filtered_sorted_list(self):
        self.model.filter_depenses('', '', '', '1', '20')
        self.model.sort_depenses('nom_desc')
        first_id = self.view.expense_rows[0].depense_id
        target_id = self.view.expense_rows[1].depense_id
        self.controller.handle_remove_expense_by_id(first_id)
        self.widget(0, 2).setText('Modifiée')
        self.widget(0, 2).editingFinished.emit()
        self.assertEqual(self.stored()[target_id].nom, 'Modifiée')
        self.view.show_error_message.assert_not_called()

    def wait_for_render(self):
        deadline = time.monotonic() + 5
        while (self.view.is_rendering_expenses or self.controller.load_thread is not None) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.001)
        self.assertFalse(self.view.is_rendering_expenses)
        self.assertIsNone(self.controller.load_thread)

    def add_large_month(self):
        for index in range(80):
            self.db.create_depense(self.month_id, Depense(
                nom=f'Operation {index}', montant=index + 1, date_depense='01/01/2026'
            ))

    def test_month_progress_advances_while_event_loop_remains_responsive(self):
        self.add_large_month()
        progress = []
        self.view.progress_bar.valueChanged.connect(progress.append)
        self.controller._load_mois_async('Test')
        self.wait_for_render()
        self.assertEqual(len(self.view.expense_rows), 84)
        self.assertTrue(any(0 < value < 100 for value in progress))
        self.assertIn(100, progress)
        self.assertTrue(self.view.progress_bar.isHidden())
        self.assertTrue(self.view.mois_selector_combo.isEnabled())

    def test_sort_progress_stays_visible_until_all_rows_are_built(self):
        self.add_large_month()
        self.model.load_mois('Test')
        self.wait_for_render()
        self.view.sort_combo.setCurrentText("Montant (plus élevé d'abord)")
        progress = []
        self.view.progress_bar.valueChanged.connect(progress.append)
        self.controller.handle_sort_expenses()
        self.assertTrue(self.view.is_rendering_expenses)
        self.assertFalse(self.view.progress_bar.isHidden())
        self.assertFalse(self.view.mois_selector_combo.isEnabled())
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(len(self.view.expense_rows)))
        self.wait_for_render()
        self.assertTrue(heartbeat and heartbeat[0] < 84)
        self.assertTrue(any(0 < value < 100 for value in progress))
        amounts = [float(self.widget(i, 3).text()) for i in range(84)]
        self.assertEqual(amounts, sorted(amounts, reverse=True))
        self.assertTrue(self.view.progress_bar.isHidden())
        self.assertTrue(self.view.mois_selector_combo.isEnabled())

    def test_new_month_cancels_pending_render_batches(self):
        self.add_large_month()
        self.model.load_mois('Test')
        self.assertTrue(self.view.is_rendering_expenses)
        self.db.create_mois('Vide', 0)
        self.controller._load_mois_async('Vide')
        self.wait_for_render()
        self.assertEqual(self.model.mois_actuel.nom, 'Vide')
        self.assertEqual(self.view.expense_rows, [])
        self.assertTrue(self.view.progress_bar.isHidden())

    def assert_interface_locked(self):
        self.assertFalse(self.view.centralWidget().isEnabled())
        self.assertTrue(self.view.progress_bar.isEnabled())
        self.assertTrue(all(not button.isEnabled() for button in self.view.findChildren(QPushButton)))
        self.assertTrue(all(not shortcut.isEnabled() for shortcut in self.view.findChildren(QShortcut)))

    def test_all_actions_locked_through_loading_and_rendering(self):
        self.add_large_month()
        self.controller._load_mois_async('Test')
        self.assert_interface_locked()
        deadline = time.monotonic() + 5
        while not self.view.is_rendering_expenses and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.001)
        self.assertTrue(self.view.is_rendering_expenses)
        self.assert_interface_locked()
        self.view.btn_generate_pdf_report.click()
        self.wait_for_render()
        self.assertTrue(self.view.centralWidget().isEnabled())
        self.assertTrue(all(shortcut.isEnabled() for shortcut in self.view.findChildren(QShortcut)))

    def test_sort_locks_actions_and_preserves_individually_disabled_controls(self):
        self.add_large_month()
        self.model.load_mois('Test')
        self.wait_for_render()
        self.view.btn_refresh_btc.setEnabled(False)
        self.view.shortcut_new_month.setEnabled(False)
        self.controller.handle_sort_expenses()
        self.assert_interface_locked()
        self.view.set_month_actions_enabled(True)
        self.assert_interface_locked()
        self.wait_for_render()
        self.assertTrue(self.view.centralWidget().isEnabled())
        self.assertTrue(self.view.btn_generate_pdf_report.isEnabled())
        self.assertTrue(self.view.shortcut_add_expense.isEnabled())
        self.assertFalse(self.view.btn_refresh_btc.isEnabled())
        self.assertFalse(self.view.shortcut_new_month.isEnabled())

    def test_failed_month_load_unlocks_interface(self):
        self.controller._load_mois_async('Inexistant')
        self.assert_interface_locked()
        self.wait_for_render()
        self.assertTrue(self.view.centralWidget().isEnabled())
        self.assertTrue(self.view.shortcut_add_expense.isEnabled())
        self.view.show_error_message.assert_called_once()
