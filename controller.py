# controller.py

from datetime import datetime
import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from utils import Result
from graph_view import GraphDialog

logger = logging.getLogger(__name__)

class BitcoinPriceWorker(QObject):
    finished = pyqtSignal(Result)

    def __init__(self, model):
        super().__init__()
        self.model = model

    def run(self):
        logger.info("Le worker BTC démarre...")
        result = self.model.get_bitcoin_price()
        self.finished.emit(result)
        logger.info("Le worker BTC a terminé.")

class ExcelImportWorker(QObject):
    finished = pyqtSignal(Result)

    def __init__(self, model, filepath, new_name):
        super().__init__()
        self.model = model
        self.filepath = filepath
        self.new_name = new_name

    def run(self):
        logger.info("Le worker d'import Excel démarre...")
        try:
            result = self.model.import_from_excel(self.filepath, self.new_name)
        except Exception as e:
            logger.critical(f"Erreur non interceptée dans le worker d'import: {e}")
            result = Result.error(f"Une erreur critique est survenue dans le worker: {e}")
        self.finished.emit(result)
        logger.info("Le worker d'import Excel a terminé.")

class BudgetController:
    def __init__(self, model):
        self.model = model
        self.view = None
        self.model.add_observer(self)
        self.import_thread = None
        self.import_worker = None
        self.btc_thread = None
        self.btc_worker = None

    def set_view(self, view):
        self.view = view
        if hasattr(self.view, 'btn_refresh_btc'):
            self.view.btn_refresh_btc.clicked.connect(self.handle_fetch_bitcoin_price)

    def start_application(self):
        self.model.initialize_backend()
        theme = self.model.get_theme_preference()
        if self.view:
            self.view.apply_theme(theme)
            self.view.clear_for_loading("Chargement des données...")
        self._refresh_mois_list()
        result = self.model.load_data_from_last_session()
        self._handle_result(result, show_success=False)
        self.handle_fetch_bitcoin_price()

    def handle_fetch_bitcoin_price(self):
        self.view.update_bitcoin_price("Chargement...", "Récupération en cours...")
        self.view.btn_refresh_btc.setEnabled(False)

        self.btc_thread = QThread()
        self.btc_worker = BitcoinPriceWorker(self.model)
        self.btc_worker.moveToThread(self.btc_thread)
        
        self.btc_thread.started.connect(self.btc_worker.run)
        self.btc_worker.finished.connect(self._on_bitcoin_price_fetched)
        self.btc_worker.finished.connect(self.btc_thread.quit)
        self.btc_worker.finished.connect(self.btc_worker.deleteLater)
        self.btc_thread.finished.connect(self.btc_thread.deleteLater)

        self.btc_thread.start()

    def _on_bitcoin_price_fetched(self, result: Result):
        if result.is_success:
            price = result.data
            price_str = f"{price:,.2f} €".replace(",", " ")
            tooltip = f"Dernière mise à jour le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
            self.view.update_bitcoin_price(price_str, tooltip)
        else:
            self.view.update_bitcoin_price("Erreur", result.error)
        
        self.view.btn_refresh_btc.setEnabled(True)

    def handle_import_from_excel(self):
        filepath = self.view.get_excel_import_filepath()
        if not filepath:
            return

        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Nouveau mois",
                                            "Entrez le nom pour ce nouveau mois importé :",
                                            default_name)
        if not new_name:
            return

        self.view.set_month_actions_enabled(False)
        self.view.update_status_bar(f"Importation de '{filepath.name}' en cours...", duration=0)
        self.view.show_progress_bar(indeterminate=True)
        QApplication.processEvents()
        
        self.import_thread = QThread()
        self.import_worker = ExcelImportWorker(self.model, filepath, new_name)
        self.import_worker.moveToThread(self.import_thread)
        
        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.finished.connect(self._on_import_excel_finished)
        self.import_worker.finished.connect(self.import_thread.quit)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)

        QTimer.singleShot(100, self.import_thread.start)

    def _on_import_excel_finished(self, result: Result):
        self._handle_result(result)
        if result.is_success and self.import_worker:
            new_name = self.import_worker.new_name
            self._load_mois_async(new_name)
        else:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.set_expenses_interactive(True) # <-- AJOUT
            self.view.update_status_bar("L'importation a échoué.", duration=5000)

    def handle_update_expense(self, index: int):
        try:
            data = self.view.get_expense_data(index)
            if data:
                result = self.model.update_expense(index, **data)
                self._handle_result(result, show_success=False)
        except Exception as e:
            logger.error(f"Erreur critique lors de la mise à jour : {e}")
            self.view.show_error_message(f"Impossible de sauvegarder la dépense : {e}")
    
    def handle_remove_expense_by_id(self, depense_id: int):
        if self.view.ask_confirmation("Confirmation", "Supprimer cette dépense ?"):
            result = self.model.remove_expense_by_id(depense_id)
            self._handle_result(result, show_success=False)

    def handle_create_mois(self):
        try:
            mois_data = self.view.get_new_mois_input()
            if mois_data:
                result = self.model.create_mois(mois_data['nom'], mois_data['salaire'])
                self._handle_result(result)
        except Exception as e:
            logger.error(f"Erreur lors de la création du mois: {e}")
            self.view.show_error_message(f"Une erreur inattendue est survenue: {e}")

    def handle_load_mois_from_combo(self, index: int):
        if index >= 0:
            nom_mois = self.view.mois_selector_combo.itemText(index)
            if nom_mois and (not self.model.mois_actuel or self.model.mois_actuel.nom != nom_mois):
                self._load_mois_async(nom_mois)

    def _load_mois_async(self, nom_mois: str):
        self.view.set_month_actions_enabled(False)
        self.view.set_expenses_interactive(False) # <-- AJOUT
        self.view.clear_for_loading(f"Chargement de '{nom_mois}'...")
        self.view.show_progress_bar(indeterminate=True)
        QApplication.processEvents()

        def do_load():
            try:
                result = self.model.load_mois(nom_mois)
                self._handle_result(result, show_success=False)
            finally:
                self.view.hide_progress_bar()
                self.view.set_month_actions_enabled(True)
                self.view.set_expenses_interactive(True) # <-- AJOUT

        QTimer.singleShot(50, do_load)

    def handle_delete_mois(self):
        if not self.model.mois_actuel:
            self.view.show_warning_message("Aucun mois n'est chargé.")
            return

        nom_mois = self.model.mois_actuel.nom
        if self.view.ask_confirmation("Confirmation", f"Supprimer '{nom_mois}' ?"):
            result = self.model.delete_mois(nom_mois)
            self._handle_result(result)

    def handle_rename_mois(self):
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois.")
            return

        original_name = self.model.mois_actuel.nom
        new_name = self.view.ask_for_string("Renommer le mois", "Nouveau nom :", original_name)
        if new_name and new_name.strip() != original_name:
            result = self.model.rename_mois(new_name)
            self._handle_result(result)

    def handle_duplicate_mois(self):
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois.")
            return

        original_name = self.model.mois_actuel.nom
        default_new_name = f"Copie de {original_name}"
        new_name = self.view.ask_for_string("Dupliquer le mois", "Nom du nouveau mois :", default_new_name)
        
        if new_name:
            try:
                self.view.set_month_actions_enabled(False)
                self.view.set_expenses_interactive(False) # <-- AJOUT
                self.view.show_progress_bar(indeterminate=True)
                self.view.update_status_bar(f"Duplication vers '{new_name}'...", duration=0)
                QApplication.processEvents()

                result = self.model.duplicate_mois(new_name)
                self._handle_result(result)
            finally:
                self.view.hide_progress_bar()
                self.view.set_month_actions_enabled(True)
                self.view.set_expenses_interactive(True) # <-- AJOUT

    def handle_set_salaire(self):
        if self.model.mois_actuel:
            salaire_str = self.view.salaire_input.text()
            try:
                if float(salaire_str) != self.model.salaire:
                    result = self.model.set_salaire(salaire_str)
                    self._handle_result(result)
            except (ValueError, TypeError):
                 result = self.model.set_salaire(salaire_str)
                 self._handle_result(result)

    def handle_add_expense(self):
        if self.model.mois_actuel:
            result = self.model.add_expense()
            self._handle_result(result, show_success=False)
        else:
            self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")

    def handle_remove_expense(self, index: int):
        if self.view.ask_confirmation("Confirmation", "Supprimer cette dépense ?"):
            result = self.model.remove_expense(index)
            self._handle_result(result, show_success=False)

    def handle_sort_expenses(self):
        if not self.model.mois_actuel:
            return

        try:
            self.view.set_month_actions_enabled(False)
            self.view.set_expenses_interactive(False) # <-- AJOUT
            self.view.show_progress_bar(indeterminate=True)
            self.view.update_status_bar("Tri en cours...", duration=0)
            QApplication.processEvents()

            sort_key = self.view.get_sort_key()
            result = self.model.sort_depenses(sort_key)
            self._handle_result(result, show_success=False)
        finally:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.set_expenses_interactive(True) # <-- AJOUT
            
    def handle_export_to_json(self):
        try:
            if not self.model.mois_actuel:
                self.view.show_warning_message("Veuillez charger un mois.")
                return
            filepath = self.view.get_export_filepath()
            if not filepath: return
            result = self.model.export_to_json(filepath)
            self._handle_result(result)
        except Exception as e:
            logger.error(f"Erreur d'export: {e}")
            self.view.show_error_message("Erreur lors de l'export")

    def handle_import_from_json(self):
        filepath = self.view.get_import_filepath()
        if not filepath: return

        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Importer", "Nom pour le nouveau mois :", default_name)
        if not new_name: return
        
        try:
            self.view.set_month_actions_enabled(False)
            self.view.set_expenses_interactive(False) # <-- AJOUT
            self.view.show_progress_bar(indeterminate=True)
            self.view.update_status_bar(f"Import de '{filepath.name}'...", duration=0)
            QApplication.processEvents()
            result = self.model.import_from_json(filepath, new_name)
            self._handle_result(result)
        finally:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.set_expenses_interactive(True) # <-- AJOUT

    def on_model_changed(self, event_type: str, data: any):
        if not self.view: return
        logger.info(f"Événement reçu: {event_type}")

        if event_type == 'theme_changed':
            self.view.apply_theme(data)
        elif event_type in ['mois_created', 'mois_loaded']:
            self._refresh_complete_view()
            self._refresh_mois_list()
        elif event_type == 'mois_cleared':
            self._refresh_complete_view()
            self._refresh_mois_list()
        elif event_type in ['mois_deleted', 'mois_duplicated', 'mois_renamed']:
            self._refresh_mois_list(select_first=True)
        elif event_type == 'salaire_updated':
            self.view.update_salary_display(data)
            self._refresh_summary_view()
        elif event_type == 'expense_added':
            self.view.add_expense_widget(data, len(self.model.depenses) - 1)
            self.view.scroll_expenses_to_bottom()
            self.view.focus_on_last_expense_name()
            self._refresh_summary_view()
        elif event_type == 'expense_updated':
            self._refresh_summary_view()
        elif event_type == 'expense_removed':
            self.view.remove_expense_widget(data['index'])
            self._refresh_summary_view()
        elif event_type == 'all_expenses_cleared':
            self.view.clear_all_expenses()
            self._refresh_summary_view()
        elif event_type == 'expenses_sorted':
            self._refresh_complete_view()

    def _refresh_complete_view(self):
        display_data = self.model.get_display_data()
        if display_data:
            self.view.update_complete_display(display_data)
            self.view.update_status_bar("Affichage mis à jour.")
            self.view.scroll_expenses_to_top()

    def _refresh_summary_view(self):
        summary_data = {
            "nombre_depenses": self.model.get_nombre_depenses(),
            "total_depenses": self.model.get_total_depenses(),
            "argent_restant": self.model.get_argent_restant(),
            "total_effectue": self.model.get_total_depenses_effectuees(),
            "total_non_effectue": self.model.get_total_depenses_non_effectuees(),
            "total_emprunte": self.model.get_total_emprunte()
        }
        self.view.update_summary_display(summary_data)

    def _refresh_mois_list(self, select_first=False):
        result = self.model.get_all_mois()
        if result.is_success:
            mois_objects = result.data
            mois_names = [m.nom for m in mois_objects]

            selected_mois = ""
            if self.model.mois_actuel:
                selected_mois = self.model.mois_actuel.nom
            elif select_first and mois_names:
                self._load_mois_async(mois_names[0])
                return

            self.view.update_mois_list(mois_names, selected_mois)

    def _handle_result(self, result, show_success=True):
        if result.is_success:
            if show_success and result.message:
                self.view.update_status_bar(result.message)
        else:
            if result.error:
                self.view.show_error_message(result.error)
                self.view.update_status_bar(f"Erreur: {result.error}", is_error=True)

    def handle_live_update(self):
        if not self.view or not self.model.mois_actuel:
            return

        try:
            salaire_str = self.view.salaire_input.text().replace(',', '.')
            salaire = float(salaire_str) if salaire_str.strip() and salaire_str.strip() != '-' else 0.0

            total_depenses = 0.0
            total_effectue = 0.0
            total_emprunte = 0.0
            nombre_depenses = len(self.view.expense_rows)

            for i in range(nombre_depenses):
                data = self.view.get_expense_data(i)
                montant_str = data['montant_str'].replace(',', '.')
                montant = float(montant_str) if montant_str.strip() and montant_str.strip() != '-' else 0.0

                total_depenses += montant
                if data['effectue']:
                    total_effectue += montant
                if data['emprunte']:
                    total_emprunte += montant
            
            argent_restant = salaire - total_depenses
            total_non_effectue = total_depenses - total_effectue
            
            summary_data = {
                "nombre_depenses": nombre_depenses,
                "total_depenses": total_depenses,
                "argent_restant": argent_restant,
                "total_effectue": total_effectue,
                "total_non_effectue": total_non_effectue,
                "total_emprunte": total_emprunte
            }
            self.view.update_summary_display(summary_data)

        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Erreur non bloquante pendant la mise à jour en direct : {e}")
            pass
        
    def handle_toggle_theme(self):
        current_theme = self.model.get_theme_preference()
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.model.save_theme_preference(new_theme)

    def handle_show_graphs(self):
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois pour voir les graphiques.")
            return

        graph_data = self.model.get_graph_data()
        
        if not graph_data or not graph_data[3]:
            self.view.show_info_message("Aucune dépense à afficher dans les graphiques pour ce mois.")
            return

        dialog = GraphDialog(graph_data, self.view)
        dialog.exec()
