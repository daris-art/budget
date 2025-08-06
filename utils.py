# utils.py - Classes de support pour l'architecture améliorée

import sqlite3
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== EXCEPTIONS PERSONNALISÉES =====
class BudgetAppError(Exception):
    """Exception de base de l'application"""
    pass

class DatabaseError(BudgetAppError):
    """Erreurs liées à la base de données"""
    pass

class ValidationError(BudgetAppError):
    """Erreurs de validation"""
    pass

class ImportExportError(BudgetAppError):
    """Erreurs d'import/export"""
    pass

# ===== CLASSES DE RÉSULTAT =====
@dataclass
class Result:
    """Classe pour encapsuler les résultats d'opérations"""
    is_success: bool
    message: str = ""
    error: str = ""
    data: Any = None
    
    @classmethod
    def success(cls, message: str = "", data: Any = None) -> 'Result':
        return cls(is_success=True, message=message, data=data)
    
    @classmethod
    def error(cls, error: str) -> 'Result':
        return cls(is_success=False, error=error)

@dataclass
class ValidationResult:
    """Résultat de validation des données"""
    is_valid: bool
    errors: List[str]
    validated_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validated_data is None:
            self.validated_data = {}

# ===== ENTITÉS DE DONNÉES =====
@dataclass
class Depense:
    nom: str = ""
    montant: float = 0.0
    categorie: str = "Autres"
    effectue: bool = False
    emprunte: bool = False
    id: Optional[int] = None

@dataclass
class Mois:
    nom: str
    salaire: float = 0.0
    date_creation: Optional[str] = None
    id: Optional[int] = None

@dataclass
class MoisInput:
    """DTO pour l'input de création de mois"""
    nom: str
    salaire: str

@dataclass
class MoisDisplayData:
    """DTO pour l'affichage des données de mois"""
    nom: str
    salaire: float
    depenses: List[Depense]
    total_depenses: float
    argent_restant: float
    total_effectue: float
    total_non_effectue: float
    total_emprunte: float

# ===== VALIDATEUR DE DONNÉES =====
class DataValidator:
    """Validation centralisée des données"""
    
    @staticmethod
    def validate_mois_data(nom: str, salaire: str) -> ValidationResult:
        """Valide les données de création d'un mois"""
        errors = []
        validated_data = {}
        
        # Validation du nom
        if not nom or not nom.strip():
            errors.append("Le nom du mois est requis")
        else:
            validated_data['nom'] = nom.strip()
        
        # Validation du salaire
        try:
            validated_salaire = float(salaire.replace(',', '.')) if salaire else 0.0
            if validated_salaire < 0:
                errors.append("Le salaire ne peut pas être négatif")
            validated_data['salaire'] = validated_salaire
        except (ValueError, AttributeError):
            errors.append("Le salaire doit être un nombre valide")
            validated_data['salaire'] = 0.0
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            validated_data=validated_data
        )
    
    @staticmethod
    def validate_expense_data(nom: str, montant: str, categorie: str) -> ValidationResult:
        """Valide les données d'une dépense"""
        errors = []
        validated_data = {}
        
        # Validation du nom (optionnel)
        validated_data['nom'] = nom.strip() if nom else ""
        
        # Validation du montant
        try:
            validated_montant = float(montant.replace(',', '.')) if montant else 0.0
            if validated_montant < 0:
                errors.append("Le montant ne peut pas être négatif")
            validated_data['montant'] = validated_montant
        except (ValueError, AttributeError):
            errors.append("Le montant doit être un nombre valide")
            validated_data['montant'] = 0.0
        
        # Validation de la catégorie
        validated_data['categorie'] = categorie if categorie else "Autres"
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            validated_data=validated_data
        )

