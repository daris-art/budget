# controller.py - Controller amélioré avec architecture MVC stricte

import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import logging
import pandas as pd
from utils import Observer, Result, MoisInput
from model import BudgetModel
from view import BudgetView
from utils import Depense

logger = logging.getLogger(__name__)

class BudgetController(Observer):
    """
    Controller - Responsable uniquement de la coordination entre Vue et Modèle
    """
    
    def __init__(self, model: BudgetModel, master):
        self.model = model
        self.view = BudgetView(master, self)
        self.master = master
        
        self.model.add_observer(self)
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)
        
        self.view.update_status("Initialisation...")
        self.master.after(100, self._handle_initial_load)
        
        logger.info("BudgetController initialisé")
    
    # ===== PATTERN OBSERVER =====
    def on_model_changed(self, event_type: str, data=None):
        """Réagit aux changements du modèle de manière optimisée."""
        try:
            if event_type == 'expense_added':
                self.view.add_expense_widget(data, self.model.categories)
                self._refresh_summary_view()
            
            elif event_type == 'expense_removed':
                self.view.remove_expense_widget(data['index'])
                self._refresh_summary_view()
            
            elif event_type in ['mois_created', 'mois_loaded', 'data_imported', 
                                'expenses_sorted', 'all_expenses_cleared', 
                                'mois_cleared', 'mois_duplicated']:
                self._refresh_complete_view()
            
            elif event_type in ['salaire_updated', 'expense_updated']:
                self._refresh_summary_view()
                
            elif event_type == 'mois_renamed':
                self.view.update_mois_title(data['new_name'])
            
            logger.debug(f"Vue mise à jour suite à l'événement: {event_type}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la vue: {e}")
            self.view.show_error_message("Erreur lors de la mise à jour de l'interface")

    # ===== GESTION DE L'APPLICATION =====
    def _handle_initial_load(self):
        """Gère le chargement initial de l'application"""
        try:
            self.model.initialize_backend()
            result = self.model.load_data_from_last_session()
            self._handle_result(result)
            self.view.update_status("Prêt.")
            
            if not result.is_success and "Aucun mois disponible" in result.error:
                self.handle_create_new_mois()
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement initial: {e}")
            self.view.show_error_message("Erreur lors du chargement initial de l'application")
    
    def handle_on_closing(self):
        """Gère la fermeture de l'application"""
        try:
            plt.close('all')
            self.view.master.destroy()
            logger.info("Application fermée proprement")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")
            self.view.master.destroy()
    
    # ===== GESTION DES MOIS =====
    def handle_create_new_mois(self):
        """Gère la création d'un nouveau mois"""
        try:
            user_input = self.view.get_new_mois_input()
            if not user_input:
                return
            
            result = self.model.create_mois(user_input.nom, user_input.salaire)
            self._handle_result(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création d'un nouveau mois: {e}")
            self.view.show_error_message("Erreur lors de la création du nouveau mois")
    
    def handle_load_mois(self):
        """Gère le chargement d'un mois existant de manière asynchrone."""
        try:
            result = self.model.get_all_mois()
            if not result.is_success:
                self._handle_result(result)
                return
            
            all_mois = result.data
            if not all_mois:
                self.view.show_info_message("Aucun mois disponible. Créez un nouveau mois.")
                return
            
            selected_mois = self.view.show_mois_selection_dialog(all_mois)
            if not selected_mois:
                return
            
            self.view.clear_for_loading(f"Chargement du mois '{selected_mois.nom}'...")
            
            self.master.after(50, lambda: self._load_mois_async(selected_mois.nom))

        except Exception as e:
            logger.error(f"Erreur lors du chargement d'un mois: {e}")
            self.view.show_error_message("Erreur lors du chargement du mois")

    def _load_mois_async(self, nom_mois: str):
        """Fonction helper pour charger les données du mois sans bloquer l'UI."""
        load_result = self.model.load_mois(nom_mois)
        self._handle_result(load_result)
    
    def handle_delete_mois(self):
        """Gère la suppression d'un mois"""
        try:
            result = self.model.get_all_mois()
            if not result.is_success:
                self._handle_result(result)
                return
            
            all_mois = result.data
            if not all_mois:
                self.view.show_info_message("Aucun mois disponible.")
                return
            
            if len(all_mois) == 1 and self.model.mois_actuel:
                if not self.view.ask_confirmation(
                    "Confirmation", 
                    "Vous êtes sur le point de supprimer le seul mois disponible. Continuer ?"
                ):
                    return
            
            selected_mois = self.view.show_mois_selection_dialog(
                all_mois, 
                title="Supprimer un mois",
                prompt="Sélectionnez un mois à supprimer:"
            )
            if not selected_mois:
                return
            
            if not self.view.ask_confirmation(
                "Confirmation", 
                f"Supprimer définitivement le mois '{selected_mois.nom}' ?"
            ):
                return
            
            delete_result = self.model.delete_mois(selected_mois.nom)
            self._handle_result(delete_result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression d'un mois: {e}")
            self.view.show_error_message("Erreur lors de la suppression du mois")

    def handle_duplicate_mois(self):
        """Gère la duplication du mois actuel."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois avant de le dupliquer.")
            return

        try:
            default_name = f"{self.model.mois_actuel.nom} (copie)"
            new_name = self.view.ask_for_string("Dupliquer le mois", 
                                                "Entrez le nom pour la copie :", 
                                                default_name)

            if not new_name:
                return

            result = self.model.duplicate_mois(new_name)
            self._handle_result(result)

            if result.is_success:
                self.model.load_mois(new_name)

        except Exception as e:
            logger.error(f"Erreur lors de la duplication du mois: {e}")
            self.view.show_error_message("Une erreur inattendue est survenue lors de la duplication.")
    
    def handle_rename_mois(self):
        """Gère le renommage du mois actuel."""
        if not self.model.mois_actuel:
            self.view.show_warning_message("Veuillez charger un mois avant de le renommer.")
            return

        try:
            current_name = self.model.mois_actuel.nom
            new_name = self.view.ask_for_string("Renommer le mois",
                                                f"Entrez le nouveau nom pour '{current_name}':",
                                                current_name)

            if not new_name or new_name == current_name:
                return

            result = self.model.rename_mois(new_name)
            self._handle_result(result)

        except Exception as e:
            logger.error(f"Erreur lors du renommage du mois: {e}")
            self.view.show_error_message("Une erreur inattendue est survenue lors du renommage.")


    # ===== GESTION DU SALAIRE =====
    def handle_salaire_update(self, *args):
        """Gère la mise à jour du salaire"""
        try:
            salaire_str = self.view.get_salaire_value()
            result = self.model.set_salaire(salaire_str)
            
            if not result.is_success:
                logger.warning(f"Erreur lors de la mise à jour du salaire: {result.error}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du salaire: {e}")
    
    # ===== GESTION DES DÉPENSES =====
    def handle_add_expense(self):
        """Gère l'ajout d'une nouvelle dépense"""
        try:
            if not self.model.mois_actuel:
                self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")
                return
            
            result = self.model.add_expense()
            if result.is_success:
                self.view.focus_last_expense()
                # --- MODIFICATION ---
                # Forcer le défilement vers le bas
                self.view.scroll_to_bottom()
            else:
                self._handle_result(result)
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout d'une dépense: {e}")
            self.view.show_error_message("Erreur lors de l'ajout de la dépense")
    
    def handle_expense_update(self, index: int):
        """Gère la mise à jour d'une dépense"""
        try:
            expense_data = self.view.get_expense_value(index)
            if expense_data is None:
                return
            
            nom, montant_str, categorie, effectue, emprunte = expense_data
            result = self.model.update_expense(index, nom, montant_str, categorie, effectue, emprunte)
            
            if not result.is_success:
                logger.warning(f"Erreur lors de la mise à jour de la dépense: {result.error}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la dépense: {e}")
    
    def handle_remove_expense(self, index: int):
        """Gère la suppression d'une dépense"""
        try:
            result = self.model.remove_expense(index)
            if not result.is_success:
                self._handle_result(result)
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la dépense: {e}")
            self.view.show_error_message("Erreur lors de la suppression de la dépense")
    
    def handle_sort(self):
        """Gère le tri des dépenses"""
        try:
            result = self.model.sort_depenses()
            if not result.is_success:
                self._handle_result(result)
                
        except Exception as e:
            logger.error(f"Erreur lors du tri: {e}")
            self.view.show_error_message("Erreur lors du tri des dépenses")
    
    def handle_reset(self):
        """Gère la réinitialisation de toutes les dépenses"""
        try:
            if not self.model.mois_actuel:
                return
            
            if not self.view.ask_confirmation(
                "Confirmation", 
                f"Effacer toutes les dépenses du mois '{self.model.mois_actuel.nom}' ? "
                "Cette action est irréversible."
            ):
                return
            
            result = self.model.clear_all_expenses()
            self._handle_result(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation: {e}")
            self.view.show_error_message("Erreur lors de la réinitialisation")
    
    # ===== IMPORT/EXPORT =====
    def handle_export_to_json(self):
        """Gère l'export vers JSON"""
        try:
            if not self.model.mois_actuel:
                self.view.show_warning_message("Aucun mois chargé à exporter.")
                return
            
            filepath = self.view.get_export_filepath(self.model.mois_actuel.nom)
            if not filepath:
                return
            
            result = self.model.export_to_json(filepath)
            self._handle_result(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            self.view.show_error_message("Erreur lors de l'export")
    
    def handle_import_from_json(self):
        """Gère l'import depuis JSON"""
        try:
            if not self.model.mois_actuel:
                self.view.show_warning_message("Veuillez d'abord créer ou charger un mois.")
                return
            
            filepath = self.view.get_import_filepath()
            if not filepath:
                return
            
            if not self.view.ask_confirmation(
                "Confirmation", 
                "L'import remplacera toutes les dépenses actuelles. Continuer ?"
            ):
                return
            
            result = self.model.import_from_json(filepath)
            self._handle_result(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import: {e}")
            self.view.show_error_message("Erreur lors de l'import")
    
    # ===== GRAPHIQUES =====
    def handle_show_graph(self):
        """Gère l'affichage des graphiques"""
        try:
            self.view.show_graph_window(lambda: self.model.get_graph_data())
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage des graphiques: {e}")
            self.view.show_error_message("Erreur lors de l'affichage des graphiques")
    
    # ===== MÉTHODES PRIVÉES =====
    def _handle_result(self, result: Result):
        """Gère l'affichage des résultats d'opération"""
        if result.is_success:
            if result.message:
                self.view.update_status(result.message)
        else:
            if result.error:
                self.view.show_error_message(result.error)
                self.view.update_status(f"Erreur: {result.error}")
    
    def _refresh_complete_view(self):
        """Rafraîchit complètement la vue"""
        try:
            display_data = self.model.get_display_data()
            self.view.update_complete_display(display_data, self.model.categories)
            self.view.update_status("Prêt.")
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement complet de la vue: {e}")
    
    def _refresh_summary_view(self):
        """Rafraîchit uniquement le résumé financier"""
        try:
            display_data = self.model.get_display_data()
            self.view.update_summary_display(display_data)
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du résumé: {e}")

    def handle_import_from_excel(self):
        """
        Gère l'importation optimisée de dépenses depuis un fichier Excel (.xlsx).
        Étape 1: Charge et valide toutes les données dans une liste.
        Étape 2: Envoie la liste complète au modèle pour un ajout en masse.
        Étape 3: Met à jour l'affichage une seule fois.
        """
        if pd is None:
            self.view.show_error_message(
                "La fonctionnalité d'import Excel nécessite des bibliothèques supplémentaires.\n\n"
                "Veuillez les installer en exécutant : pip install pandas openpyxl"
            )
            return

        if not self.model.is_mois_loaded():
            self.view.show_warning_message("Veuillez charger ou créer un mois avant d'importer.")
            return

        filepath = self.view.get_excel_import_filepath()
        if not filepath:
            return

        try:
            # --- PHASE 1 : Préparation des données ---
            df = pd.read_excel(filepath, header=9)
            required_columns = {'Libellé', 'Débit euros'}
            if not required_columns.issubset(df.columns):
                self.view.show_error_message(f"Fichier invalide. Les colonnes requises sont : {', '.join(required_columns)}.")
                return

            depenses_a_importer = []
            skipped_rows = 0
            for index, row in df.iterrows():
                try:
                    nom = str(row['Libellé']).strip()
                    montant_str = str(row['Débit euros']).replace(',', '.')
                    montant_float = float(montant_str)

                    if not nom or pd.isna(montant_float) or montant_float <= 0:
                        skipped_rows += 1
                        continue
                    
                    # On crée l'objet Depense mais on ne le sauvegarde pas encore
                    depense = Depense(
                        nom=nom,
                        montant=montant_float,
                        categorie="Importé",
                        effectue=False,
                        emprunte=False
                    )
                    depenses_a_importer.append(depense)

                except (ValueError, TypeError):
                    skipped_rows += 1
                    continue
            
            if not depenses_a_importer:
                self.view.show_warning_message("Aucune dépense valide (débit positif) n'a été trouvée dans le fichier.")
                return

            # --- PHASE 2 : Sauvegarde en masse via le modèle ---
               # On parcourt le tableau et on enregistre chaque dépense individuellement.
            for depense in depenses_a_importer:
                # Appel de la méthode du modèle pour chaque dépense
                result = self.model.add_expense(
                    nom=depense.nom,
                    montant_str=str(depense.montant), # Conversion du float en string
                    categorie=depense.categorie,
                    effectue=depense.effectue,
                    emprunte=depense.emprunte
                )
                
                # Si l'ajout d'une seule dépense échoue, on arrête tout le processus.
                if not result.is_success:
                    self.view.show_error_message(
                        f"L'importation a été interrompue en raison d'une erreur :\n{result.message}"
                    )
                    # On rafraîchit l'affichage pour voir ce qui a été importé jusqu'à présent
                    self._update_full_view()
                    return
                    
            # --- PHASE 3 : Mise à jour de l'affichage ---
            self._update_full_view()
            self.view.scroll_to_bottom()

            success_message = f"{len(depenses_a_importer)} dépense(s) ont été importée(s) avec succès."
            if skipped_rows > 0:
                success_message += f"\n{skipped_rows} ligne(s) ont été ignorées (crédits ou données invalides)."
            
            self.view.show_info_message(success_message)
            self.view.update_status(f"Importation depuis {filepath.name} terminée.")

        except Exception as e:
            self.view.show_error_message(f"Une erreur est survenue lors de la lecture du fichier Excel.\n\n{e}")

    

    # Assurez-vous que votre contrôleur a une méthode pour rafraîchir la vue, comme celle-ci :
    def _update_full_view(self):
        """Met à jour l'ensemble de la vue avec les données actuelles du modèle."""
        display_data = self.model.get_display_data()
        categories = self.model.get_categories()
        self.view.update_complete_display(display_data, categories)
        self.view.update_status("Prêt.")


