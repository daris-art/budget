# model.py

import json
from pathlib import Path
from dataclasses import dataclass, asdict

# AMÉLIORATION: Utilisation d'un dataclass pour une structure de données plus propre et plus sûre.
@dataclass
class Depense:
    nom: str = ""
    montant: float = 0.0
    categorie: str = "Autres"
    effectue: bool = False 

class BudgetModel:
    """
    Gère les données et la logique métier de l'application.
    Ne contient aucune référence à Tkinter.
    """
    def __init__(self):
        self.salaire = 0.0
        # AMÉLIORATION: La liste de dépenses contient maintenant des objets Depense.
        self.depenses: list[Depense] = []
        self.data_file = self._get_data_file_path("budget_data_Juin.json")
        # AMÉLIORATION: Ajout d'une liste de catégories prédéfinies.
        self.categories = [
            "Alimentation", "Logement", "Transport", "Loisirs", 
            "Santé", "Factures", "Shopping", "Épargne", "Autres"
        ]

    def _get_data_file_path(self, filename):
        try:
            data_dir = Path.home() / ".BudgetApp"
            data_dir.mkdir(exist_ok=True)
            return data_dir / filename
        except Exception:
            return Path(filename)

    def set_salaire(self, salaire):
        try:
            self.salaire = float(salaire)
        except (ValueError, TypeError):
            self.salaire = 0.0

    def get_total_depenses(self):
        return sum(d.montant for d in self.depenses)

    def get_argent_restant(self):
        return self.salaire - self.get_total_depenses()
    
    def get_total_depenses_effectuees(self):
        """Calcule la somme des dépenses marquées comme effectuées."""
        return sum(d.montant for d in self.depenses if d.effectue)
        
    def get_total_depenses_non_effectuees(self):
        """
        NOUVEAU: Calcule la somme des dépenses non encore effectuées.
        """
        return sum(d.montant for d in self.depenses if not d.effectue)

    def add_expense(self, nom="", montant=0.0, categorie="Autres", effectue=False):
        # AMÉLIORATION: Ajoute un objet Depense.
        self.depenses.append(Depense(nom=nom, montant=montant, categorie=categorie, effectue=effectue))
        
    def remove_expense(self, index):
        if 0 <= index < len(self.depenses):
            del self.depenses[index]
            
    def update_expense(self, index, nom, montant, categorie, effectue):
        if 0 <= index < len(self.depenses):
            try:
                montant_float = float(montant)
            except (ValueError, TypeError):
                montant_float = 0.0
            self.depenses[index] = Depense(nom, montant_float, categorie, effectue)

    def sort_depenses(self):
        self.depenses.sort(key=lambda d: d.montant, reverse=True)

    def clear_all_data(self):
        self.salaire = 0.0
        self.depenses = []

    def get_graph_data(self):
        """Retourne les données formatées pour le graphique."""
        valid_expenses = [d for d in self.depenses if d.montant > 0 and d.nom.strip()]
        
        if not valid_expenses:
            return [], [], [], {}, 0.0
            
        labels = [d.nom for d in valid_expenses]
        values = [d.montant for d in valid_expenses]
        argent_restant = self.get_argent_restant()
        
        # AMÉLIORATION: Calcule les totaux par catégorie réelle.
        categories_data = {}
        for d in valid_expenses:
            categories_data[d.categorie] = categories_data.get(d.categorie, 0) + d.montant
        
        return labels, values, argent_restant, categories_data

    def load_data(self, filepath=None):
        target_file = filepath or self.data_file
        if not Path(target_file).exists():
            return False, "Fichier non trouvé"
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.salaire = data.get('salaire') or 0.0
            # AMÉLIORATION: Reconstruit les objets Depense à partir des dictionnaires chargés.
            self.depenses = [Depense(**dep) for dep in data.get('depenses', [])]
            return True, "Chargement réussi"
        except Exception as e:
            self.clear_all_data()
            return False, f"Erreur de chargement: {e}"

    def save_data(self, filepath=None):
        """
        Sauvegarde les données.
        Si filepath est fourni, sauvegarde à cet emplacement (Sauvegarder sous).
        Sinon, utilise le chemin de fichier par défaut (Sauvegarder).
        """
        # Choisir le fichier cible : le nouveau chemin ou celui par défaut.
        target_file = filepath or self.data_file
        
        try:
            data = {'salaire': self.salaire, 'depenses': [asdict(d) for d in self.depenses]}
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Si la sauvegarde réussit avec un nouveau chemin, on le mémorise.
            if filepath:
                self.data_file = target_file
                
            return True, f"Sauvegarde réussie dans {Path(target_file).name}"
        except Exception as e:
            return False, f"Erreur de sauvegarde: {e}"