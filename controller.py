# controller.py (version avec QThread)

from datetime import datetime
import logging

# --- AJOUT : Imports nécessaires pour le multithreading ---
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from utils import Result # Assurez-vous que Result est bien importable

logger = logging.getLogger(__name__)


# --- AJOUT : Classe "Worker" pour l'import en arrière-plan ---
class ExcelImportWorker(QObject):
    """
    Worker qui effectue l'importation Excel dans un thread séparé.
    """
    finished = pyqtSignal(Result)
    # Le signal de progression n'est plus nécessaire

    def __init__(self, model, filepath, new_name):
        super().__init__()
        self.model = model
        self.filepath = filepath
        self.new_name = new_name

    def run(self):
        """Exécute la tâche d'importation de manière sécurisée."""
        logger.info("Le worker d'import Excel démarre...")
        try:
            # On exécute l'import comme avant
            result = self.model.import_from_excel(self.filepath, self.new_name)
        except Exception as e:
            # --- AJOUT CRUCIAL ---
            # Si N'IMPORTE QUELLE erreur se produit pendant l'import,
            # on la capture ici.
            logger.critical(f"Erreur non interceptée dans le worker d'import: {e}")
            # On crée un objet Result d'erreur pour l'envoyer au thread principal.
            result = Result.error(f"Une erreur critique est survenue dans le worker: {e}")
        
        # Quoi qu'il arrive (succès ou erreur), la variable 'result'
        # contiendra un objet Result valide.
        self.finished.emit(result)
        logger.info("Le worker d'import Excel a terminé.")



