# main.py

import sys
import logging
from PyQt6.QtWidgets import QApplication

# Import des composants de la nouvelle structure
from core.model import BudgetModel
from controller import BudgetController
from view import BudgetView
from core.database import DatabaseManager
from core.validation import DataValidator
from core.services import ImportExportService, BitcoinAPIService

def main():
    """Point d'entrée principal de l'application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    app = QApplication(sys.argv)

    # 1. Initialisation des composants du backend (core)
    db_manager = DatabaseManager()
    validator = DataValidator()
    import_export_service = ImportExportService(db_manager)
    api_service = BitcoinAPIService()

    # 2. Injection des dépendances dans le modèle
    model = BudgetModel(
        db_manager=db_manager,
        validator=validator,
        import_export_service=import_export_service,
        api_service=api_service
    )

    # 3. Initialisation du reste du MVC
    controller = BudgetController(model)
    view = BudgetView(controller)
    controller.set_view(view) 

    # 4. Démarrage
    controller.start_application()
    view.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()