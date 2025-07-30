# model.py

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

# ... (le dataclass Depense reste inchangé) ...
@dataclass
class Depense:
    nom: str = ""
    montant: float = 0.0
    categorie: str = "Autres"
    effectue: bool = False
    emprunte: bool = False
    id: Optional[int] = None  # Ajout de l'ID pour SQLite

@dataclass
class Mois:
    nom: str
    salaire: float = 0.0
    date_creation: Optional[str] = None
    id: Optional[int] = None

class BudgetModel:
    """
    Gère les données et la logique métier de l'application avec SQLite.
    """
    def __init__(self):
        self.salaire = 0.0
        self.depenses: List[Depense] = []
        self.mois_actuel: Optional[Mois] = None
        
        # Configuration de la base de données
        self.db_path = self._get_database_path()
        self.categories = [
            "Alimentation", "Logement", "Transport", "Loisirs",
            "Santé", "Factures", "Shopping", "Épargne", "Autres"
        ]
        
        # Initialisation de la base de données
        self._init_database()
        
    def _get_database_path(self) -> Path:
        """Retourne le chemin vers la base de données."""
        try:
            data_dir = Path.home() / ".BudgetApp"
            data_dir.mkdir(exist_ok=True)
            return data_dir / "budget.db"
        except Exception:
            return Path("budget.db")
    
    def _init_database(self):
        """Initialise la base de données et crée les tables si nécessaire."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Création de la table mois
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mois (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom TEXT UNIQUE NOT NULL,
                        salaire REAL NOT NULL DEFAULT 0.0,
                        date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Création de la table depenses
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
                
                # Création de la table de configuration
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config (
                        cle TEXT PRIMARY KEY,
                        valeur TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")

    def get_all_mois(self) -> List[Mois]:
        """Récupère tous les mois disponibles."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois ORDER BY date_creation DESC')
                rows = cursor.fetchall()
                return [Mois(nom=row[1], salaire=row[2], date_creation=row[3], id=row[0]) for row in rows]
        except sqlite3.Error:
            return []

    def create_mois(self, nom: str, salaire: float = 0.0) -> Tuple[bool, str]:
        """Crée un nouveau mois."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO mois (nom, salaire) VALUES (?, ?)',
                    (nom, salaire)
                )
                mois_id = cursor.lastrowid
                conn.commit()
                
                # Charger le nouveau mois
                self.mois_actuel = Mois(nom=nom, salaire=salaire, id=mois_id)
                self.salaire = salaire
                self.depenses = []
                
                # Sauvegarder comme dernier mois utilisé
                self._save_last_mois(nom)
                
                return True, f"Mois '{nom}' créé avec succès."
        except sqlite3.IntegrityError:
            return False, f"Le mois '{nom}' existe déjà."
        except sqlite3.Error as e:
            return False, f"Erreur lors de la création du mois: {e}"

    def load_mois(self, nom: str) -> Tuple[bool, str]:
        """Charge un mois existant."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Charger les informations du mois
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois WHERE nom = ?', (nom,))
                mois_row = cursor.fetchone()
                
                if not mois_row:
                    return False, f"Mois '{nom}' non trouvé."
                
                self.mois_actuel = Mois(
                    nom=mois_row[1], 
                    salaire=mois_row[2], 
                    date_creation=mois_row[3], 
                    id=mois_row[0]
                )
                self.salaire = mois_row[2]
                
                # Charger les dépenses associées
                cursor.execute('''
                    SELECT id, nom, montant, categorie, effectue, emprunte 
                    FROM depenses WHERE mois_id = ?
                ''', (mois_row[0],))
                
                depenses_rows = cursor.fetchall()
                self.depenses = [
                    Depense(
                        nom=row[1], 
                        montant=row[2], 
                        categorie=row[3], 
                        effectue=bool(row[4]), 
                        emprunte=bool(row[5]), 
                        id=row[0]
                    )
                    for row in depenses_rows
                ]
                
                # Sauvegarder comme dernier mois utilisé
                self._save_last_mois(nom)
                
                return True, f"Mois '{nom}' chargé avec succès."
                
        except sqlite3.Error as e:
            return False, f"Erreur lors du chargement: {e}"

    def delete_mois(self, nom: str) -> Tuple[bool, str]:
        """Supprime un mois et toutes ses dépenses."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM mois WHERE nom = ?', (nom,))
                
                if cursor.rowcount == 0:
                    return False, f"Mois '{nom}' non trouvé."
                
                conn.commit()
                
                # Si c'est le mois actuel, réinitialiser
                if self.mois_actuel and self.mois_actuel.nom == nom:
                    self.mois_actuel = None
                    self.clear_all_data()
                
                return True, f"Mois '{nom}' supprimé avec succès."
                
        except sqlite3.Error as e:
            return False, f"Erreur lors de la suppression: {e}"

    def _save_last_mois(self, nom_mois: str):
        """Sauvegarde le dernier mois utilisé dans la configuration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO config (cle, valeur) VALUES (?, ?)',
                    ('last_mois', nom_mois)
                )
                conn.commit()
        except sqlite3.Error:
            pass  # Ignorer les erreurs de configuration

    def _load_last_mois(self) -> Optional[str]:
        """Charge le nom du dernier mois utilisé."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT valeur FROM config WHERE cle = ?', ('last_mois',))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None

    def set_salaire(self, salaire):
        """Met à jour le salaire du mois actuel."""
        try:
            self.salaire = float(salaire)
            if self.mois_actuel:
                self.mois_actuel.salaire = self.salaire
                self._save_mois_salaire()
        except (ValueError, TypeError):
            self.salaire = 0.0

    def _save_mois_salaire(self):
        """Sauvegarde le salaire du mois actuel en base."""
        if not self.mois_actuel or not self.mois_actuel.id:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE mois SET salaire = ? WHERE id = ?',
                    (self.salaire, self.mois_actuel.id)
                )
                conn.commit()
        except sqlite3.Error:
            pass

    # Les méthodes de calcul restent identiques
    def get_total_depenses(self):
        return sum(d.montant for d in self.depenses)

    def get_argent_restant(self):
        return self.salaire - self.get_total_depenses()
    
    def get_total_depenses_effectuees(self):
        return sum(d.montant for d in self.depenses if d.effectue)
        
    def get_total_depenses_non_effectuees(self):
        return sum(d.montant for d in self.depenses if not d.effectue)

    def get_total_emprunte(self):
        return sum(d.montant for d in self.depenses if d.emprunte)

    def add_expense(self, nom="", montant=0.0, categorie="Autres", effectue=False, emprunte=False):
        """Ajoute une nouvelle dépense."""
        if not self.mois_actuel or not self.mois_actuel.id:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO depenses (mois_id, nom, montant, categorie, effectue, emprunte)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (self.mois_actuel.id, nom, montant, categorie, effectue, emprunte))
                
                depense_id = cursor.lastrowid
                conn.commit()
                
                # Ajouter à la liste locale
                self.depenses.append(Depense(
                    nom=nom, 
                    montant=montant, 
                    categorie=categorie, 
                    effectue=effectue, 
                    emprunte=emprunte, 
                    id=depense_id
                ))
                
        except sqlite3.Error:
            pass
        
    def remove_expense(self, index):
        """Supprime une dépense."""
        if 0 <= index < len(self.depenses):
            depense = self.depenses[index]
            if depense.id:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM depenses WHERE id = ?', (depense.id,))
                        conn.commit()
                except sqlite3.Error:
                    pass
            
            del self.depenses[index]
            
    def update_expense(self, index, nom, montant, categorie, effectue, emprunte):
        """Met à jour une dépense."""
        if 0 <= index < len(self.depenses):
            try:
                montant_float = float(montant)
            except (ValueError, TypeError):
                montant_float = 0.0
                
            depense = self.depenses[index]
            depense.nom = nom
            depense.montant = montant_float
            depense.categorie = categorie
            depense.effectue = effectue
            depense.emprunte = emprunte
            
            # Sauvegarder en base
            if depense.id:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE depenses 
                            SET nom = ?, montant = ?, categorie = ?, effectue = ?, emprunte = ?
                            WHERE id = ?
                        ''', (nom, montant_float, categorie, effectue, emprunte, depense.id))
                        conn.commit()
                except sqlite3.Error:
                    pass

    def sort_depenses(self):
        """Trie les dépenses par montant décroissant."""
        self.depenses.sort(key=lambda d: d.montant, reverse=True)

    def clear_all_data(self):
        """Réinitialise toutes les données."""
        self.salaire = 0.0
        self.depenses = []
        self.mois_actuel = None

    def get_graph_data(self):
        """Récupère les données pour les graphiques."""
        valid_expenses = [d for d in self.depenses if d.montant > 0 and d.nom.strip()]
        
        if not valid_expenses:
            return [], [], [], {}, 0.0
            
        labels = [d.nom for d in valid_expenses]
        values = [d.montant for d in valid_expenses]
        argent_restant = self.get_argent_restant()
        
        categories_data = {}
        for d in valid_expenses:
            categories_data[d.categorie] = categories_data.get(d.categorie, 0) + d.montant
        
        return labels, values, argent_restant, categories_data

    def load_data_from_last_session(self) -> Tuple[bool, str]:
        """Charge le dernier mois utilisé lors de la session précédente."""
        last_mois = self._load_last_mois()
        if last_mois:
            return self.load_mois(last_mois)
        else:
            # Si aucun mois n'est configuré, essayer de charger le plus récent
            all_mois = self.get_all_mois()
            if all_mois:
                return self.load_mois(all_mois[0].nom)
            else:
                return False, "Aucun mois disponible. Créez un nouveau mois."
            