class BudgetController:
    """
    Contrôleur de l'application Budget.
    """
    def __init__(self, model):
        self.model = model
        self.view = None
        self.model.add_observer(self)
        # On garde une référence au thread pour éviter qu'il soit supprimé par erreur
        self.import_thread = None
        self.import_worker = None

    def set_view(self, view):
        """Associe la vue à ce contrôleur."""
        self.view = view

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
    
    def handle_import_from_excel(self):
        """Gère l'import depuis un fichier Excel en utilisant un QThread."""
        filepath = self.view.get_excel_import_filepath()
        if not filepath:
            return

        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Nouveau mois",
                                            "Entrez le nom pour ce nouveau mois importé :",
                                            default_name)
        if not new_name:
            return

        # 1. D'abord, on configure l'UI
        self.view.set_month_actions_enabled(False)
        self.view.update_status_bar(f"Importation de '{filepath.name}' en cours...", duration=0)
        self.view.show_progress_bar(indeterminate=True)
        
        # 2. CRUCIAL : On force la mise à jour de l'UI avant de démarrer le thread
        QApplication.processEvents()
        
        # 3. Ensuite, on prépare le thread
        self.import_thread = QThread()
        self.import_worker = ExcelImportWorker(self.model, filepath, new_name)
        self.import_worker.moveToThread(self.import_thread)
        
        # 4. On connecte les signaux
        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.finished.connect(self._on_import_excel_finished)
        self.import_worker.finished.connect(self.import_thread.quit)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)

        # 5. On démarre le thread avec un léger délai pour s'assurer que l'UI est à jour
        QTimer.singleShot(100, self.import_thread.start)

    # Dans le fichier controller.py, remplacez cette méthode

    def _on_import_excel_finished(self, result: Result):
        """
        Slot qui gère le résultat une fois l'import en arrière-plan terminé.
        """
        # 1. On traite le résultat de l'opération en arrière-plan (lecture du fichier)
        self._handle_result(result)
        
        # 2. Si la lecture a réussi, on lance la mise à jour de l'interface
        if result.is_success and self.import_worker:
            new_name = self.import_worker.new_name
            
            # --- CORRECTION ---
            # Au lieu de gérer manuellement la barre et les boutons ici,
            # on appelle notre fonction _load_mois_async qui le fait déjà
            # de manière robuste et garantie.
            self._load_mois_async(new_name)
        
        else:
            # Si l'import a échoué, on s'assure quand même de tout réactiver
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)
            self.view.update_status_bar("L'importation a échoué.", duration=5000)

    def handle_update_expense(self, index: int):
        """Gère la mise à jour d'une dépense."""
        try:
            data = self.view.get_expense_data(index)
            if data:
                # On passe les arguments nommés au modèle
                result = self.model.update_expense(index, **data)
                self._handle_result(result, show_success=False)
        except Exception as e:
            logger.error(f"Erreur critique lors de la tentative de mise à jour de la dépense {index}: {e}")
            self.view.show_error_message(f"Impossible de sauvegarder la dépense : {e}")
    
    # --- CORRECTION 2 : Suppression par ID ---
    def handle_remove_expense_by_id(self, depense_id: int):
        """Gère la suppression d'une dépense via son ID."""
        if self.view.ask_confirmation("Confirmation", "Supprimer cette dépense ?"):
            result = self.model.remove_expense_by_id(depense_id)
            self._handle_result(result, show_success=False)


    # --- GESTIONNAIRES D'ÉVÉNEMENTS DE LA VUE ---

    def handle_create_mois(self):
        """Gère la création d'un nouveau mois."""
        try:
            # La vue PyQt demande les informations elle-même
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

    # Dans le fichier controller.py, modifiez la méthode _load_mois_async

    # Dans le fichier controller.py, remplacez la méthode _load_mois_async

    def _load_mois_async(self, nom_mois: str):
        """Charge les données d'un mois de manière asynchrone pour ne pas geler l'UI."""
        
        # On désactive les boutons AVANT le bloc try
        self.view.set_month_actions_enabled(False)
        self.view.clear_for_loading(f"Chargement de '{nom_mois}'...")
        self.view.show_progress_bar(indeterminate=True)
        QApplication.processEvents()

        def do_load():
            try:
                # Le travail réel est fait ici
                result = self.model.load_mois(nom_mois)
                self._handle_result(result, show_success=False)
            finally:
                # Ce bloc est GARANTI d'être exécuté, même en cas d'erreur
                self.view.hide_progress_bar()
                self.view.set_month_actions_enabled(True)

        # On planifie l'exécution
        QTimer.singleShot(50, do_load)

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

    # Dans le fichier controller.py, remplacez la méthode handle_duplicate_mois

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
                # --- DÉBUT DE L'OPÉRATION ---
                self.view.set_month_actions_enabled(False)
                self.view.show_progress_bar(indeterminate=True)
                self.view.update_status_bar(f"Duplication vers '{new_name}' en cours...", duration=0)
                QApplication.processEvents()

                result = self.model.duplicate_mois(new_name)
                self._handle_result(result)
            finally:
                # --- FIN (TOUJOURS EXÉCUTÉ) ---
                self.view.hide_progress_bar()
                self.view.set_month_actions_enabled(True)

    def handle_set_salaire(self):
        """Gère la mise à jour du salaire."""
        if self.model.mois_actuel:
            salaire_str = self.view.salaire_input.text()
            # Pour éviter de redéclancher une mise à jour si la valeur n'a pas changé
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

    def handle_update_expense(self, index: int):
        """Gère la mise à jour d'une dépense."""
        try:
            data = self.view.get_expense_data(index)
            if data:
                result = self.model.update_expense(index, **data)
                self._handle_result(result, show_success=False)
        except Exception as e:
            # Ce bloc attrapera les erreurs comme les incohérences de nom de paramètre
            logger.error(f"Erreur critique lors de la tentative de mise à jour de la dépense {index}: {e}")
            self.view.show_error_message(f"Impossible de sauvegarder la dépense : {e}")

    def handle_remove_expense(self, index: int):
        """Gère la suppression d'une dépense."""
        if self.view.ask_confirmation("Confirmation", "Supprimer cette dépense ?"):
            result = self.model.remove_expense(index)
            self._handle_result(result, show_success=False)

    # Dans controller.py, remplacez la méthode handle_sort_expenses

    def handle_sort_expenses(self):
        """Gère le tri des dépenses en fonction de l'option choisie dans la vue."""
        if self.model.mois_actuel:
            sort_key = self.view.get_sort_key()
            result = self.model.sort_depenses(sort_key)
            self._handle_result(result, show_success=False)

    def handle_clear_all_expenses(self):
        """Gère la suppression de toutes les dépenses."""
        if self.model.mois_actuel:
            if self.view.ask_confirmation("Confirmation", "Voulez-vous vraiment supprimer TOUTES les dépenses de ce mois ?"):
                result = self.model.clear_all_expenses()
                self._handle_result(result)

    def handle_export_to_json(self):
        """Gère l'export vers JSON"""
        try:
            if not self.model.mois_actuel:
                self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")
                return

            filepath = self.view.get_export_filepath()
            if not filepath:
                return

            result = self.model.export_to_json(filepath)
            self._handle_result(result)

        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            self.view.show_error_message("Erreur lors de l'export")

    def handle_import_from_json(self):
        """Gère l'import depuis JSON en créant un nouveau mois."""
        filepath = self.view.get_import_filepath()
        if not filepath:
            return

        # Propose un nom par défaut et demande à l'utilisateur de confirmer/modifier
        default_name = f"Import {filepath.stem} {datetime.now().strftime('%B %Y')}"
        new_name = self.view.ask_for_string("Importer un nouveau mois",
                                            "Entrez le nom pour ce nouveau mois importé :",
                                            default_name)
        if not new_name:
            return
        
        try:
            # --- DÉBUT DE L'OPÉRATION ---
            self.view.set_month_actions_enabled(False)
            self.view.show_progress_bar(indeterminate=True)
            self.view.update_status_bar(f"Importation de '{filepath.name}'...", duration=0)
            QApplication.processEvents()

            result = self.model.import_from_json(filepath, new_name)
            self._handle_result(result)
        finally:
            # --- FIN (TOUJOURS EXÉCUTÉ) ---
            self.view.hide_progress_bar()
            self.view.set_month_actions_enabled(True)


    # --- MÉTHODE DE L'OBSERVATEUR ---
    def on_model_changed(self, event_type: str, data: any):
        """
        Méthode appelée par le modèle lorsqu'il change.
        """
        if not self.view:
            return

        logger.info(f"Événement reçu: {event_type}")

        # MODIFICATION : Ajout du cas pour le changement de thème
        if event_type == 'theme_changed':
            if self.view:
                self.view.apply_theme(data)
        
        # On s'assure que la liste des mois est aussi rafraîchie lors de ces événements
        elif event_type in ['mois_created', 'mois_loaded']:
            self._refresh_complete_view()
            self._refresh_mois_list() # <- C'EST LA LIGNE QUI MANQUAIT

        elif event_type == 'mois_cleared':
            self._refresh_complete_view()
            self._refresh_mois_list()
        elif event_type in ['mois_deleted', 'mois_duplicated', 'mois_renamed']:
            self._refresh_mois_list(select_first=True)
        elif event_type == 'salaire_updated':
            # Pas besoin de rafraîchir toute la vue, juste le salaire et le résumé
            self.view.update_salary_display(data)
            self._refresh_summary_view()
        
        elif event_type == 'expense_added':
            # 1. On ajoute le widget à la vue (qui va aussi scroller)
            self.view.add_expense_widget(data, len(self.model.depenses) - 1)

            # On demande explicitement à la vue de défiler vers le bas.
            self.view.scroll_expenses_to_bottom()
            
            # 2. --- AJOUT : On demande explicitement à la vue de mettre le focus ---
            self.view.focus_on_last_expense_name()
            
            # 3. On met à jour le résumé comme avant
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

    # --- MÉTHODES PRIVÉES DE MISE À JOUR DE LA VUE ---

    def _refresh_complete_view(self):
        """Met à jour l'ensemble de l'affichage."""
        display_data = self.model.get_display_data()
        if display_data:
            self.view.update_complete_display(display_data)
            self.view.update_status_bar("Affichage mis à jour.")

            # Après avoir rafraîchi toute la vue, on demande un défilement vers le haut.
            self.view.scroll_expenses_to_top()

    def _refresh_summary_view(self):
        """Ne met à jour que le récapitulatif."""
        summary_data = {
            # --- MODIFICATION ---
            "nombre_depenses": self.model.get_nombre_depenses(),
            "total_depenses": self.model.get_total_depenses(),
            "argent_restant": self.model.get_argent_restant(),
            "total_effectue": self.model.get_total_depenses_effectuees(),
            "total_non_effectue": self.model.get_total_depenses_non_effectuees(),
            "total_emprunte": self.model.get_total_emprunte()
        }
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
                # Si un mois a été supprimé, chargeons le premier de la liste
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

    # Dans controller.py, remplacez cette méthode

    def handle_live_update(self):
        """
        Met à jour le récapitulatif en direct en se basant sur les données
        actuellement affichées dans la vue.
        """
        if not self.view or not self.model.mois_actuel:
            return

        try:
            salaire_str = self.view.salaire_input.text().replace(',', '.')
            salaire = float(salaire_str) if salaire_str.strip() and salaire_str.strip() != '-' else 0.0

            total_depenses = 0.0
            total_effectue = 0.0
            total_emprunte = 0.0
            # --- MODIFICATION ---
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
                # --- MODIFICATION ---
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
        
    # AJOUT : Gestionnaire pour le bouton de changement de thème
    def handle_toggle_theme(self):
        """Bascule entre le thème clair et le thème sombre."""
        current_theme = self.model.get_theme_preference()
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.model.save_theme_preference(new_theme)



    