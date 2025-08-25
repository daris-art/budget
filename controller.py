# controller.py (Version finale refactorisée)

import logging
from datetime import datetime
from core.data_models import Depense
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QApplication

# --- IMPORTS DEPUIS LA NOUVELLE STRUCTURE ---
from core.data_models import Result
from graph_view import GraphDialog
from workers.task_workers import BitcoinPriceWorker, ExcelImportWorker

logger = logging.getLogger(__name__)

class BudgetController:
    """
    Contrôleur de l'application Budget.
    Orchestre les interactions entre le modèle et la vue.
    """
    def __init__(self, model):
        self.model = model
        self.view = None
        self.model.add_observer(self)
        self.import_thread = None
        self.import_worker = None
        self.btc_thread = None
        self.btc_worker = None

    def set_view(self, view):
        """Associe la vue à ce contrôleur."""
        self.view = view
        if hasattr(self.view, 'btn_refresh_btc'):
            self.view.btn_refresh_btc.clicked.connect(self.handle_fetch_bitcoin_price)

    def start_application(self):
        """Démarre l'application."""
        self.model.initialize_backend()
        theme = self.model.get_theme_preference()
        if self.view:
            self.view.apply_theme(theme)
            self.view.clear_for_loading("Chargement des données...")
        self._refresh_mois_list()
        result = self.model.load_data_from_last_session()
        self._handle_result(result, show_success=False)
        self.handle_fetch_bitcoin_price()

    # --- GESTIONNAIRES D'ÉVÉNEMENTS (HANDLERS) ---

    def handle_fetch_bitcoin_price(self):
        """Gère la récupération du prix du BTC en utilisant un QThread."""
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

    def handle_import_from_excel(self):
        """Gère l'import depuis un fichier Excel en utilisant un QThread."""
        filepath = self.view.get_excel_import_filepath()
        if not filepath:
            return

        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Nouveau mois", "Entrez le nom pour ce nouveau mois importé :", default_name)
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
    
    def handle_create_mois(self):
        """Gère la création d'un nouveau mois."""
        try:
            mois_data = self.view.get_new_mois_input()
            if mois_data:
                result = self.model.create_mois(mois_data['nom'], mois_data['salaire'])
                self._handle_result(result)
        except Exception as e:
            logger.error(f"Erreur lors de la création du mois: {e}")
            self.view.show_error_message(f"Une erreur inattendue est survenue: {e}")

    def handle_load_mois_from_combo(self, index: int):
        """Gère le chargement d'un mois depuis la sélection dans le ComboBox."""
        if index >= 0:
            nom_mois = self.view.mois_selector_combo.itemText(index)
            if nom_mois and (not self.model.mois_actuel or self.model.mois_actuel.nom != nom_mois):
                self._load_mois_async(nom_mois)

    def handle_delete_mois(self):
        """Gère la suppression du mois actuel."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Aucun mois n'est chargé pour être supprimé.")
            return

        nom_mois = self.model.mois_actuel.nom
        if self.view.ask_confirmation("Confirmation de suppression", f"Êtes-vous sûr de vouloir supprimer '{nom_mois}' et toutes ses dépenses ?"):
            result = self.model.delete_mois(nom_mois)
            self._handle_result(result)

    def handle_rename_mois(self):
        """Gère le renommage du mois actuel."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois pour le renommer.")
            return

        original_name = self.model.mois_actuel.nom
        new_name = self.view.ask_for_string("Renommer le mois", "Entrez le nouveau nom du mois :", original_name)
        if new_name and new_name.strip() != original_name:
            result = self.model.rename_mois(new_name)
            self._handle_result(result)

    def handle_duplicate_mois(self):
        """Gère la duplication du mois actuel."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois à dupliquer.")
            return

        original_name = self.model.mois_actuel.nom
        default_new_name = f"Copie de {original_name}"
        new_name = self.view.ask_for_string("Dupliquer le mois", "Entrez le nom du nouveau mois :", default_new_name)
        
        if new_name:
            try:
                self.view.set_month_actions_enabled(False)
                self.view.show_progress_bar(indeterminate=True)
                self.view.update_status_bar(f"Duplication vers '{new_name}' en cours...", duration=0)
                QApplication.processEvents()

                result = self.model.duplicate_mois(new_name)
                self._handle_result(result)
            finally:
                self.view.hide_progress_bar()
                self.view.set_month_actions_enabled(True)

    def handle_set_salaire(self):
        """Gère la mise à jour du salaire."""
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
        """Gère l'ajout d'une nouvelle dépense."""
        if self.model.mois_actuel:
            result = self.model.add_expense()
            self._handle_result(result, show_success=False)
        else:
            self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")

    # controller.py

    def handle_update_expense(self, index: int):
        """Gère la mise à jour d'une dépense."""
        try:
            data = self.view.get_expense_data(index)
            if data:
                # On retire la clé 'est_credit' qui est utile pour le calcul en direct
                # mais ne doit pas être passée à la méthode de mise à jour du modèle,
                # car cette propriété n'est pas modifiable depuis l'interface.
                data.pop('est_credit', None)
                
                result = self.model.update_expense(index, **data)
                self._handle_result(result, show_success=False)
        except Exception as e:
            logger.error(f"Erreur critique lors de la mise à jour de la dépense {index}: {e}")
            self.view.show_error_message(f"Impossible de sauvegarder la dépense : {e}")

    def handle_remove_expense_by_id(self, depense_id: int):
        """Gère la suppression d'une dépense via son ID."""
        if self.view.ask_confirmation("Confirmation", "Supprimer cette dépense ?"):
            result = self.model.remove_expense_by_id(depense_id)
            self._handle_result(result, show_success=False)

    def handle_sort_expenses(self):
        """Gère le tri des dépenses en fonction de l'option choisie dans la vue."""
        if not self.model.mois_actuel:
            return
        try:
            self.view.set_month_actions_enabled(False)
            self.view.show_progress_bar(indeterminate=True)
            self.view.update_status_bar("Tri des dépenses en cours...", duration=0)
            QApplication.processEvents()
            sort_key = self.view.get_sort_key()
            result = self.model.sort_depenses(sort_key)
            self._handle_result(result, show_success=False)
            self.handle_live_update()
        finally:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.update_status_bar("Tri terminé.", duration=3000)
            
    def handle_export_to_json(self):
        """Gère l'export vers JSON"""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")
            return
        filepath = self.view.get_export_filepath()
        if not filepath:
            return
        result = self.model.export_to_json(filepath)
        self._handle_result(result)

    def handle_import_from_json(self):
        """Gère l'import depuis JSON en créant un nouveau mois."""
        filepath = self.view.get_import_filepath()
        if not filepath:
            return
        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Importer un nouveau mois", "Entrez le nom pour ce nouveau mois importé :", default_name)
        if not new_name:
            return
        try:
            self.view.set_month_actions_enabled(False)
            self.view.show_progress_bar(indeterminate=True)
            self.view.update_status_bar(f"Importation de '{filepath.name}'...", duration=0)
            QApplication.processEvents()
            result = self.model.import_from_json(filepath, new_name)
            self._handle_result(result)
        finally:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)

    def handle_live_update(self):
        """
        Met à jour le récapitulatif en direct en se basant sur les données
        actuellement affichées dans la vue. Utilise uniquement les revenus et dépenses.
        """
        if not self.view or not self.model.mois_actuel:
            return

        try:
            # Créer une liste temporaire des dépenses avec les valeurs actuelles de l'interface
            temp_expenses = []
            
            for i in range(len(self.view.expense_rows)):
                data = self.view.get_expense_data(i)
                if not data: 
                    continue

                # Récupérer le montant depuis l'interface
                montant_str = data.get('montant_str', '0').replace(',', '.')
                try:
                    montant = float(montant_str) if montant_str.strip() and montant_str.strip() != '-' else 0.0
                except (ValueError, TypeError):
                    montant = 0.0

                # Créer un objet temporaire avec les valeurs de l'interface
                temp_expense = type('TempExpense', (), {
                    'montant': montant,
                    'est_credit': data.get('est_credit', False),
                    'effectue': data.get('effectue', False),
                    'emprunte': data.get('emprunte', False),
                    'est_fixe': data.get('est_fixe', False)
                })()
                
                temp_expenses.append(temp_expense)

            # Utiliser la méthode du modèle pour calculer les totaux
            summary_data = self.model._calculate_summary_for_list(temp_expenses)
            
            # Mettre à jour l'affichage
            self.view.update_summary_display(summary_data)

        except Exception as e:
            logger.error(f"Erreur dans handle_live_update: {e}")


    def handle_toggle_theme(self):
        """Bascule entre le thème clair et le thème sombre."""
        current_theme = self.model.get_theme_preference()
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.model.save_theme_preference(new_theme)

    def handle_show_graphs(self):
        """Ouvre une fenêtre affichant les graphiques pour le mois en cours."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois pour voir les graphiques.")
            return
        graph_data = self.model.get_graph_data()
        if not graph_data or (not graph_data[2] and not graph_data[3]):
            self.view.show_info_message("Aucune dépense ou revenu à afficher dans les graphiques.")
            return
        dialog = GraphDialog(graph_data, self.view)
        dialog.exec()

    # --- SLOTS (RÉPONSES AUX WORKERS) ---
    
    def _on_bitcoin_price_fetched(self, result: Result):
        """Slot qui gère le résultat une fois la récupération du prix terminée."""
        if result.is_success:
            price = result.data
            price_str = f"{price:,.2f} €".replace(",", " ")
            tooltip = f"Dernière mise à jour le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
            self.view.update_bitcoin_price(price_str, tooltip)
        else:
            self.view.update_bitcoin_price("Erreur", result.error)
        self.view.btn_refresh_btc.setEnabled(True)

    def _on_import_excel_finished(self, result: Result):
        """Slot qui gère le résultat une fois l'import en arrière-plan terminé."""
        self._handle_result(result)
        if result.is_success and self.import_worker:
            new_name = self.import_worker.new_name
            self._load_mois_async(new_name)
        else:
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.update_status_bar("L'importation a échoué.", duration=5000)

    # --- MÉTHODE DE L'OBSERVATEUR ---

    def on_model_changed(self, event_type: str, data: any):
        """Méthode appelée par le modèle lorsqu'il change."""
        if not self.view: return
        logger.info(f"Événement reçu: {event_type}")

        if event_type == 'display_updated':
            # Cet événement gère maintenant TOUS les rafraîchissements
            # de la liste et du résumé.
            self.view.refresh_expense_list(data['expenses'])
            self.view.update_summary_display(data['summary'])
        elif event_type == 'theme_changed':
            self.view.apply_theme(data)
        elif event_type in ['mois_created', 'mois_loaded']:
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
        elif event_type in ['live_summary_updated']:
            self._refresh_summary_view()
        elif event_type == 'expense_removed':
            self.view.remove_expense_widget(data['index'])
            self._refresh_summary_view()
        elif event_type == 'expenses_sorted':
            self._refresh_complete_view()

        elif event_type == 'display_updated':
            # On met à jour la liste des dépenses ET le résumé en même temps
            self.view.refresh_expense_list(data['expenses'])
            self.view.update_summary_display(data['summary'])


    # --- MÉTHODES PRIVÉES ---

    def _load_mois_async(self, nom_mois: str):
        """Charge les données d'un mois sans geler l'UI."""
        self.view.set_month_actions_enabled(False)
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
        QTimer.singleShot(50, do_load)
        
    def _refresh_complete_view(self):
        """Met à jour l'ensemble de l'affichage."""
        display_data = self.model.get_display_data()
        if display_data:
            self.view.update_complete_display(display_data)
            self.view.update_status_bar("Affichage mis à jour.")
            self.view.scroll_expenses_to_top()

    def _refresh_summary_view(self):
        """Ne met à jour que le récapitulatif."""
        summary_data = self.model.get_summary_data()
        self.view.update_summary_display(summary_data)

    def _refresh_mois_list(self, select_first=False):
        """Met à jour la liste des mois dans le ComboBox."""
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
        """Gère un objet Result retourné par le modèle."""
        if result.is_success:
            if show_success and result.message:
                self.view.update_status_bar(result.message)
        else:
            if result.error:
                self.view.show_error_message(result.error)
                self.view.update_status_bar(f"Erreur: {result.error}", is_error=True)

    # --- NOUVEAU HANDLER POUR LA RECHERCHE ---
    def handle_search_expenses(self, search_text: str):
        """
        Appelé à chaque fois que le texte dans le champ de recherche change.
        """
        self.model.filter_depenses_by_name(search_text)
        self.handle_live_update()


    