# ===== GESTIONNAIRE DE BASE DE DONNÉES =====
class DatabaseManager:
    """Responsable uniquement des opérations SQLite"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données et crée les tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mois (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom TEXT UNIQUE NOT NULL,
                        salaire REAL NOT NULL DEFAULT 0.0,
                        date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS depenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mois_id INTEGER NOT NULL,
                        nom TEXT NOT NULL DEFAULT '',
                        montant REAL NOT NULL DEFAULT 0.0,
                        categorie TEXT NOT NULL DEFAULT 'Autres',
                        effectue BOOLEAN NOT NULL DEFAULT 0,
                        emprunte BOOLEAN NOT NULL DEFAULT 0,
                        FOREIGN KEY (mois_id) REFERENCES mois (id) ON DELETE CASCADE
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config (
                        cle TEXT PRIMARY KEY,
                        valeur TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de l'initialisation de la base de données: {e}")
    
    def create_mois(self, nom: str, salaire: float) -> int:
        """Crée un mois et retourne son ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO mois (nom, salaire) VALUES (?, ?)',
                    (nom, salaire)
                )
                mois_id = cursor.lastrowid
                conn.commit()
                return mois_id
        except sqlite3.IntegrityError:
            raise DatabaseError(f"Le mois '{nom}' existe déjà")
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la création du mois: {e}")
    
    def get_all_mois(self) -> List[Mois]:
        """Récupère tous les mois"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois ORDER BY date_creation DESC')
                rows = cursor.fetchall()
                return [Mois(nom=row[1], salaire=row[2], date_creation=row[3], id=row[0]) for row in rows]
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la récupération des mois: {e}")
    
    def get_mois_by_name(self, nom: str) -> Optional[Mois]:
        """Récupère un mois par son nom"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois WHERE nom = ?', (nom,))
                row = cursor.fetchone()
                if row:
                    return Mois(nom=row[1], salaire=row[2], date_creation=row[3], id=row[0])
                return None
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la récupération du mois: {e}")
    
    def delete_mois(self, nom: str) -> bool:
        """Supprime un mois"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM mois WHERE nom = ?', (nom,))
                deleted = cursor.rowcount > 0
                conn.commit()
                return deleted
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la suppression du mois: {e}")
    
    def update_mois_salaire(self, mois_id: int, salaire: float):
        """Met à jour le salaire d'un mois"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE mois SET salaire = ? WHERE id = ?', (salaire, mois_id))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la mise à jour du salaire: {e}")
        
    def update_mois_name(self, mois_id: int, new_name: str):
        """Met à jour le nom d'un mois."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE mois SET nom = ? WHERE id = ?', (new_name, mois_id))
                conn.commit()
        except sqlite3.IntegrityError:
            raise DatabaseError(f"Le nom '{new_name}' existe déjà.")
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors du renommage du mois: {e}")
    
    
    def get_depenses_by_mois(self, mois_id: int) -> List[Depense]:
        """Récupère les dépenses d'un mois"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nom, montant, categorie, effectue, emprunte 
                    FROM depenses WHERE mois_id = ?
                ''', (mois_id,))
                rows = cursor.fetchall()
                return [
                    Depense(
                        nom=row[1], montant=row[2], categorie=row[3], 
                        effectue=bool(row[4]), emprunte=bool(row[5]), id=row[0]
                    )
                    for row in rows
                ]
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la récupération des dépenses: {e}")
    
    def create_depense(self, mois_id: int, depense: Depense) -> int:
        """Crée une dépense et retourne son ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO depenses (mois_id, nom, montant, categorie, effectue, emprunte)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (mois_id, depense.nom, depense.montant, depense.categorie, 
                      depense.effectue, depense.emprunte))
                depense_id = cursor.lastrowid
                conn.commit()
                return depense_id
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la création de la dépense: {e}")
    
    def update_depense(self, depense: Depense):
        """Met à jour une dépense"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE depenses 
                    SET nom = ?, montant = ?, categorie = ?, effectue = ?, emprunte = ?
                    WHERE id = ?
                ''', (depense.nom, depense.montant, depense.categorie, 
                      depense.effectue, depense.emprunte, depense.id))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la mise à jour de la dépense: {e}")
    
    def delete_depense(self, depense_id: int):
        """Supprime une dépense"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM depenses WHERE id = ?', (depense_id,))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la suppression de la dépense: {e}")
    
    def delete_all_depenses_by_mois(self, mois_id: int):
        """Supprime toutes les dépenses d'un mois"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM depenses WHERE mois_id = ?', (mois_id,))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la suppression des dépenses: {e}")
    
    def save_config(self, key: str, value: str):
        """Sauvegarde une valeur de configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO config (cle, valeur) VALUES (?, ?)',
                    (key, value)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Erreur lors de la sauvegarde de config: {e}")
    
    def get_config(self, key: str) -> Optional[str]:
        """Récupère une valeur de configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT valeur FROM config WHERE cle = ?', (key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            logger.warning(f"Erreur lors de la récupération de config: {e}")
            return None

# ===== SERVICE IMPORT/EXPORT =====
class ImportExportService:
    """Service pour l'import/export JSON"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def export_mois_to_json(self, mois: Mois, depenses: List[Depense], filepath: Path) -> Result:
        """Exporte un mois vers JSON"""
        try:
            data = {
                'mois': {
                    'nom': mois.nom,
                    'salaire': mois.salaire,
                    'date_creation': mois.date_creation
                },
                'depenses': [
                    {
                        'nom': d.nom,
                        'montant': d.montant,
                        'categorie': d.categorie,
                        'effectue': d.effectue,
                        'emprunte': d.emprunte
                    }
                    for d in depenses
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return Result.success(f"Export réussi vers {filepath.name}")
            
        except (IOError, json.JSONEncodeError) as e:
            logger.error(f"Erreur d'export: {e}")
            return Result.error(f"Erreur d'export: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'export: {e}")
            return Result.error("Erreur inattendue lors de l'export")
    
    def import_from_json(self, filepath: Path, mois_id: int) -> Result:
        """Importe des données JSON vers un mois existant"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validation de la structure
            if 'depenses' not in data:
                return Result.error("Structure JSON invalide: 'depenses' manquant")
            
            # Suppression des dépenses existantes
            self.db_manager.delete_all_depenses_by_mois(mois_id)
            
            # Import du salaire si présent
            imported_count = 0
            if 'mois' in data and 'salaire' in data['mois']:
                self.db_manager.update_mois_salaire(mois_id, data['mois']['salaire'])
            
            # Import des dépenses
            for dep_data in data['depenses']:
                depense = Depense(
                    nom=dep_data.get('nom', ''),
                    montant=dep_data.get('montant', 0.0),
                    categorie=dep_data.get('categorie', 'Autres'),
                    effectue=dep_data.get('effectue', False),
                    emprunte=dep_data.get('emprunte', False)
                )
                self.db_manager.create_depense(mois_id, depense)
                imported_count += 1
            
            return Result.success(f"Import réussi: {imported_count} dépenses importées")
            
        except FileNotFoundError:
            return Result.error("Fichier non trouvé")
        except json.JSONDecodeError as e:
            return Result.error(f"Fichier JSON invalide: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'import: {e}")
            return Result.error("Erreur inattendue lors de l'import")

# ===== PATTERN OBSERVER =====
class Observable:
    """Classe de base pour les objets observables"""
    
    def __init__(self):
        self._observers = []
    
    def add_observer(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, event_type: str, data: Any = None):
        for observer in self._observers:
            observer.on_model_changed(event_type, data)

class Observer:
    """Interface pour les observateurs"""
    
    def on_model_changed(self, event_type: str, data: Any):
        pass