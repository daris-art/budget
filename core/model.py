# core/model.py

import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import requests
from pathlib import Path 
# Imports depuis la nouvelle structure
from core.data_models import *
from core.database import DatabaseManager
from core.validation import DataValidator
from core.services import ImportExportService, BitcoinAPIService

logger = logging.getLogger(__name__)

class BudgetModel(Observable):
    def __init__(self, db_manager: DatabaseManager, validator: DataValidator, 
                 import_export_service: ImportExportService, api_service: BitcoinAPIService):
        super().__init__()
        self._db_manager = db_manager
        self._validator = validator
        self._import_export_service = import_export_service
        self._api_service = api_service

        self._displayed_depenses: List[Depense] = []  # AJOUT
        self._current_search_term: str = ""     

        self.mois_actuel: Optional[Mois] = None
        self._depenses: List[Depense] = []
        self._current_sort_key: str = "date_desc"
        self.categories = ["Alimentation", "Logement", "Transport", "Loisirs", "Santé", "Factures", "Shopping", "Épargne", "Autres"]
    
    # --- NOUVELLE MÉTHODE PUBLIQUE ---
    def filter_depenses_by_name(self, search_text: str):
        """Met à jour le terme de recherche et rafraîchit la liste affichée."""
        self._current_search_term = search_text.lower()
        self._refresh_displayed_expenses()

    # --- NOUVELLE MÉTHODE PRIVÉE ---
    # core/model.py

    # core/model.py

    def _calculate_summary_for_list(self, expense_list: List[Depense], salaire_override: float = None) -> Dict[str, float]:
        """
        Calcule les totaux pour une liste de dépenses/revenus fournie.
        Peut accepter un salaire optionnel pour les calculs en direct depuis l'interface.
        """
        total_depenses_affiches = sum(d.montant for d in expense_list if not d.est_credit)
        total_effectue_affiches = sum(d.montant for d in expense_list if d.effectue and not d.est_credit)
        total_emprunte_affiches = sum(d.montant for d in expense_list if d.emprunte)
        total_depenses_fixes_affiches = sum(d.montant for d in expense_list if not d.est_credit and d.est_fixe)
        nombre_lignes_affiches = len(expense_list)

        total_revenus_liste = sum(d.montant for d in expense_list if d.est_credit)
        
        # Utilise le salaire "override" s'il est fourni, sinon celui du modèle
        salaire_du_mois = self.salaire if salaire_override is None else salaire_override
        
        argent_restant_affiche = total_revenus_liste - total_depenses_affiches

        return {
            "nombre_depenses": nombre_lignes_affiches,
            "total_depenses": total_depenses_affiches,
            "total_effectue": total_effectue_affiches,
            "total_non_effectue": total_depenses_affiches - total_effectue_affiches,
            "total_emprunte": total_emprunte_affiches,
            "total_depenses_fixes": total_depenses_fixes_affiches,
            "total_revenus": total_revenus_liste,
            "argent_restant": argent_restant_affiche
        }

    def _refresh_displayed_expenses(self):
        """
        Applique le filtre et le tri actuels à la liste des dépenses
        et notifie la vue pour qu'elle se mette à jour.
        C'est la méthode centrale pour tout rafraîchissement de la liste.
        """
        # 1. Filtrage basé sur le terme de recherche
        if self._current_search_term:
            # On filtre la liste source (_depenses)
            temp_list = [
                d for d in self._depenses 
                if self._current_search_term in d.nom.lower()
            ]
        else:
            # Si la recherche est vide, on prend une copie de la liste complète
            temp_list = self._depenses.copy()

        # 2. Tri de la liste (filtrée ou non)
        sort_key = self._current_sort_key
        try:
            if sort_key == "montant_desc":
                temp_list.sort(key=lambda d: d.montant, reverse=True)
            elif sort_key == "montant_asc":
                temp_list.sort(key=lambda d: d.montant)
            elif sort_key == "date_desc":
                temp_list.sort(key=lambda d: datetime.strptime(d.date_depense, '%d/%m/%Y'), reverse=True)
            elif sort_key == "date_asc":
                temp_list.sort(key=lambda d: datetime.strptime(d.date_depense, '%d/%m/%Y'))
            elif sort_key == "nom_asc":
                temp_list.sort(key=lambda d: d.nom.lower())
            elif sort_key == "nom_desc":
                temp_list.sort(key=lambda d: d.nom.lower(), reverse=True)
            elif sort_key == "effectue_desc":
                temp_list.sort(key=lambda d: d.effectue, reverse=True)
            elif sort_key == "effectue_asc":
                temp_list.sort(key=lambda d: d.effectue)
            elif sort_key == "est_fixe_desc":
                temp_list.sort(key=lambda d: d.est_fixe, reverse=True)
            elif sort_key == "type":
                temp_list.sort(key=lambda d: (not d.est_credit, d.nom))
            else: # Tri par défaut
                temp_list.sort(key=lambda d: datetime.strptime(d.date_depense, '%d/%m/%Y'), reverse=True)
        except (ValueError, TypeError) as e:
            logger.error(f"Erreur de tri lors du rafraîchissement: {e}")

        # Mise à jour de la liste qui sera affichée
        self._displayed_depenses = temp_list
        
        # 3. Calcul du résumé pour la liste filtrée et triée
        summary_for_display = self._calculate_summary_for_list(self._displayed_depenses)
        
        # 4. Notification à la vue avec un paquet de données complet
        update_data = {
            'expenses': self._displayed_depenses,
            'summary': summary_for_display
        }
        self.notify_observers('display_updated', update_data)

    def get_nombre_depenses(self) -> int:
        """Retourne le nombre total de dépenses pour le mois actuel."""
        return len(self._depenses)
    
    def get_bitcoin_price(self) -> Result:
        """Délègue l'appel API au service concerné."""
        return self._api_service.get_price()
       
    def get_bitcoin_price(self) -> Result:
        """
        Récupère le prix actuel du Bitcoin en Euros via l'API CoinGecko.
        """
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin",
            "vs_currencies": "eur"
        }
        try:
            # On met un timeout pour ne pas attendre indéfiniment
            response = requests.get(url, params=params, timeout=10)
            # Lève une exception si la requête a échoué (ex: erreur 404, 500)
            response.raise_for_status()
            
            data = response.json()
            
            # On extrait le prix de la réponse JSON : {"bitcoin":{"eur":60000.12}}
            price = data.get("bitcoin", {}).get("eur")
            
            if price is None:
                return Result.error("Format de réponse de l'API inattendu.")
            
            return Result.success(data=price)

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau lors de la récupération du prix du BTC: {e}")
            return Result.error("Erreur réseau. Vérifiez votre connexion.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du prix du BTC: {e}")
            return Result.error("Une erreur inattendue est survenue.")

    def get_total_revenus(self) -> float:
        """Retourne le total des revenus (opérations de crédit)."""
        return sum(d.montant for d in self._depenses if d.est_credit)

    def get_total_depenses_fixes(self) -> float:
        """Retourne le total des dépenses marquées comme fixes."""
        return sum(d.montant for d in self._depenses if not d.est_credit and d.est_fixe)


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

            self._refresh_displayed_expenses() # Rafraîchit l'affichage
            
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

            self._displayed_depenses = depenses.copy()

            self._current_search_term = "" # On réinitialise la recherche
            self._refresh_displayed_expenses() # On met à jour l'affichage
        
            
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

    def duplicate_mois(self, new_name: str, reset_status: bool = False) -> Result:
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
            
            # On délègue la logique de bas niveau au DatabaseManager
            result = self._db_manager.duplicate_mois(self.mois_actuel.id, new_name.strip())
            
            # --- CORRECTION ---
            if result.is_success:
                # Si la duplication réussit, on charge ce nouveau mois pour l'afficher.
                # La méthode load_mois s'occupe déjà d'envoyer la bonne notification
                # à la vue pour qu'elle se mette à jour complètement.
                self.load_mois(new_name.strip())
            
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
               emprunte: bool = False, est_fixe: bool = False) -> Result:
        """
        MODIFICATION: Supprime l'appel redondant à _refresh_displayed_expenses.
        """
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
                emprunte=emprunte,
                est_fixe=est_fixe
            )
            
            depense_id = self._db_manager.create_depense(self.mois_actuel.id, depense)
            depense.id = depense_id
            
            self._depenses.append(depense)
            # AJOUT: Ajouter aussi à la liste affichée si elle correspond aux critères de filtrage
            if not self._current_search_term or self._current_search_term in depense.nom.lower():
                self._displayed_depenses.append(depense)
            
            # SUPPRESSION: Plus d'appel à _refresh_displayed_expenses
            self.notify_observers('expense_added', depense)
            
            return Result.success("Dépense ajoutée")
            
        except DatabaseError as e:
            logger.error(f"Erreur DB lors ajout dépense: {e}")
            return Result.error("Erreur lors de l'ajout de la dépense")
        except Exception as e:
            logger.critical(f"Erreur inattendue lors ajout dépense: {e}")
            return Result.error("Une erreur inattendue s'est produite")

    def update_expense(self, index: int, nom: str, montant_str: str, date_depense: str, 
                 categorie: str, effectue: bool, emprunte: bool, est_fixe: bool) -> Result:
        """
        MODIFICATION: Ne déclenche plus _refresh_displayed_expenses pour éviter 
        le rafraîchissement complet de la liste.
        """
        
        if not (0 <= index < len(self._displayed_depenses)):
            return Result.error("Index de dépense invalide.")
        
        depense_a_mettre_a_jour_id = self._displayed_depenses[index].id
        
        # Trouve la dépense correspondante dans la liste source
        original_depense = next((d for d in self._depenses if d.id == depense_a_mettre_a_jour_id), None)
        if not original_depense:
            return Result.error("Impossible de trouver la dépense originale à mettre à jour.")

        validation = self._validator.validate_expense_data(nom, montant_str, categorie)
        if not validation.is_valid:
            return Result.error("\n".join(validation.errors))

        # Met à jour l'objet original
        original_depense.nom = validation.validated_data['nom']
        original_depense.montant = validation.validated_data['montant']
        original_depense.categorie = validation.validated_data['categorie']
        original_depense.date_depense = date_depense
        original_depense.effectue = effectue
        original_depense.emprunte = emprunte
        original_depense.est_fixe = est_fixe

        try:
            self._db_manager.update_depense(original_depense)
            
            # MODIFICATION CRUCIALE: On met aussi à jour la liste affichée
            # pour que les deux listes restent synchronisées
            displayed_depense = self._displayed_depenses[index]
            displayed_depense.nom = validation.validated_data['nom']
            displayed_depense.montant = validation.validated_data['montant']
            displayed_depense.categorie = validation.validated_data['categorie']
            displayed_depense.date_depense = date_depense
            displayed_depense.effectue = effectue
            displayed_depense.emprunte = emprunte
            displayed_depense.est_fixe = est_fixe
            
            # SUPPRESSION: Plus de _refresh_displayed_expenses() qui provoquait le scintillement
            # La mise à jour des totaux sera gérée par le contrôleur
            
            return Result.success()
        except DatabaseError as e:
            return Result.error(str(e))
            
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
    
    # Dans model.py, remplacez la méthode sort_depenses

    def sort_depenses(self, sort_key: str) -> Result:
        """Met à jour la clé de tri et rafraîchit la liste."""
        self._current_sort_key = sort_key
        self._refresh_displayed_expenses()
        return Result.success()
            
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
        """Retourne le total des dépenses (opérations de débit uniquement)."""
        # On ne somme que les montants où 'est_credit' est False
        return sum(d.montant for d in self._depenses if not d.est_credit)

    def get_total_depenses_effectuees(self) -> float:
        """Retourne le total des dépenses effectuées (débits uniquement)."""
        # On ajoute la condition 'not d.est_credit'
        return sum(d.montant for d in self._depenses if d.effectue and not d.est_credit)

    def get_total_depenses_non_effectuees(self) -> float:
        """Retourne le total des dépenses prévues (débits uniquement)."""
        total_depenses = self.get_total_depenses()
        total_effectue = self.get_total_depenses_effectuees()
        return total_depenses - total_effectue
    
    def get_total_emprunte(self) -> float:
        return sum(d.montant for d in self._depenses if d.emprunte)
    
    def get_argent_restant(self) -> float:
        """Calcule l'argent restant comme : total_revenus - total_dépenses"""
        return self.get_total_revenus() - self.get_total_depenses()


    def get_display_data(self) -> Optional[MoisDisplayData]:
        """Retourne un DTO avec toutes les données nécessaires pour l'affichage complet."""
        if not self.mois_actuel:
            return None
        
        total_depenses = self.get_total_depenses()
        total_effectue = self.get_total_depenses_effectuees()
        
        return MoisDisplayData(
            nom=self.mois_actuel.nom,
            salaire=self.salaire,
            nombre_depenses=len(self._depenses), # <-- Ajout ici
            depenses=self._displayed_depenses, 
            total_depenses=total_depenses,
            argent_restant=self.salaire - total_depenses,
            total_effectue=total_effectue,
            total_non_effectue=total_depenses - total_effectue,
            total_emprunte=self.get_total_emprunte(),
            total_revenus=self.get_total_revenus(),
            total_depenses_fixes=self.get_total_depenses_fixes()
        )
    
    def get_summary_data(self) -> Dict[str, float]:
        """
        Retourne un dictionnaire avec toutes les données agrégées
        pour le récapitulatif.
        """
        return {
            "nombre_depenses": self.get_nombre_depenses(),
            "total_depenses": self.get_total_depenses(),
            "argent_restant": self.get_argent_restant(),
            "total_effectue": self.get_total_depenses_effectuees(),
            "total_non_effectue": self.get_total_depenses_non_effectuees(),
            "total_emprunte": self.get_total_emprunte(),
            "total_revenus": self.get_total_revenus(),
            "total_depenses_fixes": self.get_total_depenses_fixes()
        }
    
    def get_graph_data(self) -> Tuple[List[str], List[float], float, Dict[str, float]]:
        """
        Prépare les données pour les graphiques en excluant les crédits (revenus)
        et en tronquant les libellés trop longs.
        """
        valid_expenses = [
            d for d in self._depenses 
            if d.montant > 0 and d.nom.strip() and not d.est_credit
        ]
        
        if not valid_expenses:
            return [], [], 0.0, {}
        
        # --- MODIFICATION 1 : Tronquer les noms de dépenses pour le graphique en barres ---
        # On utilise une expression conditionnelle pour ajouter "..." uniquement si le nom est trop long.
        labels = [
            (d.nom[:21] + '...') if len(d.nom) > 21 else d.nom 
            for d in valid_expenses
        ]

        values = [d.montant for d in valid_expenses]
        argent_restant = self.get_argent_restant()
        
        categories_data = {}
        for d in valid_expenses:
            # --- MODIFICATION 2 : Tronquer les noms de catégories pour le camembert ---
            categorie_label = (d.categorie[:21] + '...') if len(d.categorie) > 21 else d.categorie
            categories_data[categorie_label] = categories_data.get(categorie_label, 0) + d.montant
        
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

    # Dans model.py, remplacez la méthode import_from_excel

    def import_from_excel(self, filepath: Path, new_mois_name: str, progress_callback=None) -> Result:
        """
        Gère l'importation d'un fichier Excel 
        """
        try:
            if not new_mois_name or not new_mois_name.strip():
                return Result.error("Le nom du nouveau mois ne peut pas être vide.")

            result = self._import_export_service.import_from_excel(filepath, new_mois_name.strip())   
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