# model.py
import sqlite3
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

# --- Data Classes ---
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

# --- Main Model Class ---
class BudgetModel:
    """
    Gère les données et la logique métier de l'application avec SQLite.
    Toute la logique de base de données et de manipulation de fichiers est ici.
    """
    def __init__(self):
        self.salaire = 0.0
        self.depenses: List[Depense] = []
        self.mois_actuel: Optional[Mois] = None
        
        self.db_path = self._get_database_path()
        self.categories = [
            "Alimentation", "Logement", "Transport", "Loisirs",
            "Santé", "Factures", "Shopping", "Épargne", "Autres", "Importée"
        ]
        
        self._init_database()
        
    def _get_database_path(self) -> Path:
        """Retourne le chemin vers la base de données dans le dossier utilisateur."""
        try:
            data_dir = Path.home() / ".BudgetApp"
            data_dir.mkdir(exist_ok=True)
            return data_dir / "budget.db"
        except Exception:
            return Path("budget.db") # Fallback en cas de problème de permissions
    
    def _init_database(self):
        """Initialise la base de données et crée les tables si elles n'existent pas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('PRAGMA foreign_keys = ON;') # Activer les clés étrangères
                
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
            print(f"Erreur d'initialisation de la base de données: {e}")

    # --- Gestion des Mois (CRUD) ---

    def get_all_mois(self) -> List[Mois]:
        """Récupère tous les mois de la base, triés du plus récent au plus ancien."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois ORDER BY date_creation DESC')
                return [Mois(id=r[0], nom=r[1], salaire=r[2], date_creation=r[3]) for r in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def create_mois(self, nom: str, salaire: float = 0.0) -> Tuple[bool, str]:
        """Crée un nouveau mois et le charge comme mois actuel."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO mois (nom, salaire) VALUES (?, ?)', (nom, salaire))
                mois_id = cursor.lastrowid
                conn.commit()
                
                self.load_mois(nom) # Charge le mois nouvellement créé
                return True, f"Mois '{nom}' créé avec succès."
        except sqlite3.IntegrityError:
            return False, f"Le mois '{nom}' existe déjà."
        except sqlite3.Error as e:
            return False, f"Erreur de base de données : {e}"

    def load_mois(self, nom: str) -> Tuple[bool, str]:
        """Charge un mois et ses dépenses depuis la base de données."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nom, salaire, date_creation FROM mois WHERE nom = ?', (nom,))
                mois_row = cursor.fetchone()
                
                if not mois_row:
                    return False, f"Mois '{nom}' non trouvé."
                
                self.mois_actuel = Mois(id=mois_row[0], nom=mois_row[1], salaire=mois_row[2], date_creation=mois_row[3])
                self.salaire = mois_row[2]
                
                cursor.execute('SELECT id, nom, montant, categorie, effectue, emprunte FROM depenses WHERE mois_id = ?', (self.mois_actuel.id,))
                self.depenses = [Depense(id=r[0], nom=r[1], montant=r[2], categorie=r[3], effectue=bool(r[4]), emprunte=bool(r[5])) for r in cursor.fetchall()]
                
                self._save_last_mois(nom)
                return True, f"Mois '{nom}' chargé."
        except sqlite3.Error as e:
            return False, f"Erreur de chargement: {e}"

    def rename_mois(self, mois_id: int, nouveau_nom: str) -> Tuple[bool, str]:
        """Renomme un mois dans la base de données."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE mois SET nom = ? WHERE id = ?', (nouveau_nom, mois_id))
                conn.commit()

                if self.mois_actuel and self.mois_actuel.id == mois_id:
                    self.mois_actuel.nom = nouveau_nom
                    self._save_last_mois(nouveau_nom)
                return True, "Mois renommé."
        except sqlite3.IntegrityError:
            return False, f"Le nom '{nouveau_nom}' est déjà utilisé."
        except sqlite3.Error as e:
            return False, f"Erreur de renommage: {e}"

    def dupliquer_mois(self) -> Tuple[bool, str]:
        """Duplique le mois actuel avec un nouveau nom."""
        if not self.mois_actuel:
            return False, "Aucun mois à dupliquer."

        # Logique pour trouver un nom unique
        base_nom = self.mois_actuel.nom
        nouveau_nom = f"{base_nom} (copie)"
        all_names = [m.nom for m in self.get_all_mois()]
        i = 1
        while nouveau_nom in all_names:
            i += 1
            nouveau_nom = f"{base_nom} (copie {i})"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Créer le nouveau mois
                cursor.execute('INSERT INTO mois (nom, salaire) VALUES (?, ?)', (nouveau_nom, self.salaire))
                nouveau_id = cursor.lastrowid
                # Copier les dépenses
                depenses_a_copier = [(nouveau_id, d.nom, d.montant, d.categorie, d.effectue, d.emprunte) for d in self.depenses]
                cursor.executemany('INSERT INTO depenses (mois_id, nom, montant, categorie, effectue, emprunte) VALUES (?,?,?,?,?,?)', depenses_a_copier)
                conn.commit()
            
            self.load_mois(nouveau_nom) # Charge le nouveau mois dupliqué
            return True, f"Mois dupliqué et chargé : '{nouveau_nom}'."
        except sqlite3.Error as e:
            return False, f"Erreur de duplication: {e}"

    def delete_mois(self, nom: str) -> Tuple[bool, str]:
        """Supprime un mois de la base de données."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM mois WHERE nom = ?', (nom,))
                if cursor.rowcount == 0:
                    return False, "Mois non trouvé."
                conn.commit()
                if self.mois_actuel and self.mois_actuel.nom == nom:
                    self.clear_all_data() # Réinitialise l'état si on supprime le mois courant
                return True, f"Mois '{nom}' supprimé."
        except sqlite3.Error as e:
            return False, f"Erreur de suppression: {e}"

    # --- Session et Configuration ---
    def load_data_from_last_session(self) -> Tuple[bool, str]:
        """Charge le dernier mois utilisé ou le plus récent."""
        last_mois_nom = self._load_last_mois()
        if last_mois_nom:
            success, msg = self.load_mois(last_mois_nom)
            if success: return True, msg
        
        all_mois = self.get_all_mois()
        if all_mois:
            return self.load_mois(all_mois[0].nom)
        
        return False, "Aucun mois disponible. Créez-en un nouveau."

    def _save_last_mois(self, nom_mois: str):
        """Sauvegarde le nom du dernier mois utilisé."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO config (cle, valeur) VALUES (?, ?)', ('last_mois', nom_mois))
                conn.commit()
        except sqlite3.Error: pass # Non-critique

    def _load_last_mois(self) -> Optional[str]:
        """Récupère le nom du dernier mois utilisé."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT valeur FROM config WHERE cle = ?', ('last_mois',))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error: return None

    # --- Gestion des Dépenses et du Salaire ---
    def set_salaire(self, salaire_str: str):
        """Met à jour le salaire et le sauvegarde en base."""
        try:
            self.salaire = float(str(salaire_str).replace(',', '.'))
            if self.mois_actuel:
                self.mois_actuel.salaire = self.salaire
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('UPDATE mois SET salaire = ? WHERE id = ?', (self.salaire, self.mois_actuel.id))
                    conn.commit()
        except (ValueError, TypeError):
            self.salaire = 0.0

    def add_expense(self, **kwargs):
        """Ajoute une dépense à la fois en mémoire et dans la base."""
        if not self.mois_actuel: return
        dep = Depense(**kwargs)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO depenses (mois_id, nom, montant, categorie, effectue, emprunte) VALUES (?,?,?,?,?,?)''',
                               (self.mois_actuel.id, dep.nom, dep.montant, dep.categorie, dep.effectue, dep.emprunte))
                dep.id = cursor.lastrowid
                conn.commit()
                self.depenses.append(dep)
        except sqlite3.Error as e: print(f"Erreur d'ajout de dépense: {e}")

    def update_expense(self, index, nom, montant, categorie, effectue, emprunte):
        """Met à jour une dépense."""
        if 0 <= index < len(self.depenses):
            try:
                montant_float = float(str(montant).replace(',', '.'))
            except (ValueError, TypeError):
                montant_float = 0.0
            
            dep = self.depenses[index]
            dep.nom, dep.montant, dep.categorie, dep.effectue, dep.emprunte = nom, montant_float, categorie, effectue, emprunte
            
            if dep.id:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute('UPDATE depenses SET nom=?, montant=?, categorie=?, effectue=?, emprunte=? WHERE id=?',
                                     (dep.nom, dep.montant, dep.categorie, dep.effectue, dep.emprunte, dep.id))
                        conn.commit()
                except sqlite3.Error as e: print(f"Erreur de mise à jour: {e}")

    def remove_expense(self, index):
        """Supprime une dépense."""
        if 0 <= index < len(self.depenses):
            dep_id_to_delete = self.depenses[index].id
            del self.depenses[index]
            if dep_id_to_delete:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute('DELETE FROM depenses WHERE id = ?', (dep_id_to_delete,))
                        conn.commit()
                except sqlite3.Error as e: print(f"Erreur de suppression: {e}")
    
    def sort_depenses(self):
        """Trie les dépenses par montant."""
        self.depenses.sort(key=lambda d: d.montant, reverse=True)

    def clear_current_month_expenses(self):
        """Supprime toutes les dépenses du mois actuel."""
        if not self.mois_actuel: return
        self.depenses.clear()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM depenses WHERE mois_id = ?', (self.mois_actuel.id,))
                conn.commit()
        except sqlite3.Error as e: print(f"Erreur de réinitialisation: {e}")
    
    def clear_all_data(self):
        """Réinitialise l'état du modèle en mémoire."""
        self.salaire = 0.0
        self.depenses = []
        self.mois_actuel = None

    # --- Calculs et Données pour la Vue ---
    def get_total_depenses(self): return sum(d.montant for d in self.depenses)
    def get_total_depenses_effectuees(self): return sum(d.montant for d in self.depenses if d.effectue)
    def get_total_depenses_non_effectuees(self): return sum(d.montant for d in self.depenses if not d.effectue)
    def get_total_emprunte(self): return sum(d.montant for d in self.depenses if d.emprunte)
    def get_argent_restant(self): return self.salaire - self.get_total_depenses()

    def get_graph_data(self):
        """Prépare les données pour les graphiques."""
        valid_expenses = [d for d in self.depenses if d.montant > 0 and d.nom.strip()]
        if not valid_expenses:
            return [], [], 0.0, {}
        
        labels = [d.nom for d in valid_expenses]
        values = [d.montant for d in valid_expenses]
        categories_data = {}
        for d in valid_expenses:
            categories_data[d.categorie] = categories_data.get(d.categorie, 0) + d.montant
        
        return labels, values, self.get_argent_restant(), categories_data

    # --- Logique d'Import/Export (MAINTENANT DANS LE MODÈLE) ---

    def export_to_json(self, filepath: str) -> Tuple[bool, str]:
        """Exporte le mois actuel vers un fichier JSON."""
        if not self.mois_actuel:
            return False, "Aucun mois à exporter."
        try:
            data = {
                'salaire': self.salaire,
                'depenses': [{'nom': d.nom, 'montant': d.montant, 'categorie': d.categorie, 'effectue': d.effectue, 'emprunte': d.emprunte} for d in self.depenses]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True, "Export JSON réussi."
        except Exception as e:
            return False, f"Erreur d'export: {e}"

    def import_from_json(self, filepath: str) -> Tuple[bool, str]:
        """Importe et remplace les données depuis un fichier JSON."""
        if not self.mois_actuel:
            return False, "Chargez un mois avant d'importer."
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.clear_current_month_expenses()
            self.set_salaire(data.get('salaire', 0.0))
            for dep_data in data.get('depenses', []):
                self.add_expense(**dep_data)
                
            return True, "Import JSON réussi."
        except Exception as e:
            self.load_mois(self.mois_actuel.nom) # Recharger pour annuler les changements partiels
            return False, f"Erreur d'import JSON: {e}"
            
    def import_from_excel(self, file_path: str, start_date_str: str, end_date_str: str) -> Tuple[bool, str]:
        """Crée un nouveau mois en important les données d'un fichier Excel."""
        try:
            import pandas as pd # Importation locale
        except ImportError:
            return False, "La librairie 'pandas' et 'openpyxl' sont requises. Installez-les avec 'pip install pandas openpyxl'."

        try:
            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
        except ValueError:
            return False, "Format de date invalide. Utilisez JJ/MM/AAAA."

        try:
            df = pd.read_excel(file_path, header=9)
            if not all(col in df.columns for col in ["Date", "Libellé", "Débit euros"]):
                return False, "Colonnes 'Date', 'Libellé' ou 'Débit euros' manquantes."

            df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
            df_filtre = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

            depenses = [(str(row["Libellé"]).strip(), float(row["Débit euros"])) for _, row in df_filtre.iterrows() if pd.notna(row["Débit euros"]) and row["Débit euros"] > 0]

            if not depenses:
                return True, "Aucune dépense trouvée dans cette période."

            # Créer un nom de mois unique
            nom_base = f"Import Excel {start_date.strftime('%d-%m-%Y')} au {end_date.strftime('%d-%m-%Y')}"
            nom_mois = nom_base
            all_names = [m.nom for m in self.get_all_mois()]
            suffixe = 1
            while nom_mois in all_names:
                nom_mois = f"{nom_base} (copie {suffixe})"
                suffixe += 1

            # Créer et charger le nouveau mois
            success, message = self.create_mois(nom_mois, 0.0)
            if not success:
                return False, message
            
            # Ajouter les dépenses importées
            for nom, montant in depenses:
                self.add_expense(nom=nom, montant=montant, categorie="Importée", effectue=True, emprunte=False)
            
            return True, f"Import réussi. Nouveau mois '{nom_mois}' créé."

        except Exception as e:
            return False, f"Erreur lors de la lecture du fichier Excel: {e}"