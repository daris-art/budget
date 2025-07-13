# main.py

import tkinter as tk
from model import BudgetModel
from controller import BudgetController

if __name__ == "__main__":
    # Créer la fenêtre principale
    root = tk.Tk()

    def close_app(event=None):
        root.destroy()

    # Associer Ctrl+Escape à la fermeture
    root.bind('<Control-Escape>', close_app)

    
    # Créer les composants MVC
    model = BudgetModel()
    controller = BudgetController(model, root)
    
    # Lancer la boucle principale de l'application
    root.mainloop()
