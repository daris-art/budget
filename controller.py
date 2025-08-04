# controller.py - Controller amélioré avec architecture MVC stricte

from tkinter import filedialog, simpledialog, messagebox
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import logging

from utils import Observer, Result, MoisInput
from model import BudgetModel
from view import BudgetView

logger = logging.getLogger(__name__)

class BudgetController(Observer):
    """
    Controller - Responsable uniquement de la coordination entre Vue et Modèle
    """
    
    def __init__(self, model: BudgetModel, master):
        self.model = model
        self.view = BudgetView(master, self)
        self.master = master
        
        # Inscription comme observateur du modèle
        self.model.add_observer(self)
        
        # Configuration de la fenêtre
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)
        
        # Chargement initial
        self._handle_initial_load()
        
        logger.info("BudgetController initialisé")
    
    # ===== PATTERN OBSERVER =====
    def on_model_changed(self, event_type: str, data=None):
        """Réagit aux changements du modèle"""
        try:
            if event_type in ['mois_created', 'mois_loaded', 'data_imported']:
                self._refresh_complete_view()
            elif event_type in ['expense_added', 'expense_updated', 'expense_removed', 
                              'expenses_sorted', 'all_expenses_cleared']:
                self._refresh_expenses_view()
            elif event_type == 'salaire_updated':
                self._refresh_summary_view()
            elif event_type == 'mois_cleared':
                self._refresh_complete_view()
            
            logger.debug(f"Vue mise à jour suite à l'événement: {event_type}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la vue: {e}")
            self.view.show_error_message("Erreur lors de la mise à jour de l'interface")
    
    # ===== GESTION DE L'APPLICATION =====
    def _handle_initial_load(self):
        """Gère le chargement initial de l'application"""
        try:
            result = self.model.load_data_from_last_session()
            self._handle_result(result)
            
            # Si aucun mois n'est disponible, proposer d'en créer un
            if not result.is_success and "Aucun mois disponible" in result.error:
                self.handle_create_new_mois()
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement initial: {e}")
            self.view.show_error_message("Erreur lors du chargement initial de l'application")
    
    def handle_on_closing(self):
        """Gère la fermeture de l'application"""
        try:
            plt.close('all')  # Fermer tous les graphiques matplotlib
            self.view.master.destroy()
            logger.info("Application fermée proprement")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")
            self.view.master.destroy()  # Forcer la fermeture
    
    # ===== GESTION DES MOIS =====
    def handle_create_new_mois(self):
        """Gère la création d'un nouveau mois"""
        try:
            # 1. Récupération des données utilisateur
            user_input = self.view.get_new_mois_input()
            if not user_input:
                return
            
            # 2. Délégation au modèle
            result = self.model.create_mois(user_input.nom, user_input.salaire)
            
            # 3. Gestion du résultat
            self._handle_result(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création d'un nouveau mois: {e}")
            self.view.show_error_message("Erreur lors de la création du nouveau mois")
    
    def handle_load_mois(self):
        """Gère le chargement d'un mois existant"""
        try:
            # 1. Récupération de la liste des mois
            result = self.model.get_all_mois()
            if not result.is_success:
                self._handle_result(result)
                return
            
            all_mois = result.data
            if not all_mois:
                self.view.show_info_message("Aucun mois disponible. Créez un nouveau mois.")
                return
            
            # 2. Sélection par l'utilisateur
            selected_mois = self.view.show_mois_selection_dialog(all_mois)
            if not selected_mois:
                return
            
            # 3. Chargement du mois sélectionné
            load_result = self.model.load_mois(selected_mois.nom)
            self._handle_result(load_result)
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement d'un mois: {e}")
            self.view.show_error_message("Erreur lors du chargement du mois")
    
    def handle_delete_mois(self):
        """Gère la suppression d'un mois"""
        try:
            # 1. Récupération de la liste des mois
            result = self.model.get_all_mois()
            if not result.is_success:
                self._handle_result(result)
                return
            
            all_mois = result.data
            if not all_mois:
                self.view.show_info_message("Aucun mois disponible.")
                return
            
            # 2. Avertissement si c'est le seul mois
            if len(all_mois) == 1 and self.model.mois_actuel:
                if not self.view.ask_confirmation(
                    "Confirmation", 
                    "Vous êtes sur le point de supprimer le seul mois disponible. "
                    "Cela effacera toutes vos données. Continuer ?"
                ):
                    return
            
            # 3. Sélection du mois à supprimer
            selected_mois = self.view.show_mois_selection_dialog(
                all_mois, 
                title="Supprimer un mois",
                prompt="Sélectionnez un mois à supprimer:"
            )
            if not selected_mois:
                return
            
            # 4. Confirmation finale
            if not self.view.ask_confirmation(
                "Confirmation", 
                f"Supprimer définitivement le mois '{selected_mois.nom}' ?"
            ):
                return
            
            # 5. Suppression
            delete_result = self.model.delete_mois(selected_mois.nom)
            self._handle_result(delete_result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression d'un mois: {e}")
            self.view.show_error_message("Erreur lors de la suppression du mois")
    
    # ===== GESTION DU SALAIRE =====
    def handle_salaire_update(self, *args):
        """Gère la mise à jour du salaire"""
        try:
            salaire_str = self.view.get_salaire_value()
            result = self.model.set_salaire(salaire_str)
            
            if not result.is_success:
                logger.warning(f"Erreur lors de la mise à jour du salaire: {result.error}")
                # Ne pas afficher d'erreur pour chaque frappe, juste logger
            
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
                # Donner le focus à la nouvelle dépense
                self.view.focus_last_expense()
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
            
            # Sélection du fichier
            filepath = self.view.get_export_filepath(self.model.mois_actuel.nom)
            if not filepath:
                return
            
            # Export
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
            
            # Sélection du fichier
            filepath = self.view.get_import_filepath()
            if not filepath:
                return
            
            # Confirmation
            if not self.view.ask_confirmation(
                "Confirmation", 
                "L'import remplacera toutes les dépenses actuelles. Continuer ?"
            ):
                return
            
            # Import
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
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement complet de la vue: {e}")
    
    def _refresh_expenses_view(self):
        """Rafraîchit uniquement la partie dépenses de la vue"""
        try:
            display_data = self.model.get_display_data()
            self.view.update_expenses_display(display_data.depenses, self.model.categories)
            self.view.update_summary_display(display_data)
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement des dépenses: {e}")
    
    def _refresh_summary_view(self):
        """Rafraîchit uniquement le résumé financier"""
        try:
            display_data = self.model.get_display_data()
            self.view.update_summary_display(display_data)
            self.view.set_salaire_display(display_data.salaire)
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du résumé: {e}")
    
    # ===== MÉTHODES DE DEBUG =====
    def get_controller_state(self):
        """Retourne l'état du controller (pour debug)"""
        return {
            'model_state': self.model.get_model_state(),
            'view_initialized': self.view is not None,
            'observers_count': len(self.model._observers)
        }