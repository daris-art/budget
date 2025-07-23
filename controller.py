# controller.py

from tkinter import filedialog
import matplotlib.pyplot as plt
from pathlib import Path # Importer Path
from view import BudgetView
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
        
        self.autosave_interval = 60000 
        self.autosave_job = None
        
        self.handle_initial_load()
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)
        self.schedule_autosave()

    def _refresh_view(self):
        self.view.set_display_salaire(self.model.salaire)
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        self.update_summary()

    def update_summary(self):
        total = self.model.get_total_depenses()
        total_effectue = self.model.get_total_depenses_effectuees()
        total_non_effectue = self.model.get_total_depenses_non_effectuees()
        restant = self.model.get_argent_restant()
        total_emprunte = self.model.get_total_emprunte()
        self.view.update_summary(total, restant, total_effectue, total_non_effectue, total_emprunte)
        
    # AMÉLIORATION: Charge le dernier fichier utilisé au démarrage
    def handle_initial_load(self):
        """Tente de charger le dernier fichier utilisé, sinon charge le fichier par défaut."""
        last_file_path = self.model.load_last_file_path()
        
        # Essayer de charger le dernier fichier s'il existe
        if last_file_path and last_file_path.exists():
            success, message = self.model.load_data(last_file_path)
        else:
            # Sinon, charger le fichier par défaut
            success, message = self.model.load_data()
            
        self.view.update_status(message)
        self._refresh_view()

    # AMÉLIORATION: Sauvegarde le chemin du fichier actuel avant de fermer
    def handle_on_closing(self):
        """Sauvegarde les données et la configuration avant de fermer l'application."""
        self.handle_save()
        # Enregistre le chemin du fichier actuellement utilisé pour la prochaine session
        self.model.save_last_file_path(self.model.data_file)
        
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        plt.close('all')
        self.view.master.destroy()
        
    def schedule_autosave(self):
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        self.autosave_job = self.master.after(self.autosave_interval, self.handle_autosave)

    def handle_autosave(self):
        self.handle_save(is_auto=True)
        self.schedule_autosave()

    def handle_save_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Sauvegarder le budget sous...",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        if not filepath:
            self.view.update_status("Sauvegarde annulée.")
            return
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
        nom, montant_str, categorie, effectue, emprunte = self.view.get_expense_value(index)
        if nom is not None:
            self.model.update_expense(index, nom, montant_str, categorie, effectue, emprunte)
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
            self.view.update_status(message)
            self._refresh_view()
            
    def handle_show_graph(self):
        self.view.show_graph_window(self.model.get_graph_data)