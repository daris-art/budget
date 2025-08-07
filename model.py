# model.py (version mise à jour)

from pathlib import Path
import logging
from typing import List, Optional, Dict, Any, Tuple

from utils import (
    DatabaseManager, DataValidator, ImportExportService, Result,
    Depense, Mois, MoisDisplayData, Observable, DatabaseError
)

logger = logging.getLogger(__name__)

class BudgetModel(Observable):
    """
    Responsable uniquement de la logique métier de l'application de budget.
    """
    def __init__(self):
        super().__init__()
        # On utilise expanduser() pour résoudre le '~' et trouver le dossier personnel
        app_dir = Path.home() / ".BudgetApp"
        # On s'assure que le dossier existe
        app_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = app_dir / "budget.db"

        self._db_manager: Optional[DatabaseManager] = None
        self._validator: Optional[DataValidator] = None
        self._import_export_service: Optional[ImportExportService] = None

        self.mois_actuel: Optional[Mois] = None
        self._depenses: List[Depense] = []
        self.categories = ["Alimentation", "Logement", "Transport", "Loisirs", "Santé", "Factures", "Shopping", "Épargne", "Autres"]

        logger.info("BudgetModel instancié (backend non initialisé)")

    def get_nombre_depenses(self) -> int:
        """Retourne le nombre total de dépenses pour le mois actuel."""
        return len(self._depenses)

    def update_expense(self, index: int, nom: str, montant_str: str, categorie: str, effectue: bool, emprunte: bool) -> Result:
        """Met à jour une dépense existante."""
        if not (0 <= index < len(self._depenses)):
            return Result.error("Index de dépense invalide")

        validation = self._validator.validate_expense_data(nom, montant_str, categorie)
        if not validation.is_valid:
            return Result.error("\n".join(validation.errors))

        depense_a_jour = self._depenses[index]
        depense_a_jour.nom = validation.validated_data['nom']
        depense_a_jour.montant = validation.validated_data['montant']
        depense_a_jour.categorie = validation.validated_data['categorie']
        depense_a_jour.effectue = effectue
        depense_a_jour.emprunte = emprunte

        try:
            self._db_manager.update_depense(depense_a_jour)
            self.notify_observers('expense_updated', {'index': index, 'depense': depense_a_jour})
            return Result.success()
        except DatabaseError as e:
            return Result.error(str(e))

    # --- CORRECTION 2 : Suppression par ID ---
    def remove_expense_by_id(self, depense_id: int) -> Result:
        """Supprime une dépense en utilisant son ID unique."""
        try:
            # On supprime d'abord de la base de données
            self._db_manager.delete_depense(depense_id)

            # Ensuite, on met à jour notre liste en mémoire
            # On cherche l'index de la dépense avec cet ID pour la notifier à la vue
            index_to_remove = -1
            for i, dep in enumerate(self._depenses):
                if dep.id == depense_id:
                    index_to_remove = i
                    break
            
            if index_to_remove != -1:
                self._depenses.pop(index_to_remove)
                # On notifie la vue pour qu'elle supprime la bonne ligne
                self.notify_observers('expense_removed', {'index': index_to_remove})
            
            return Result.success()
        except DatabaseError as e:
            return Result.error(str(e))

    def initialize_backend(self):
        """Initialise les composants du backend."""
        if not self._db_manager:
            self._db_manager = DatabaseManager(self.db_path)
            self._validator = DataValidator()
            self._import_export_service = ImportExportService(self._db_manager)
            logger.info("Backend initialisé.")

    def _get_database_path(self) -> Path:
        """Retourne le chemin vers la base de données"""
        try:
            data_dir = Path.home() / ".BudgetApp"
            data_dir.mkdir(exist_ok=True)
            return data_dir / "budget.db"
        except Exception:
            return Path("budget.db")
    
    # ===== PROPRIÉTÉS =====
    @property
    def salaire(self) -> float:
        """Salaire du mois actuel"""
        return self.mois_actuel.salaire if self.mois_actuel else 0.0
    
    @property
    def depenses(self) -> List[Depense]:
        """Liste des dépenses actuelles (lecture seule)"""
        return self._depenses.copy()
    
    # ===== GESTION DES MOIS =====
    def create_mois(self, nom: str, salaire_str: str) -> Result:
        """Crée un nouveau mois avec validation complète"""
        try:
            validation_result = self._validator.validate_mois_data(nom, salaire_str)
            if not validation_result.is_valid:
                return Result.error("; ".join(validation_result.errors))
            
            mois_id = self._db_manager.create_mois(
                validation_result.validated_data['nom'],
                validation_result.validated_data['salaire']
            )
            
            self.mois_actuel = Mois(
                nom=validation_result.validated_data['nom'],
                salaire=validation_result.validated_data['salaire'],
                id=mois_id
            )
            self._depenses = []
            
            self._save_last_mois(self.mois_actuel.nom)
            self.notify_observers('mois_created', self.mois_actuel)
            return Result.success(f"Mois '{nom}' créé avec succès")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors création mois: {e}")
            return Result.error(str(e))
        except Exception as e:
            logger.critical(f"Erreur inattendue lors création mois: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    def load_mois(self, nom: str) -> Result:
        """Charge un mois existant"""
        try:
            mois = self._db_manager.get_mois_by_name(nom)
            if not mois:
                return Result.error(f"Mois '{nom}' non trouvé")
            
            depenses = self._db_manager.get_depenses_by_mois(mois.id)
            
            self.mois_actuel = mois
            self._depenses = depenses
            
            self._save_last_mois(nom)
            self.notify_observers('mois_loaded', self.mois_actuel)
            return Result.success(f"Mois '{nom}' chargé avec succès")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors chargement mois: {e}")
            return Result.error(f"Erreur lors du chargement: {e}")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors chargement mois: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    def delete_mois(self, nom: str) -> Result:
        """Supprime un mois et toutes ses dépenses"""
        try:
            deleted = self._db_manager.delete_mois(nom)
            if not deleted:
                return Result.error(f"Mois '{nom}' non trouvé")
            
            if self.mois_actuel and self.mois_actuel.nom == nom:
                self.clear_all_data()
                self.notify_observers('mois_cleared', None)
            
            self.notify_observers('mois_deleted', nom)
            return Result.success(f"Mois '{nom}' supprimé avec succès")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors suppression mois: {e}")
            return Result.error(f"Erreur lors de la suppression: {e}")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors suppression mois: {e}")
            return Result.error("Une erreur inattendue s'est produite")

    def duplicate_mois(self, new_name: str, reset_status: bool = True) -> Result:
        """
        Duplique le mois actuel avec un nouveau nom.
        
        Args:
            new_name: Le nom pour le mois dupliqué.
            reset_status: Si True, les statuts 'effectue' et 'emprunte' sont réinitialisés.
        """
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé à dupliquer.")

        try:
            # 1. Validation du nouveau nom
            if not new_name or not new_name.strip():
                return Result.error("Le nom du nouveau mois ne peut pas être vide.")
            
            # 2. Création du nouveau mois dans la base de données
            new_mois_id = self._db_manager.create_mois(new_name, self.mois_actuel.salaire)
            
            # 3. Duplication des dépenses
            for depense in self._depenses:
                new_depense = Depense(
                    nom=depense.nom,
                    montant=depense.montant,
                    categorie=depense.categorie,
                    effectue=False if reset_status else depense.effectue,
                    emprunte=False if reset_status else depense.emprunte
                )
                self._db_manager.create_depense(new_mois_id, new_depense)
            
            # 4. Notification (sans charger le mois ici)
            self.notify_observers('mois_duplicated', {'new_name': new_name})
            
            return Result.success(f"Mois '{self.mois_actuel.nom}' dupliqué vers '{new_name}'")

        except DatabaseError as e:
            logger.error(f"Erreur DB lors de la duplication: {e}")
            return Result.error(str(e))
        except Exception as e:
            logger.critical(f"Erreur inattendue lors de la duplication: {e}")
            return Result.error("Une erreur inattendue s'est produite.")

    def get_all_mois(self) -> Result:
        """Récupère tous les mois disponibles"""
        try:
            mois_list = self._db_manager.get_all_mois()
            return Result.success("Mois récupérés", data=mois_list)
        except DatabaseError as e:
            logger.error(f"Erreur DB lors récupération mois: {e}")
            return Result.error("Erreur lors de la récupération des mois")
        
    def rename_mois(self, new_name: str) -> Result:
        """Renomme le mois actuel."""
        if not self.mois_actuel:
            return Result.error("Aucun mois n'est chargé.")

        original_name = self.mois_actuel.nom
        if original_name == new_name.strip():
            return Result.success("Le nom est identique, aucune modification n'a été apportée.")

        try:
            validation_result = self._validator.validate_mois_data(new_name, str(self.mois_actuel.salaire))
            if "Le nom du mois est requis" in validation_result.errors:
                 return Result.error("Le nouveau nom ne peut pas être vide.")

            validated_new_name = validation_result.validated_data['nom']

            self._db_manager.update_mois_name(self.mois_actuel.id, validated_new_name)
            self.mois_actuel.nom = validated_new_name
            self._save_last_mois(validated_new_name)

            self.notify_observers('mois_renamed', {'new_name': validated_new_name})
            return Result.success(f"Mois '{original_name}' renommé en '{validated_new_name}'.")

        except DatabaseError as e:
            logger.error(f"Erreur DB lors du renommage: {e}")
            return Result.error(str(e))
        except Exception as e:
            logger.critical(f"Erreur inattendue lors du renommage: {e}")
            return Result.error("Une erreur inattendue est survenue.")

    
    # ===== GESTION DU SALAIRE =====
    def set_salaire(self, salaire_str: str) -> Result:
        """Met à jour le salaire du mois actuel"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé")
        
        try:
            validation_result = self._validator.validate_mois_data(
                self.mois_actuel.nom, salaire_str
            )
            
            if not validation_result.is_valid:
                try:
                    salaire = float(salaire_str.replace(',', '.')) if salaire_str else 0.0
                    if salaire < 0:
                        return Result.error("Le salaire ne peut pas être négatif")
                except (ValueError, AttributeError):
                    return Result.error("Le salaire doit être un nombre valide")
            else:
                salaire = validation_result.validated_data['salaire']
            
            self.mois_actuel.salaire = salaire
            self._db_manager.update_mois_salaire(self.mois_actuel.id, salaire)
            
            self.notify_observers('salaire_updated', salaire)
            return Result.success("Salaire mis à jour")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors mise à jour salaire: {e}")
            return Result.error("Erreur lors de la mise à jour du salaire")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors mise à jour salaire: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    # ===== GESTION DES DÉPENSES =====
    def add_expense(self, nom: str = "", montant_str: str = "0", 
                   categorie: str = "Autres", effectue: bool = False, 
                   emprunte: bool = False) -> Result:
        """Ajoute une nouvelle dépense"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé")
        
        try:
            validation_result = self._validator.validate_expense_data(nom, montant_str, categorie)
            if not validation_result.is_valid:
                logger.warning(f"Données de dépense partiellement invalides: {validation_result.errors}")
            
            depense = Depense(
                nom=validation_result.validated_data.get('nom', nom),
                montant=validation_result.validated_data.get('montant', 0.0),
                categorie=validation_result.validated_data.get('categorie', categorie),
                effectue=effectue,
                emprunte=emprunte
            )
            
            depense_id = self._db_manager.create_depense(self.mois_actuel.id, depense)
            depense.id = depense_id
            
            self._depenses.append(depense)
            
            self.notify_observers('expense_added', depense)
            return Result.success("Dépense ajoutée")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors ajout dépense: {e}")
            return Result.error("Erreur lors de l'ajout de la dépense")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors ajout dépense: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    def update_expense(self, index: int, nom: str, montant_str: str, 
                      categorie: str, effectue: bool, emprunte: bool) -> Result:
        """Met à jour une dépense"""
        if not (0 <= index < len(self._depenses)):
            return Result.error("Index de dépense invalide")
        
        try:
            validation_result = self._validator.validate_expense_data(nom, montant_str, categorie)
            if not validation_result.is_valid:
                logger.warning(f"Données de dépense partiellement invalides: {validation_result.errors}")
            
            depense = self._depenses[index]
            depense.nom = validation_result.validated_data.get('nom', nom)
            depense.montant = validation_result.validated_data.get('montant', 0.0)
            depense.categorie = validation_result.validated_data.get('categorie', categorie)
            depense.effectue = effectue
            depense.emprunte = emprunte
            
            self._db_manager.update_depense(depense)
            
            self.notify_observers('expense_updated', {'index': index, 'depense': depense})
            return Result.success("Dépense mise à jour")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors mise à jour dépense: {e}")
            return Result.error("Erreur lors de la mise à jour de la dépense")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors mise à jour dépense: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    def remove_expense(self, index: int) -> Result:
        """Supprime une dépense"""
        if not (0 <= index < len(self._depenses)):
            return Result.error("Index de dépense invalide")
        
        try:
            depense = self._depenses[index]
            if depense.id:
                self._db_manager.delete_depense(depense.id)
            
            removed_depense = self._depenses.pop(index)
            
            self.notify_observers('expense_removed', {'index': index, 'depense': removed_depense})
            return Result.success("Dépense supprimée")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors suppression dépense: {e}")
            return Result.error("Erreur lors de la suppression de la dépense")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors suppression dépense: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    def sort_depenses(self) -> Result:
        """Trie les dépenses par montant décroissant"""
        try:
            self._depenses.sort(key=lambda d: d.montant, reverse=True)
            self.notify_observers('expenses_sorted', self._depenses)
            return Result.success("Dépenses triées")
        except Exception as e:
            logger.error(f"Erreur lors du tri des dépenses: {e}")
            return Result.error("Erreur lors du tri")
    
    def clear_all_expenses(self) -> Result:
        """Supprime toutes les dépenses du mois actuel"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé")
        
        try:
            self._db_manager.delete_all_depenses_by_mois(self.mois_actuel.id)
            self._depenses.clear()
            
            self.notify_observers('all_expenses_cleared', None)
            return Result.success("Toutes les dépenses ont été supprimées")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors suppression toutes dépenses: {e}")
            return Result.error("Erreur lors de la suppression des dépenses")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors suppression toutes dépenses: {e}")
            return Result.error("Une erreur inattendue s'est produite")
    
    # ===== CALCULS FINANCIERS =====
    def get_total_depenses(self) -> float:
        return sum(d.montant for d in self._depenses)
    
    def get_argent_restant(self) -> float:
        return self.salaire - self.get_total_depenses()
    
    def get_total_depenses_effectuees(self) -> float:
        return sum(d.montant for d in self._depenses if d.effectue)
    
    def get_total_depenses_non_effectuees(self) -> float:
        return sum(d.montant for d in self._depenses if not d.effectue)
    
    def get_total_emprunte(self) -> float:
        return sum(d.montant for d in self._depenses if d.emprunte)

    def get_display_data(self) -> Optional[MoisDisplayData]:
        """Retourne un DTO avec toutes les données nécessaires pour l'affichage complet."""
        if not self.mois_actuel:
            return None
        
        total_depenses = self.get_total_depenses()
        total_effectue = self.get_total_depenses_effectuees()
        
        return MoisDisplayData(
            nom=self.mois_actuel.nom,
            salaire=self.salaire,
            depenses=self._depenses,
            nombre_depenses=len(self._depenses), # <-- Ajout ici
            total_depenses=total_depenses,
            argent_restant=self.salaire - total_depenses,
            total_effectue=total_effectue,
            total_non_effectue=total_depenses - total_effectue,
            total_emprunte=self.get_total_emprunte()
        )
    
    def get_graph_data(self) -> Tuple[List[str], List[float], float, Dict[str, float]]:
        valid_expenses = [d for d in self._depenses if d.montant > 0 and d.nom.strip()]
        if not valid_expenses:
            return [], [], 0.0, {}
        
        labels = [d.nom for d in valid_expenses]
        values = [d.montant for d in valid_expenses]
        argent_restant = self.get_argent_restant()
        
        categories_data = {}
        for d in valid_expenses:
            categories_data[d.categorie] = categories_data.get(d.categorie, 0) + d.montant
        
        return labels, values, argent_restant, categories_data
    
    # ===== IMPORT/EXPORT =====
    def export_to_json(self, filepath: Path) -> Result:
        """Orchestre l'export du mois actuel vers un fichier JSON."""
        if not self.mois_actuel:
            return Result.error("Aucun mois n'est chargé pour l'export.")
        
        # S'assure qu'un nom de fichier a une extension .json
        if not filepath.name.endswith('.json'):
            filepath = filepath.with_suffix('.json')
            
        return self._import_export_service.export_to_json(self.mois_actuel.id, filepath)

    def import_from_json(self, filepath: Path, new_mois_name: str) -> Result:
        """Orchestre l'import d'un fichier JSON comme un nouveau mois."""
        if not new_mois_name or not new_mois_name.strip():
            return Result.error("Le nom du nouveau mois ne peut pas être vide.")

        result = self._import_export_service.import_from_json(filepath, new_mois_name.strip())
        
        # --- CORRECTION ---
        if result.is_success:
            # Si l'import réussit, on charge ce nouveau mois pour l'afficher.
            # La méthode load_mois s'occupe déjà d'envoyer la bonne notification
            # à la vue pour qu'elle se mette à jour complètement.
            self.load_mois(new_mois_name.strip())
        
        return result
        
    # ===== MÉTHODES DE SESSION =====
    def load_data_from_last_session(self) -> Result:
        try:
            last_mois = self._db_manager.get_config('last_mois')
            if last_mois:
                return self.load_mois(last_mois)
            else:
                result = self.get_all_mois()
                if result.is_success and result.data:
                    return self.load_mois(result.data[0].nom)
                else:
                    return Result.error("Aucun mois disponible. Créez un nouveau mois.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la dernière session: {e}")
            return Result.error("Erreur lors du chargement de la session précédente")
    
    def clear_all_data(self):
        self.mois_actuel = None
        self._depenses.clear()
        logger.info("Données locales réinitialisées")
    
    # ===== MÉTHODES PRIVÉES =====
    def _save_last_mois(self, nom_mois: str):
        try:
            self._db_manager.save_config('last_mois', nom_mois)
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder le dernier mois: {e}")
    
    def _reload_current_mois_data(self):
        if self.mois_actuel:
            try:
                mois = self._db_manager.get_mois_by_name(self.mois_actuel.nom)
                if mois:
                    self.mois_actuel = mois
                
                self._depenses = self._db_manager.get_depenses_by_mois(self.mois_actuel.id)
                logger.info(f"Données du mois '{self.mois_actuel.nom}' rechargées")
            except Exception as e:
                logger.error(f"Erreur lors du rechargement des données: {e}")
    
    # ===== MÉTHODES DE DEBUG =====
    def get_model_state(self) -> Dict[str, Any]:
        return {
            'mois_actuel': self.mois_actuel,
            'nombre_depenses': len(self._depenses),
            'total_depenses': self.get_total_depenses(),
            'argent_restant': self.get_argent_restant()
        }

    def import_from_excel(self, filepath: Path, new_mois_name: str) -> Result:
        """
        Gère l'importation d'un fichier Excel pour créer un nouveau mois de dépenses.
        """
        try:
            # Valider le nom du nouveau mois
            if not new_mois_name or not new_mois_name.strip():
                return Result.error("Le nom du nouveau mois ne peut pas être vide.")

            # Déléguer l'ensemble du processus au service d'import/export
            result = self._import_export_service.import_from_excel(filepath, new_mois_name.strip())
            
            if result.is_success:
                # Si l'import réussit, on charge ce nouveau mois pour l'afficher
                self.load_mois(new_mois_name.strip())
                # La méthode load_mois s'occupe déjà de notifier les observateurs
            
            return result

        except Exception as e:
            logger.critical(f"Erreur inattendue lors de l'import Excel: {e}")
            return Result.error("Une erreur inattendue s'est produite lors de l'import.")
        
    # AJOUT : Méthodes pour gérer le thème
    def save_theme_preference(self, theme: str):
        """Sauvegarde le thème préféré ('light' or 'dark') dans la config."""
        try:
            self._db_manager.save_config('theme', theme)
            # On notifie les observateurs que le thème a changé
            self.notify_observers('theme_changed', theme)
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder la préférence de thème : {e}")

    def get_theme_preference(self) -> str:
        """Récupère le thème préféré depuis la config, défaut sur 'light'."""
        try:
            theme = self._db_manager.get_config('theme')
            return theme if theme in ['light', 'dark'] else 'light'
        except Exception as e:
            logger.warning(f"Impossible de récupérer la préférence de thème : {e}")
            return 'light'