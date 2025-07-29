# model.py

import json
from pathlib import Path
from dataclasses import dataclass, asdict

# ... (le dataclass Depense reste inchangé) ...
@dataclass
class Depense:
    nom: str = ""
    montant: float = 0.0
    categorie: str = "Autres"
    effectue: bool = False
    emprunte: bool = False

class BudgetModel:
    """
    Gère les données et la logique métier de l'application.
    """
    def __init__(self):
        self.salaire = 0.0
        self.depenses: list[Depense] = []
        # NOUVEAU: Chemin vers le fichier de configuration
        self.config_file = self._get_data_file_path("config.json")
        self.data_file = self._get_data_file_path("budget_data_Juin.json")
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
    
    # NOUVEAU: Charge le chemin du dernier fichier depuis config.json
    def load_last_file_path(self):
        """Lit le fichier de configuration pour trouver le dernier fichier utilisé."""
        try:
            if not self.config_file.exists():
                return None
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return Path(config_data.get("last_file"))
        except (json.JSONDecodeError, IOError, TypeError):
            return None

    # NOUVEAU: Sauvegarde le chemin du dernier fichier dans config.json
    def save_last_file_path(self, filepath):
        """Sauvegarde le chemin du fichier actuel dans le fichier de configuration."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # On s'assure que le chemin est stocké comme une chaîne de caractères
                json.dump({"last_file": str(filepath)}, f, indent=4)
        except IOError as e:
            # Gérer l'erreur de manière silencieuse pour ne pas bloquer l'app
            print(f"Erreur lors de la sauvegarde de la configuration : {e}")

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
        return sum(d.montant for d in self.depenses if d.effectue)
        
    def get_total_depenses_non_effectuees(self):
        return sum(d.montant for d in self.depenses if not d.effectue)

    def get_total_emprunte(self):
        return sum(d.montant for d in self.depenses if d.emprunte)

    def add_expense(self, nom="", montant=0.0, categorie="Autres", effectue=False, emprunte=False):
        self.depenses.append(Depense(nom=nom, montant=montant, categorie=categorie, effectue=effectue, emprunte=emprunte))
        
    def remove_expense(self, index):
        if 0 <= index < len(self.depenses):
            del self.depenses[index]
            
    def update_expense(self, index, nom, montant, categorie, effectue, emprunte):
        if 0 <= index < len(self.depenses):
            try:
                montant_float = float(montant)
            except (ValueError, TypeError):
                montant_float = 0.0
            self.depenses[index] = Depense(nom, montant_float, categorie, effectue, emprunte)

    def sort_depenses(self):
        self.depenses.sort(key=lambda d: d.montant, reverse=True)

    def clear_all_data(self):
        self.salaire = 0.0
        self.depenses = []

    def get_graph_data(self):
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

    def load_data(self, filepath=None):
        target_file = filepath or self.data_file
        if not Path(target_file).exists():
            return False, f"Fichier '{Path(target_file).name}' non trouvé."
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.salaire = data.get('salaire') or 0.0
            self.depenses = [Depense(**dep) for dep in data.get('depenses', [])]
            self.data_file = Path(target_file) # Mémoriser le fichier chargé avec succès
            return True, f"Fichier '{Path(target_file).name}' chargé."
        except Exception as e:
            self.clear_all_data()
            return False, f"Erreur de chargement: {e}"

    def save_data(self, filepath=None):
        target_file = filepath or self.data_file
        
        try:
            data = {'salaire': self.salaire, 'depenses': [asdict(d) for d in self.depenses]}
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            if filepath:
                self.data_file = Path(target_file)
                
            return True, f"Sauvegarde réussie dans {Path(target_file).name}"
        except Exception as e:
            return False, f"Erreur de sauvegarde: {e}"