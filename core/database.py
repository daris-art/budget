# core/database.py

import sqlite3
from pathlib import Path
from typing import List, Optional
import logging 
from core.data_models import Depense, Mois, DatabaseError, Result

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Responsable uniquement des opérations SQLite."""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = db_path
        else:
            app_dir = Path.home() / ".BudgetApp"
            app_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = app_dir / "budget.db"
        self._init_database()

    # ... (toutes les méthodes de la classe DatabaseManager de votre ancien utils.py vont ici) ...
    # Exemples : _init_database, create_mois, get_all_mois, update_depense, etc.
    # Le code de ces méthodes ne change pas, seule leur localisation.
    # Assurez-vous d'importer Depense, Mois, et DatabaseError depuis core.data_models

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
                        date_depense TEXT NOT NULL DEFAULT (strftime('%d/%m/%Y', 'now')),
                        est_credit BOOLEAN NOT NULL DEFAULT 0,
                        effectue BOOLEAN NOT NULL DEFAULT 0,
                        emprunte BOOLEAN NOT NULL DEFAULT 0,
                        est_fixe BOOLEAN NOT NULL DEFAULT 0,
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
    
    # Dans utils.py, à l'intérieur de la classe DatabaseManager, remplacez cette méthode :

    def delete_mois(self, nom: str) -> bool:
        """
        Supprime un mois et toutes ses dépenses associées en deux étapes explicites
        au sein d'une seule transaction.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Étape 1 : Trouver l'ID du mois à partir de son nom.
                cursor.execute('SELECT id FROM mois WHERE nom = ?', (nom,))
                row = cursor.fetchone()

                # Si le mois n'est pas trouvé, on ne peut rien supprimer.
                if not row:
                    return False

                mois_id = row[0]

                # Étape 2 : Supprimer toutes les dépenses de la table 'depenses'
                # qui sont associées à cet ID de mois.
                cursor.execute('DELETE FROM depenses WHERE mois_id = ?', (mois_id,))
                
                # Étape 3 : Une fois les dépenses supprimées, supprimer le mois lui-même.
                cursor.execute('DELETE FROM mois WHERE id = ?', (mois_id,))

                # La transaction est validée automatiquement à la fin du bloc 'with'
                conn.commit()

                # On retourne True si la suppression du mois a bien eu lieu (rowcount > 0)
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            # En cas d'erreur, la transaction est automatiquement annulée.
            raise DatabaseError(f"Erreur lors de la suppression du mois et de ses dépenses : {e}")
            
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
        """Récupère toutes les dépenses pour un mois donné."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # --- CORRECTION ---
                # On ajoute 'date_depense' et 'est_credit' à la requête SELECT
                sql = '''
                    SELECT id, nom, montant, categorie, date_depense, est_credit, effectue, emprunte, est_fixe
                    FROM depenses WHERE mois_id = ?
                '''
                
                cursor.execute(sql, (mois_id,))
                rows = cursor.fetchall()
                
                depenses = []
                for row in rows:
                    # On s'assure que les valeurs correspondent à l'ordre des colonnes
                    depenses.append(Depense(
                        id=row[0],
                        nom=row[1],
                        montant=row[2],
                        categorie=row[3],
                        date_depense=row[4],
                        est_credit=bool(row[5]), # Conversion en booléen
                        effectue=bool(row[6]),   # Conversion en booléen
                        emprunte=bool(row[7]),    # Conversion en booléen
                        est_fixe=bool(row[8])
                    ))
                return depenses
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la récupération des dépenses: {e}")
        
    def create_depense(self, mois_id: int, depense: Depense) -> int:
        """Crée une nouvelle dépense dans la base de données et retourne son ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # --- CORRECTION ---
                # On ajoute les nouvelles colonnes à la requête SQL
                sql = '''
                    INSERT INTO depenses (
                        mois_id, nom, montant, categorie, 
                        date_depense, est_credit, effectue, emprunte, est_fixe
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                # On s'assure que les valeurs correspondent aux colonnes
                values = (
                    mois_id,
                    depense.nom,
                    depense.montant,
                    depense.categorie,
                    depense.date_depense,
                    depense.est_credit,
                    depense.effectue,
                    depense.emprunte,
                    depense.est_fixe
                )
                
                cursor.execute(sql, values)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la création de la dépense : {e}")
 
    def update_depense(self, depense: Depense):
        """Met à jour une dépense existante dans la base de données."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # --- MODIFICATION : Ajout de date_depense à la requête UPDATE ---
                sql = '''
                    UPDATE depenses SET
                        nom = ?, montant = ?, categorie = ?, date_depense = ?,
                        effectue = ?, emprunte = ?, est_credit = ?, est_fixe = ?
                    WHERE id = ?
                '''
                values = (
                    depense.nom, depense.montant, depense.categorie, depense.date_depense,
                    depense.effectue, depense.emprunte, depense.est_credit, depense.est_fixe,
                    depense.id
                )
                cursor.execute(sql, values)
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
        
    def get_mois_by_id(self, mois_id: int) -> Optional[Mois]:
        """Récupère les détails d'un mois par son ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire FROM mois WHERE id = ?', (mois_id,))
                row = cursor.fetchone()
                if row:
                    return Mois(id=row[0], nom=row[1], salaire=row[2])
                return None
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur lors de la récupération du mois par ID: {e}")

    def duplicate_mois(self, original_mois_id: int, new_mois_name: str) -> Result:
        """Crée une copie d'un mois existant avec toutes ses opérations au sein d'une seule transaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # On démarre explicitement la transaction
                cursor.execute("BEGIN TRANSACTION")
                try:
                    # Étape 1 : Récupérer les détails du mois original (hors transaction)
                    original_mois = self.get_mois_by_id(original_mois_id)
                    if not original_mois:
                        # Pas besoin d'annuler si rien n'a commencé
                        return Result.error("Le mois original à dupliquer n'a pas été trouvé.")

                    # Étape 2 : Créer le nouveau mois
                    cursor.execute(
                        'INSERT INTO mois (nom, salaire) VALUES (?, ?)',
                        (new_mois_name, original_mois.salaire)
                    )
                    new_mois_id = cursor.lastrowid

                    # Étape 3 : Récupérer toutes les opérations du mois original
                    original_depenses = self.get_depenses_by_mois(original_mois_id)

                    # Étape 4 : Insérer des copies de ces opérations pour le nouveau mois
                    for depense in original_depenses:
                        sql = '''
                            INSERT INTO depenses (
                                mois_id, nom, montant, categorie, date_depense, 
                                est_credit, effectue, emprunte, est_fixe
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        values = (
                            new_mois_id, depense.nom, depense.montant, depense.categorie,
                            depense.date_depense, depense.est_credit, depense.effectue, depense.emprunte, depense.est_fixe
                        )
                        cursor.execute(sql, values)
                    
                    # Si tout s'est bien passé jusqu'ici, on valide toutes les modifications
                    conn.commit()
                    return Result.success(f"Mois '{original_mois.nom}' dupliqué avec succès en '{new_mois_name}'.")

                except sqlite3.IntegrityError:
                    conn.rollback() # Annule tout en cas de nom de mois dupliqué
                    raise DatabaseError(f"Le mois '{new_mois_name}' existe déjà.")
                except Exception as e:
                    conn.rollback() # Annule tout si une autre erreur survient
                    raise DatabaseError(f"Erreur lors de la duplication du mois : {e}")

        except Exception as e:
            # Lève une exception qui sera attrapée par le modèle
            raise DatabaseError(f"Erreur de connexion lors de la duplication du mois : {e}")
        
    def import_new_mois(self, nom_mois: str, salaire: float, depenses: List[Depense]):
        """
        Crée un nouveau mois et y importe une liste de dépenses dans une transaction unique.
        Retourne l'ID du nouveau mois créé.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")
                try:
                    # 1. Créer le mois
                    cursor.execute('INSERT INTO mois (nom, salaire) VALUES (?, ?)', (nom_mois, salaire))
                    new_mois_id = cursor.lastrowid

                    # 2. Insérer toutes les dépenses
                    for dep in depenses:
                        sql = '''
                            INSERT INTO depenses (
                                mois_id, nom, montant, categorie, date_depense, 
                                est_credit, effectue, emprunte
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        values = (
                            new_mois_id, dep.nom, dep.montant, dep.categorie,
                            dep.date_depense, dep.est_credit, dep.effectue, dep.emprunte
                        )
                        cursor.execute(sql, values)
                    
                    # Si tout va bien, on valide
                    conn.commit()
                    return new_mois_id

                except sqlite3.IntegrityError:
                    conn.rollback()
                    raise DatabaseError(f"Le mois '{nom_mois}' existe déjà.")
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Erreur durant la transaction d'import, annulation : {e}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Erreur de connexion lors de l'import : {e}")
