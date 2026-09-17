"""Vérifie le chargement asynchrone et l'affinité des notifications Qt."""
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QPA_PLATFORMTHEME', '')

from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QApplication
from controller import BudgetController
from core.database import DatabaseManager
from core.data_models import Depense
from core.model import BudgetModel
from core.services import BitcoinAPIService, ImportExportService
from core.validation import DataValidator


class MonthLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DatabaseManager(Path(self.tmp.name) / 'budget.db')
        for name in ('A', 'B', 'C'):
            mid = self.db.create_mois(name, 0)
            self.db.create_depense(mid, Depense(nom=name, montant=10, date_depense='01/01/2026'))
        self.model = BudgetModel(self.db, DataValidator(), ImportExportService(self.db), BitcoinAPIService())
        self.controller = BudgetController(self.model)
        self.view = Mock()
        self.controller.set_view(self.view)
        self.gate = threading.Event()
        self.notifications = []
        observer = Mock()
        observer.on_model_changed.side_effect = lambda event, data: self.notifications.append((event, QThread.currentThread()))
        self.model.add_observer(observer)

    def tearDown(self):
        self.gate.set()
        self.controller._shutdown_month_loading()
        self.app.processEvents()
        self.controller.deleteLater()
        self.tmp.cleanup()

    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.001)
        self.assertTrue(condition(), 'Le chargement ne se termine pas')

    def test_read_runs_off_gui_and_display_refreshes_once(self):
        read = self.model.read_mois
        worker_threads = []
        def blocked_read(name):
            worker_threads.append(QThread.currentThread())
            if not self.gate.wait(2):
                raise RuntimeError('Timeout du test')
            return read(name)
        self.model.read_mois = blocked_read
        self.controller._load_mois_async('A')
        self.wait_for(lambda: bool(worker_threads))
        self.assertNotEqual(worker_threads[0], self.app.thread())
        self.assertIsNone(self.model.mois_actuel)
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(True))
        self.wait_for(lambda: bool(heartbeat))
        self.assertFalse(self.notifications)
        self.gate.set()
        self.wait_for(lambda: self.controller.load_thread is None)
        self.assertEqual(self.model.mois_actuel.nom, 'A')
        self.view.refresh_expense_list.assert_called_once()
        self.view.update_complete_display.assert_not_called()
        self.assertTrue(all(thread == self.app.thread() for _, thread in self.notifications))
        self.view.hide_progress_bar.assert_called_once()
        self.view.set_month_actions_enabled.assert_called_with(True)

    def test_only_latest_request_is_applied(self):
        read = self.model.read_mois
        names = []
        def blocked_read(name):
            names.append(name)
            self.gate.wait(2)
            return read(name)
        self.model.read_mois = blocked_read
        self.controller._load_mois_async('A')
        self.wait_for(lambda: bool(names))
        self.controller._load_mois_async('B')
        self.controller._load_mois_async('C')
        self.gate.set()
        self.wait_for(lambda: self.controller.load_thread is None)
        self.assertEqual(names, ['A', 'C'])
        self.assertEqual(self.model.mois_actuel.nom, 'C')
        self.view.refresh_expense_list.assert_called_once()
        self.assertEqual(self.db.get_config('last_mois'), 'C')

    def test_failed_load_keeps_previous_month_and_restores_controls(self):
        self.model.load_mois('A')
        self.view.reset_mock()
        self.controller._load_mois_async('Inexistant')
        self.wait_for(lambda: self.controller.load_thread is None)
        self.assertEqual(self.model.mois_actuel.nom, 'A')
        self.view.update_complete_display.assert_called_once()
        self.view.show_error_message.assert_called_once()
        self.view.hide_progress_bar.assert_called_once()
        self.view.set_month_actions_enabled.assert_called_with(True)

    def test_startup_restores_last_month_asynchronously(self):
        self.db.save_config('last_mois', 'B')
        self.controller.handle_fetch_bitcoin_price = Mock()
        self.model.load_data_from_last_session = Mock(side_effect=AssertionError('Chargement synchrone'))
        self.controller.start_application()
        self.wait_for(lambda: self.controller.load_thread is None)
        self.assertEqual(self.model.mois_actuel.nom, 'B')
        self.model.load_data_from_last_session.assert_not_called()
        self.view.refresh_expense_list.assert_called_once()

    def test_unexpected_worker_error_restores_controls(self):
        self.model.read_mois = Mock(side_effect=RuntimeError('Lecture impossible'))
        self.controller._load_mois_async('A')
        self.wait_for(lambda: self.controller.load_thread is None)
        self.view.show_error_message.assert_called_once()
        self.assertIn('Lecture impossible', self.view.show_error_message.call_args.args[0])
        self.view.hide_progress_bar.assert_called_once()
        self.view.set_month_actions_enabled.assert_called_with(True)

    def test_first_startup_without_month_restores_controls(self):
        for name in ('A', 'B', 'C'):
            self.db.delete_mois(name)
        self.controller._load_mois_async(None)
        self.wait_for(lambda: self.controller.load_thread is None)
        self.assertIsNone(self.model.mois_actuel)
        self.view.show_error_message.assert_called_once()
        self.view.hide_progress_bar.assert_called_once()
        self.view.set_month_actions_enabled.assert_called_with(True)

    def test_shutdown_waits_for_worker_without_applying_result(self):
        self.controller._load_mois_async('A')
        thread = self.controller.load_thread
        self.controller._shutdown_month_loading()
        self.assertFalse(thread.isRunning())
        self.app.processEvents()
        self.assertIsNone(self.model.mois_actuel)
        self.view.refresh_expense_list.assert_not_called()
