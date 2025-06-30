# controller.py

from tkinter import filedialog
import matplotlib.pyplot as plt
from view import BudgetView #, GraphWindow # AMÉLIORATION: Importe GraphWindow
from datetime import datetime

class BudgetController:
    """
    Fait le lien entre la Vue et le Modèle.
    Gère la logique de l'application.
    """
    def __init__(self, model, master):
        self.model = model
        self.view = BudgetView(master, self)
        self.master = master
        
        # AMÉLIORATION: Configuration de la sauvegarde automatique.
        self.autosave_interval = 60000  # en millisecondes (60 secondes)
        self.autosave_job = None
        
        self.handle_initial_load()
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)
        self.schedule_autosave()

    def _refresh_view(self):
        """Met à jour toute la vue à partir du modèle."""
        self.view.set_display_salaire(self.model.salaire)
        # AMÉLIORATION: Passe la liste des catégories à la vue.
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        self.update_summary()

    def update_summary(self):
        total = self.model.get_total_depenses()
        restant = self.model.get_argent_restant()
        self.view.update_summary(total, restant)
        
    def handle_initial_load(self):
        success, message = self.model.load_data()
        self.view.update_status(message if success else f"Erreur: {message}")
        self._refresh_view()

    def handle_on_closing(self):
        self.handle_save() # Sauvegarde une dernière fois avant de fermer.
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        plt.close('all')
        self.view.master.destroy()
        
    # AMÉLIORATION: Logique de sauvegarde automatique et manuelle.
    def schedule_autosave(self):
        """Planifie la prochaine sauvegarde automatique."""
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        self.autosave_job = self.master.after(self.autosave_interval, self.handle_autosave)

    def handle_autosave(self):
        self.handle_save(is_auto=True)
        self.schedule_autosave() # Re-planifie la prochaine

    def handle_save_as(self):
        """Ouvre une boîte de dialogue pour choisir où sauvegarder le fichier."""
        filepath = filedialog.asksaveasfilename(
            title="Sauvegarder le budget sous...",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        # Si l'utilisateur annule, filepath sera vide.
        if not filepath:
            self.view.update_status("Sauvegarde annulée.")
            return

        # On appelle la méthode de sauvegarde du modèle AVEC le nouveau chemin
        success, message = self.model.save_data(filepath)
        self.view.update_status(message)
        
    def handle_save(self, is_auto=False):
        success, message = self.model.save_data()
        now = datetime.now().strftime("%H:%M:%S")
        prefix = "Sauvegarde auto" if is_auto else "Sauvegarde"
        if success:
            self.view.update_status(f"{prefix} réussie à {now}")
        else:
            self.view.update_status(f"Erreur de sauvegarde à {now}: {message}")

    def handle_salaire_update(self, *args):
        salaire_str = self.view.salaire_var.get().replace(',', '.')
        self.model.set_salaire(salaire_str)
        self.update_summary()

    def handle_expense_update(self, index):
        # AMÉLIORATION: Récupère et met à jour la catégorie.
        nom, montant_str, categorie = self.view.get_expense_value(index)
        if nom is not None:
            self.model.update_expense(index, nom, montant_str, categorie)
            self.update_summary()
            
    def handle_add_expense(self):
        self.model.add_expense()
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        if self.view.depenses_widgets:
            last_entry = self.view.depenses_widgets[-1]['frame'].winfo_children()[0]
            last_entry.focus_set()
        self.update_summary()

    def handle_remove_expense(self, index):
        self.model.remove_expense(index)
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        self.update_summary()
        
    def handle_sort(self):
        self.model.sort_depenses()
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        
    def handle_reset(self):
        if self.view.ask_confirmation("Confirmation", "Effacer toutes les données ? Cette action est irréversible."):
            self.model.clear_all_data()
            self._refresh_view()
            self.view.update_status("Données réinitialisées.")

    def handle_load_file(self):
        filepath = filedialog.askopenfilename(
            title="Ouvrir un fichier de budget",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        if not filepath: return

        if self.view.ask_confirmation("Confirmer le chargement", 
                                   "Charger ce fichier écrasera les données actuelles. Continuer ?"):
            success, message = self.model.load_data(filepath)
            self.view.update_status(message if success else f"Erreur: {message}")
            self._refresh_view()
            
    def handle_show_graph(self):
        # AMÉLIORATION: Passe une fonction "callback" à la vue pour qu'elle puisse obtenir des données fraîches à tout moment.
        self.view.show_graph_window(self.model.get_graph_data)