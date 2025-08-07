# main.py (version mise à jour pour PyQt6)

import sys
import logging

# On importe les composants nécessaires
from PyQt6.QtWidgets import QApplication
from model import BudgetModel
from controller import BudgetController
from view import BudgetView # Assurez-vous d'utiliser le view.py de PyQt6

def main():
    """Point d'entrée principal de l'application."""
    # Configuration du logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    # 1. Création de l'instance de l'application PyQt
    app = QApplication(sys.argv)

    # 2. Initialisation du MVC
    model = BudgetModel()
    controller = BudgetController(model)
    view = BudgetView(controller)
    
    # 3. Lier la vue au contrôleur
    controller.set_view(view) 

    # 4. Démarrage de la logique de l'application (charge les données et applique le thème)
    controller.start_application()

    # 5. Affichage de la fenêtre principale
    view.show()
    
    # 6. Lancement de la boucle principale de l'application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()