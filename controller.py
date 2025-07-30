# controller.py

from tkinter import filedialog, simpledialog, messagebox
import matplotlib.pyplot as plt
from pathlib import Path
from view import BudgetView
from datetime import datetime
import json


class BudgetController:
    """
    Fait le lien entre la Vue et le Modèle.
    Gère la logique de l'application avec SQLite.
    """
    def __init__(self, model, master):
        self.model = model
        self.view = BudgetView(master, self)
        self.master = master
        
        self.autosave_interval = 30000  # Réduit à 30 secondes car SQLite est plus rapide
        self.autosave_job = None
        
        self.handle_initial_load()
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)
        self.schedule_autosave()

    def _refresh_view(self):
        """Met à jour l'affichage de la vue."""
        self.view.set_display_salaire(self.model.salaire)
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        self.update_summary()
        
        # Mettre à jour le titre de la fenêtre avec le mois actuel
        if self.model.mois_actuel:
            self.master.title(f"Budget Manager - {self.model.mois_actuel.nom}")
        else:
            self.master.title("Budget Manager")

    def update_summary(self):
        """Met à jour le résumé financier."""
        total = self.model.get_total_depenses()
        total_effectue = self.model.get_total_depenses_effectuees()
        total_non_effectue = self.model.get_total_depenses_non_effectuees()
        restant = self.model.get_argent_restant()
        total_emprunte = self.model.get_total_emprunte()
        self.view.update_summary(total, restant, total_effectue, total_non_effectue, total_emprunte)
        
    def handle_initial_load(self):
        """Tente de charger le dernier mois utilisé au démarrage."""
        success, message = self.model.load_data_from_last_session()
        self.view.update_status(message)
        self._refresh_view()
        
        # Si aucun mois n'est disponible, proposer d'en créer un
        if not success and "Aucun mois disponible" in message:
            self.handle_create_new_mois()

    def handle_on_closing(self):
        """Gère la fermeture de l'application."""
        # Pas besoin de sauvegarde manuelle avec SQLite, les données sont automatiquement persistées
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        plt.close('all')
        self.view.master.destroy()
        
    def schedule_autosave(self):
        """Programme la sauvegarde automatique (principalement pour le salaire)."""
        if self.autosave_job:
            self.master.after_cancel(self.autosave_job)
        self.autosave_job = self.master.after(self.autosave_interval, self.handle_autosave)

    def handle_autosave(self):
        """Gère la sauvegarde automatique."""
        # Avec SQLite, la sauvegarde est automatique, on s'assure juste que le salaire est à jour
        if self.model.mois_actuel:
            self.model._save_mois_salaire()
            now = datetime.now().strftime("%H:%M:%S")
            self.view.update_status(f"Sauvegarde auto à {now}")
        self.schedule_autosave()

    def handle_create_new_mois(self):
        """Crée un nouveau mois."""
        nom_mois = simpledialog.askstring(
            "Nouveau mois", 
            "Nom du nouveau mois (ex: Janvier 2024):",
            initialvalue=f"{datetime.now().strftime('%B %Y')}"
        )
        
        if not nom_mois:
            return
            
        salaire_str = simpledialog.askstring(
            "Salaire", 
            f"Salaire pour {nom_mois}:",
            initialvalue="0"
        )
        
        try:
            salaire = float(salaire_str.replace(',', '.')) if salaire_str else 0.0
        except ValueError:
            salaire = 0.0
            
        success, message = self.model.create_mois(nom_mois, salaire)
        self.view.update_status(message)
        
        if success:
            self._refresh_view()

    def handle_load_mois(self):
        """Charge un mois existant."""
        all_mois = self.model.get_all_mois()
        
        if not all_mois:
            messagebox.showinfo("Information", "Aucun mois disponible. Créez un nouveau mois.")
            return
            
        # Créer une liste des noms de mois pour la sélection
        mois_names = [f"{mois.nom} (Salaire: {mois.salaire}€)" for mois in all_mois]
        
        # Utiliser une boîte de dialogue simple pour la sélection
        # Note: Vous pourriez vouloir créer une boîte de dialogue personnalisée plus élégante
        selected = self._show_selection_dialog("Charger un mois", "Sélectionnez un mois:", mois_names)
        
        if selected:
            # Extraire le nom original du mois
            selected_mois = all_mois[mois_names.index(selected)]
            success, message = self.model.load_mois(selected_mois.nom)
            self.view.update_status(message)
            
            if success:
                self._refresh_view()

    def handle_delete_mois(self):
        """Supprime un mois existant."""
        all_mois = self.model.get_all_mois()
        
        if not all_mois:
            messagebox.showinfo("Information", "Aucun mois disponible.")
            return
            
        if len(all_mois) == 1 and self.model.mois_actuel:
            if not messagebox.askyesno("Confirmation", 
                                     "Vous êtes sur le point de supprimer le seul mois disponible. "
                                     "Cela effacera toutes vos données. Continuer ?"):
                return
                
        mois_names = [mois.nom for mois in all_mois]
        selected = self._show_selection_dialog("Supprimer un mois", "Sélectionnez un mois à supprimer:", mois_names)
        
        if selected:
            if messagebox.askyesno("Confirmation", f"Supprimer définitivement le mois '{selected}' ?"):
                success, message = self.model.delete_mois(selected)
                self.view.update_status(message)
                
                if success:
                    self._refresh_view()

    def _show_selection_dialog(self, title, prompt, options):
        """Affiche une boîte de dialogue de sélection simple."""
        # Cette méthode utilise une approche simple avec des boîtes de dialogue
        # Vous pourriez vouloir créer une interface plus sophistiquée
        from tkinter import Toplevel, Listbox, Button, Label, SINGLE
        
        result = [None]
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                result[0] = options[selection[0]]
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
            
        dialog = Toplevel(self.master)
        dialog.title(title)
        dialog.geometry("400x460")
        dialog.transient(self.master)
        dialog.grab_set()
        
        Label(dialog, text=prompt, pady=10).pack()
        
        listbox = Listbox(dialog, selectmode=SINGLE)
        for option in options:
            listbox.insert('end', option)
        listbox.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_frame = Button(dialog)
        Button(dialog, text="Sélectionner", command=on_select).pack(side='left', padx=5, pady=5)
        Button(dialog, text="Annuler", command=on_cancel).pack(side='left', padx=5, pady=5)
        
        dialog.wait_window()
        return result[0]

    # NOUVELLES MÉTHODES pour l'import/export JSON (pour la compatibilité)
    def handle_export_to_json(self):
        """Exporte le mois actuel vers un fichier JSON."""
        if not self.model.mois_actuel:
            messagebox.showwarning("Attention", "Aucun mois chargé à exporter.")
            return
            
        filepath = filedialog.asksaveasfilename(
            title=f"Exporter {self.model.mois_actuel.nom}",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            initialfilename=f"{self.model.mois_actuel.nom.replace(' ', '_')}.json"
        )
        
        if not filepath:
            return
            
        try:
            data = {
                'salaire': self.model.salaire,
                'depenses': [
                    {
                        'nom': d.nom,
                        'montant': d.montant,
                        'categorie': d.categorie,
                        'effectue': d.effectue,
                        'emprunte': d.emprunte
                    }
                    for d in self.model.depenses
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            self.view.update_status(f"Export réussi vers {Path(filepath).name}")
            
        except Exception as e:
            self.view.update_status(f"Erreur d'export: {e}")

    def handle_import_from_json(self):
        """Importe des données depuis un fichier JSON vers le mois actuel."""
        if not self.model.mois_actuel:
            messagebox.showwarning("Attention", "Veuillez d'abord créer ou charger un mois.")
            return
            
        filepath = filedialog.askopenfilename(
            title="Importer depuis JSON",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        )
        
        if not filepath:
            return
            
        if not messagebox.askyesno("Confirmation", 
                                 "L'import remplacera toutes les dépenses actuelles. Continuer ?"):
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Effacer les dépenses actuelles
            self.model.depenses.clear()
            
            # Supprimer les dépenses de la base
            if self.model.mois_actuel.id:
                import sqlite3
                with sqlite3.connect(self.model.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM depenses WHERE mois_id = ?', (self.model.mois_actuel.id,))
                    conn.commit()
            
            # Importer le salaire
            if 'salaire' in data:
                self.model.set_salaire(data['salaire'])
                
            # Importer les dépenses
            for dep_data in data.get('depenses', []):
                self.model.add_expense(
                    nom=dep_data.get('nom', ''),
                    montant=dep_data.get('montant', 0.0),
                    categorie=dep_data.get('categorie', 'Autres'),
                    effectue=dep_data.get('effectue', False),
                    emprunte=dep_data.get('emprunte', False)
                )
                
            self._refresh_view()
            self.view.update_status(f"Import réussi depuis {Path(filepath).name}")
            
        except Exception as e:
            self.view.update_status(f"Erreur d'import: {e}")

    # Les méthodes existantes restent largement identiques
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
        if not self.model.mois_actuel:
            messagebox.showwarning("Attention", "Veuillez d'abord créer ou charger un mois.")
            return
            
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
        if not self.model.mois_actuel:
            return
            
        if self.view.ask_confirmation("Confirmation", 
                                    f"Effacer toutes les dépenses du mois '{self.model.mois_actuel.nom}' ? "
                                    "Cette action est irréversible."):
            # Supprimer toutes les dépenses du mois actuel
            if self.model.mois_actuel.id:
                import sqlite3
                try:
                    with sqlite3.connect(self.model.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM depenses WHERE mois_id = ?', (self.model.mois_actuel.id,))
                        conn.commit()
                except sqlite3.Error:
                    pass
                    
            self.model.depenses = []
            self._refresh_view()
            self.view.update_status("Dépenses réinitialisées.")

    def handle_load_file(self):
        """Remplacé par handle_load_mois pour la version SQLite."""
        self.handle_load_mois()
            
    def handle_show_graph(self):
        self.view.show_graph_window(self.model.get_graph_data)