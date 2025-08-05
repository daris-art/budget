# controller.py

from tkinter import filedialog, simpledialog, messagebox
import matplotlib.pyplot as plt
from pathlib import Path
from view import BudgetView
import json
from datetime import datetime
import tempfile
import os
from pdf_generator import PDFReportGenerator


class BudgetController:
    """
    Fait le lien entre la Vue et le Modèle.
    Gère la logique de l'application avec SQLite.
    """
    def __init__(self, model, master):
        self.model = model
        self.view = BudgetView(master, self)
        self.master = master
        self.handle_initial_load()
        self.master.protocol("WM_DELETE_WINDOW", self.handle_on_closing)

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
        self.update_mois_label()
        self._refresh_view()
        
        # Si aucun mois n'est disponible, proposer d'en créer un
        if not success and "Aucun mois disponible" in message:
            self.handle_create_new_mois()

    def handle_on_closing(self):
        """Gère la fermeture de l'application."""
        plt.close('all')
        self.view.master.destroy()
        
    def handle_create_new_mois(self):
        """Crée un nouveau mois."""
        nom_mois, salaire = self.view.demander_infos_nouveau_mois()
        
        if not nom_mois:
            return
        
        success, message = self.model.create_mois(nom_mois, salaire)
        self.view.update_status(message)
        
        if success:
            self._refresh_view()

        self.update_mois_label()

    def update_mois_label(self):
        if self.model.mois_actuel:
            self.view.update_mois_actuel(self.model.mois_actuel.nom)
        else:
            self.view.update_mois_actuel("Aucun mois")


    def handle_load_mois(self):
        """Charge un mois existant via la vue."""
        all_mois = self.model.get_all_mois()
        if not all_mois:
            self.view.update_status("Aucun mois disponible à charger.")
            return

        # Demander à la vue de présenter les mois disponibles
        selected_mois = self.view.demander_mois_a_charger(all_mois)
        if not selected_mois:
            return

        success, message = self.model.load_mois(selected_mois.nom)
        self.view.update_status(message)

        if success:
            self._refresh_view()

        self.update_mois_label()


    def handle_delete_mois(self):
        """Supprime un mois existant via la vue."""
        all_mois = self.model.get_all_mois()
        if not all_mois:
            self.view.informer_aucun_mois()
            return

        if len(all_mois) == 1 and self.model.mois_actuel:
            if not self.view.confirmer_suppression_unique():
                return

        selected_mois = self.view.demander_mois_a_supprimer(all_mois)
        if not selected_mois:
            return

        if not self.view.confirmer_suppression_mois(selected_mois.nom):
            return

        success, message = self.model.delete_mois(selected_mois.nom)
        self.view.update_status(message)

        if success:
            self._refresh_view()
            self.update_mois_label()

    def handle_duplicate_mois(self):
        """
        Appelé par le bouton « Dupliquer Mois » de la vue.
        Déclenche la duplication, puis rafraîchit tout l’écran.
        """
        ok, msg = self.model.dupliquer_mois()
        self.view.update_status(msg)

        if ok:
            # Nouveau mois déjà chargé comme actif par le modèle ;
            # il suffit de tout redessiner.
            self._refresh_view()
            self.update_mois_label()

    def handle_generate_pdf_report(self):
        """Lance la génération du rapport PDF pour le mois actuel."""
        if not self.model.mois_actuel:
            if self.view:
                self.view.show_message("Attention", "Aucun mois chargé à exporter.")
            return

        # Le callback qui sera exécuté après que l'utilisateur ait choisi un emplacement
        def on_pdf_path_selected(file_path):
            if not file_path:
                self.view.update_status("Export PDF annulé.")
                return

            self.view.update_status("Génération du PDF en cours...")
            
            # 1. Préparer les données pour le rapport
            _, _, _, categories_data = self.model.get_graph_data()
            report_data = {
                'mois_nom': self.model.mois_actuel.nom,
                'salaire': self.model.salaire,
                'depenses': self.model.depenses,
                'total_depenses': self.model.get_total_depenses(),
                'argent_restant': self.model.get_argent_restant(),
                'categories_data': categories_data
            }

            # 2. Générer l'image du graphique temporairement
            graph_path = self._create_temp_graph_image()

            # 3. Générer le PDF
            try:
                generator = PDFReportGenerator(report_data)
                generator.generate(file_path, graph_path)
                self.view.update_status(f"Rapport PDF sauvegardé : {Path(file_path).name}")
                # Afficher un message de succès
                self.view.show_message("Succès", f"Le rapport PDF a été sauvegardé avec succès sous le nom :\n{Path(file_path).name}")

            except Exception as e:
                # MODIFICATION ICI : AFFICHER UNE BOÎTE DE DIALOGUE D'ERREUR
                error_message = f"Une erreur est survenue lors de la création du PDF :\n\n{e}\n\nVérifiez que la police 'DejaVuSans.ttf' est bien dans le dossier du programme."
                self.view.update_status(f"Erreur PDF : {e}")
                self.view.show_message("Erreur de Génération PDF", error_message) # Utilise messagebox.showerror ou équivalent

            finally:
                # 4. Nettoyer le fichier image temporaire
                if graph_path and os.path.exists(graph_path):
                    os.unlink(graph_path)


        # Demander à la vue d'afficher la boîte de dialogue de sauvegarde
        default_filename = f"Rapport_{self.model.mois_actuel.nom.replace(' ', '_')}_{datetime.now().strftime('%Y-%m')}.pdf"
        self.view.show_save_file_dialog(
            title="Enregistrer le rapport PDF",
            default_filename=default_filename,
            callback=on_pdf_path_selected,
            file_extensions=".pdf"
        )

    # AJOUTER CETTE MÉTHODE UTILITAIRE
    def _create_temp_graph_image(self) -> str | None:
        """Génère l'image du graphique et la sauvegarde dans un fichier temporaire."""
        labels, values, argent_restant, categories_data = self.model.get_graph_data()
        
        if not labels or not values:
            return None
        
        try:
            # On utilise le code de la vue pour créer le graphique
            fig, ax1 = plt.subplots(figsize=(8, 5))
            fig.suptitle('Répartition des Dépenses par Catégorie', fontsize=14, fontweight='bold')
            
            if categories_data:
                cat_labels = list(categories_data.keys())
                cat_values = list(categories_data.values())
                colors = plt.cm.Set3(plt.np.linspace(0, 1, len(cat_labels)))
                
                # Créer le pie chart
                wedges, texts, autotexts = ax1.pie(cat_values, autopct='%1.1f%%', startangle=90, colors=colors)
                
                # Ajouter la légende
                ax1.legend(wedges, cat_labels,
                          title="Catégories",
                          loc="center left",
                          bbox_to_anchor=(1, 0, 0.5, 1))

                plt.setp(autotexts, size=8, weight="bold")
                ax1.set_title('')
            
            plt.tight_layout(rect=[0, 0, 0.75, 1])

            # Sauvegarder dans un fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return temp_file.name
            
        except Exception:
            plt.close()
            return None
        
    def handle_import_excel(self):
        from tkinter import Toplevel, Label, Entry, Button, filedialog, messagebox
        import pandas as pd
        from datetime import datetime

        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=[("Fichiers Excel", "*.xls *.xlsx")]
        )
        if not file_path:
            return

        # Fenêtre de saisie des dates
        date_window = Toplevel()
        date_window.title("Filtrer par période")

        Label(date_window, text="Date de début (JJ/MM/AAAA)").grid(row=0, column=0, padx=10, pady=5)
        start_entry = Entry(date_window)
        start_entry.grid(row=0, column=1, padx=10, pady=5)

        Label(date_window, text="Date de fin (JJ/MM/AAAA)").grid(row=1, column=0, padx=10, pady=5)
        end_entry = Entry(date_window)
        end_entry.grid(row=1, column=1, padx=10, pady=5)

        def lancer_import():
            try:
                start_date = datetime.strptime(start_entry.get(), "%d/%m/%Y")
                end_date = datetime.strptime(end_entry.get(), "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Erreur", "Format de date invalide. Utilisez JJ/MM/AAAA.")
                return

            try:
                df = pd.read_excel(file_path, header=9)

                if "Date" not in df.columns or "Libellé" not in df.columns or "Débit euros" not in df.columns:
                    messagebox.showerror("Erreur", "Colonnes 'Date', 'Libellé' ou 'Débit euros' manquantes.")
                    return

                # Convertir la colonne "Date" en datetime
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

                # Filtrer les lignes par date
                df_filtré = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

                depenses = []
                for _, row in df_filtré.iterrows():
                    libelle = str(row["Libellé"]).strip()
                    montant = row["Débit euros"]
                    if pd.notna(montant) and montant > 0:
                        depenses.append((libelle, float(montant)))

                if not depenses:
                    messagebox.showinfo("Aucune dépense", "Aucune dépense trouvée dans cette période.")
                    return

                # Format du nom avec les dates
                nom_base = f"Importé depuis Excel - {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
                nom_mois = nom_base

                # Vérifier les doublons
                mois_existants = [mois.nom for mois in self.model.get_all_mois()]
                suffixe = 1
                while nom_mois in mois_existants:
                    nom_mois = f"{nom_base} (copie {suffixe})"
                    suffixe += 1

                
                salaire = 0.0

                success, message = self.model.create_mois(nom_mois, salaire)
                self.view.update_status(message)

                if success:
                    for nom, montant in depenses:
                        self.model.add_expense(
                            nom=nom,
                            montant=montant,
                            categorie="Importée",
                            effectue=True,
                            emprunte=False
                        )
                    self._refresh_view()
                    self.update_mois_label()

            except Exception as e:
                messagebox.showerror("Erreur d'import", f"Erreur lors de l'import :\n{str(e)}")

            date_window.destroy()

        Button(date_window, text="Importer", command=lancer_import).grid(row=2, column=0, columnspan=2, pady=10)

    def on_rename_mois(self):
        if not self.model.mois_actuel:
            messagebox.showwarning("Aucun mois sélectionné",
                                   "Sélectionne ou crée d'abord un mois.")
            return

        # Demander le nouveau nom
        nouveau_nom = simpledialog.askstring(
            "Renommer mois",
            f"Nouveau nom pour « {self.model.mois_actuel.nom} » :",
            parent=self.view.master
        )
        if not nouveau_nom:
            return  # utilisateur a annulé ou champ vide

        ok, msg = self.model.rename_mois(self.model.mois_actuel.id, nouveau_nom)
        if ok:
            self.view.update_mois_actuel(nouveau_nom)
            """ self.view.refresh_mois_list()      # si ta vue affiche la liste des mois """
            messagebox.showinfo("Succès", msg)
        else:
            messagebox.showerror("Erreur", msg)
    
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
        self.view.scroll_to_bottom()
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