# model.py - Modèle amélioré avec architecture MVC stricte

from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging

from utils import (
    Observable, Result, ValidationResult, DatabaseManager, DataValidator, 
    ImportExportService, Depense, Mois, MoisDisplayData, 
    DatabaseError, ValidationError, BudgetAppError
)

logger = logging.getLogger(__name__)

class BudgetModel(Observable):
    """
    Modèle principal de l'application - Responsable uniquement de la logique métier
    """
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.categories = [
            "Alimentation", "Logement", "Transport", "Loisirs",
            "Santé", "Factures", "Shopping", "Épargne", "Autres"
        ]
        
        # État actuel
        self.mois_actuel: Optional[Mois] = None
        self._depenses: List[Depense] = []
        
        # Services
        self._db_manager = DatabaseManager(self._get_database_path())
        self._validator = DataValidator()
        self._import_export_service = ImportExportService(self._db_manager)
        
        logger.info("BudgetModel initialisé")
    
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
            # 1. Validation des données
            validation_result = self._validator.validate_mois_data(nom, salaire_str)
            if not validation_result.is_valid:
                return Result.error("; ".join(validation_result.errors))
            
            # 2. Création en base de données
            mois_id = self._db_manager.create_mois(
                validation_result.validated_data['nom'],
                validation_result.validated_data['salaire']
            )
            
            # 3. Mise à jour de l'état local
            self.mois_actuel = Mois(
                nom=validation_result.validated_data['nom'],
                salaire=validation_result.validated_data['salaire'],
                id=mois_id
            )
            self._depenses = []
            
            # 4. Sauvegarde de la configuration
            self._save_last_mois(self.mois_actuel.nom)
            
            # 5. Notification des observateurs
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
            # 1. Récupération du mois
            mois = self._db_manager.get_mois_by_name(nom)
            if not mois:
                return Result.error(f"Mois '{nom}' non trouvé")
            
            # 2. Récupération des dépenses
            depenses = self._db_manager.get_depenses_by_mois(mois.id)
            
            # 3. Mise à jour de l'état local
            self.mois_actuel = mois
            self._depenses = depenses
            
            # 4. Sauvegarde de la configuration
            self._save_last_mois(nom)
            
            # 5. Notification des observateurs
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
            
            # Si c'est le mois actuel, réinitialiser
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
    
    def get_all_mois(self) -> Result:
        """Récupère tous les mois disponibles"""
        try:
            mois_list = self._db_manager.get_all_mois()
            return Result.success("Mois récupérés", data=mois_list)
        except DatabaseError as e:
            logger.error(f"Erreur DB lors récupération mois: {e}")
            return Result.error("Erreur lors de la récupération des mois")
    
    # ===== GESTION DU SALAIRE =====
    def set_salaire(self, salaire_str: str) -> Result:
        """Met à jour le salaire du mois actuel"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé")
        
        try:
            # Validation
            validation_result = self._validator.validate_mois_data(
                self.mois_actuel.nom, salaire_str
            )
            
            if not validation_result.is_valid:
                # Pour le salaire seul, on peut être plus tolérant
                try:
                    salaire = float(salaire_str.replace(',', '.')) if salaire_str else 0.0
                    if salaire < 0:
                        return Result.error("Le salaire ne peut pas être négatif")
                except (ValueError, AttributeError):
                    return Result.error("Le salaire doit être un nombre valide")
            else:
                salaire = validation_result.validated_data['salaire']
            
            # Mise à jour
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
            # Validation
            validation_result = self._validator.validate_expense_data(nom, montant_str, categorie)
            if not validation_result.is_valid:
                logger.warning(f"Données de dépense partiellement invalides: {validation_result.errors}")
                # On continue car les dépenses peuvent être créées vides
            
            # Création de la dépense
            depense = Depense(
                nom=validation_result.validated_data.get('nom', nom),
                montant=validation_result.validated_data.get('montant', 0.0),
                categorie=validation_result.validated_data.get('categorie', categorie),
                effectue=effectue,
                emprunte=emprunte
            )
            
            # Sauvegarde en base
            depense_id = self._db_manager.create_depense(self.mois_actuel.id, depense)
            depense.id = depense_id
            
            # Ajout à la liste locale
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
            # Validation
            validation_result = self._validator.validate_expense_data(nom, montant_str, categorie)
            if not validation_result.is_valid:
                logger.warning(f"Données de dépense partiellement invalides: {validation_result.errors}")
                # On continue avec les données validées
            
            # Mise à jour de la dépense
            depense = self._depenses[index]
            depense.nom = validation_result.validated_data.get('nom', nom)
            depense.montant = validation_result.validated_data.get('montant', 0.0)
            depense.categorie = validation_result.validated_data.get('categorie', categorie)
            depense.effectue = effectue
            depense.emprunte = emprunte
            
            # Sauvegarde en base
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
            
            # Suppression de la base de données
            if depense.id:
                self._db_manager.delete_depense(depense.id)
            
            # Suppression de la liste locale
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
            # Suppression de la base de données
            self._db_manager.delete_all_depenses_by_mois(self.mois_actuel.id)
            
            # Suppression de la liste locale
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
        """Calcule le total des dépenses"""
        return sum(d.montant for d in self._depenses)
    
    def get_argent_restant(self) -> float:
        """Calcule l'argent restant"""
        return self.salaire - self.get_total_depenses()
    
    def get_total_depenses_effectuees(self) -> float:
        """Calcule le total des dépenses effectuées"""
        return sum(d.montant for d in self._depenses if d.effectue)
    
    def get_total_depenses_non_effectuees(self) -> float:
        """Calcule le total des dépenses non effectuées"""
        return sum(d.montant for d in self._depenses if not d.effectue)
    
    def get_total_emprunte(self) -> float:
        """Calcule le total emprunté"""
        return sum(d.montant for d in self._depenses if d.emprunte)
    
    def get_display_data(self) -> MoisDisplayData:
        """Retourne les données formatées pour l'affichage"""
        return MoisDisplayData(
            nom=self.mois_actuel.nom if self.mois_actuel else "Aucun mois",
            salaire=self.salaire,
            depenses=self.depenses,
            total_depenses=self.get_total_depenses(),
            argent_restant=self.get_argent_restant(),
            total_effectue=self.get_total_depenses_effectuees(),
            total_non_effectue=self.get_total_depenses_non_effectuees(),
            total_emprunte=self.get_total_emprunte()
        )
    
    def get_graph_data(self) -> Tuple[List[str], List[float], float, Dict[str, float]]:
        """Récupère les données pour les graphiques"""
        valid_expenses = [d for d in self._depenses if d.montant > 0 and d.nom.strip()]
        
        if not valid_expenses:
            return [], [], 0.0, {}
        
        labels = [d.nom for d in valid_expenses]
        values = [d.montant for d in valid_expenses]
        argent_restant = self.get_argent_restant()
        
        # Données par catégorie
        categories_data = {}
        for d in valid_expenses:
            categories_data[d.categorie] = categories_data.get(d.categorie, 0) + d.montant
        
        return labels, values, argent_restant, categories_data
    
    # ===== IMPORT/EXPORT =====
    def export_to_json(self, filepath: Path) -> Result:
        """Exporte le mois actuel vers JSON"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé à exporter")
        
        return self._import_export_service.export_mois_to_json(
            self.mois_actuel, self._depenses, filepath
        )
    
    def import_from_json(self, filepath: Path) -> Result:
        """Importe des données JSON vers le mois actuel"""
        if not self.mois_actuel:
            return Result.error("Aucun mois chargé pour l'import")
        
        try:
            result = self._import_export_service.import_from_json(filepath, self.mois_actuel.id)
            
            if result.is_success:
                # Recharger les données locales
                self._reload_current_mois_data()
                self.notify_observers('data_imported', filepath)
            
            return result
            
        except Exception as e:
            logger.critical(f"Erreur inattendue lors import: {e}")
            return Result.error("Une erreur inattendue s'est produite lors de l'import")
    
    # ===== MÉTHODES DE SESSION =====
    def load_data_from_last_session(self) -> Result:
        """Charge le dernier mois utilisé lors de la session précédente"""
        try:
            last_mois = self._db_manager.get_config('last_mois')
            if last_mois:
                return self.load_mois(last_mois)
            else:
                # Essayer de charger le plus récent
                result = self.get_all_mois()
                if result.is_success and result.data:
                    return self.load_mois(result.data[0].nom)
                else:
                    return Result.error("Aucun mois disponible. Créez un nouveau mois.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la dernière session: {e}")
            return Result.error("Erreur lors du chargement de la session précédente")
    
    def clear_all_data(self):
        """Réinitialise toutes les données locales"""
        self.mois_actuel = None
        self._depenses.clear()
        logger.info("Données locales réinitialisées")
    
    # ===== MÉTHODES PRIVÉES =====
    def _save_last_mois(self, nom_mois: str):
        """Sauvegarde le dernier mois utilisé"""
        try:
            self._db_manager.save_config('last_mois', nom_mois)
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder le dernier mois: {e}")
    
    def _reload_current_mois_data(self):
        """Recharge les données du mois actuel depuis la base"""
        if self.mois_actuel:
            try:
                # Recharger les informations du mois
                mois = self._db_manager.get_mois_by_name(self.mois_actuel.nom)
                if mois:
                    self.mois_actuel = mois
                
                # Recharger les dépenses
                self._depenses = self._db_manager.get_depenses_by_mois(self.mois_actuel.id)
                
                logger.info(f"Données du mois '{self.mois_actuel.nom}' rechargées")
            except Exception as e:
                logger.error(f"Erreur lors du rechargement des données: {e}")
    
    # ===== MÉTHODES DE DEBUG =====
    def get_model_state(self) -> Dict[str, Any]:
        """Retourne l'état actuel du modèle (pour debug)"""
        return {
            'mois_actuel': self.mois_actuel,
            'nombre_depenses': len(self._depenses),
            'total_depenses': self.get_total_depenses(),
            'argent_restant': self.get_argent_restant()
        }