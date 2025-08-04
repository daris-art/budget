# main.py - Point d'entrée de l'application Budget Manager

import tkinter as tk
import logging
import sys
from pathlib import Path

# Configuration du logging
# Le logging permet de suivre le déroulement de l'application et de déboguer
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('budget_app.log'),  # Enregistre les logs dans un fichier
        logging.StreamHandler(sys.stdout)       # Affiche les logs dans la console
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Point d'entrée principal de l'application"""
    try:
        logger.info("Démarrage de l'application Budget Manager")
        
        # Import des modules principaux
        # L'application suit l'architecture MVC (Modèle-Vue-Contrôleur)
        from model import BudgetModel
        from controller import BudgetController
        
        # Création de la fenêtre principale
        root = tk.Tk()
        
        # Configuration de base de la fenêtre
        root.withdraw()  # Masquer temporairement pendant l'initialisation pour éviter un flash
        
        try:
            # Initialisation du modèle
            # Le modèle gère la logique métier et les données
            logger.info("Initialisation du modèle...")
            model = BudgetModel()
            
            # Initialisation du contrôleur (qui crée la vue)
            # Le contrôleur orchestre les interactions entre la vue et le modèle
            logger.info("Initialisation du contrôleur et de la vue...")
            controller = BudgetController(model, root)
            
            # Révéler la fenêtre principale une fois que tout est initialisé
            root.deiconify()
            
            # Démarrage de la boucle principale de l'interface graphique
            # C'est ici que l'application attend les événements utilisateur
            logger.info("Lancement de la boucle principale de Tkinter")
            root.mainloop()
            
        except Exception as e:
            logger.critical(f"Erreur fatale lors de l'initialisation : {e}")
            # Si une erreur critique survient, on force la fermeture
            root.destroy()
            sys.exit(1)
            
    except Exception as e:
        # Gère les erreurs qui pourraient survenir avant même l'initialisation de Tkinter
        print(f"Une erreur inattendue est survenue: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
