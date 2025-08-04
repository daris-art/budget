# controller.py
from view import BudgetView
from datetime import datetime
# Le contrôleur n'a plus besoin d'importer os, tempfile, ou pyplot !
from pdf_generator import PDFReportGenerator # On importe le générateur PDF
from view import BudgetView

class BudgetController:
    """
    Fait le lien entre la Vue et le Modèle.
    Gère la logique de l'application en orchestrant les appels.
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
        
        if self.model.mois_actuel:
            self.master.title(f"Budget Manager - {self.model.mois_actuel.nom}")
        else:
            self.master.title("Budget Manager")

    def update_summary(self):
        """Met à jour le résumé financier en demandant les calculs au modèle."""
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
        
        if not success and "Aucun mois disponible" in message:
            self.handle_create_new_mois()

    def handle_on_closing(self):
        """Gère la fermeture propre de l'application."""
        import matplotlib.pyplot as plt # Import local pour une tâche de vue
        plt.close('all')
        self.view.master.destroy()
        
    def handle_create_new_mois(self):
        """Orchestre la création d'un nouveau mois."""
        # La vue est responsable de demander les informations
        nom_mois, salaire = self.view.demander_infos_nouveau_mois()
        if not nom_mois:
            return
        
        # Le modèle est responsable de la création
        success, message = self.model.create_mois(nom_mois, salaire)
        self.view.update_status(message)
        
        if success:
            self._refresh_view()
        self.update_mois_label()

    def update_mois_label(self):
        """Met à jour le label du mois dans la vue."""
        if self.model.mois_actuel:
            self.view.update_mois_actuel(self.model.mois_actuel.nom)
        else:
            self.view.update_mois_actuel("Aucun mois")

    def handle_load_mois(self):
        """Orchestre le chargement d'un mois."""
        all_mois = self.model.get_all_mois()
        if not all_mois:
            self.view.update_status("Aucun mois disponible à charger.")
            return

        selected_mois = self.view.demander_mois_a_charger(all_mois)
        if not selected_mois:
            return

        success, message = self.model.load_mois(selected_mois.nom)
        self.view.update_status(message)

        if success:
            self._refresh_view()
        self.update_mois_label()

    def handle_delete_mois(self):
        """Orchestre la suppression d'un mois."""
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
        """Demande la duplication du mois au modèle."""
        ok, msg = self.model.dupliquer_mois()
        self.view.update_status(msg)
        if ok:
            self._refresh_view()
            self.update_mois_label()

    def handle_generate_pdf_report(self):
        """
        Orchestre la génération du PDF.
        Le contrôleur ne fait que collecter les données et appeler le générateur.
        """
        if not self.model.mois_actuel:
            self.view.show_message("Attention", "Aucun mois chargé à exporter.")
            return

        # Le callback est simple : il appelle le générateur.
        def on_pdf_path_selected(file_path):
            if not file_path:
                self.view.update_status("Export PDF annulé.")
                return

            self.view.update_status("Génération du PDF en cours...")
            
            # 1. Préparer les données (ça, c'est le rôle du contrôleur)
            _, _, _, categories_data = self.model.get_graph_data()
            report_data = {
                'mois_nom': self.model.mois_actuel.nom,
                'salaire': self.model.salaire,
                'depenses': self.model.depenses,
                'total_depenses': self.model.get_total_depenses(),
                'argent_restant': self.model.get_argent_restant(),
                'categories_data': categories_data
            }

            # 2. Instancier et lancer le générateur (logique déportée)
            generator = PDFReportGenerator(report_data)
            success, message = generator.generate(file_path)

            # 3. Mettre à jour la vue avec le résultat
            self.view.update_status(message)
            if success:
                self.view.show_message("Succès", f"Le rapport PDF a été sauvegardé avec succès.")
            else:
                self.view.show_message("Erreur de Génération PDF", message, "error")

        # La vue gère l'affichage de la boîte de dialogue
        default_filename = f"Rapport_{self.model.mois_actuel.nom.replace(' ', '_')}_{datetime.now().strftime('%Y-%m')}.pdf"
        self.view.show_save_file_dialog(
            title="Enregistrer le rapport PDF",
            default_filename=default_filename,
            callback=on_pdf_path_selected,
            file_extensions=".pdf"
        )
    
    def on_rename_mois(self):
        """Orchestre le renommage du mois."""
        if not self.model.mois_actuel:
            self.view.show_message("Attention", "Aucun mois sélectionné", "warning")
            return

        nouveau_nom = self.view.ask_string_dialog(
            "Renommer mois",
            f"Nouveau nom pour « {self.model.mois_actuel.nom} » :"
        )
        if not nouveau_nom:
            return

        ok, msg = self.model.rename_mois(self.model.mois_actuel.id, nouveau_nom)
        
        if ok:
            self.view.update_mois_actuel(nouveau_nom)
            self.view.show_message("Succès", msg)
        else:
            self.view.show_message("Erreur", msg, "error")

    # --- MÉTHODES DE MANIPULATION DES DONNÉES ---

    def handle_salaire_update(self, *args):
        salaire_str = self.view.salaire_var.get()
        self.model.set_salaire(salaire_str)
        self.update_summary()

    def handle_expense_update(self, index):
        # La vue fournit les valeurs, le contrôleur les passe au modèle
        values = self.view.get_expense_value(index)
        if values is not None:
            nom, montant_str, categorie, effectue, emprunte = values
            self.model.update_expense(index, nom, montant_str, categorie, effectue, emprunte)
            self.update_summary()
            
    def handle_add_expense(self):
        if not self.model.mois_actuel:
            self.view.show_message("Attention", "Veuillez d'abord créer ou charger un mois.", "warning")
            return
        
        # Le modèle ajoute une dépense vide
        self.model.add_expense()
        # La vue redessine
        self.view.redraw_expenses(self.model.depenses, self.model.categories)
        self.view.focus_on_last_expense()
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
                                    f"Effacer toutes les dépenses du mois '{self.model.mois_actuel.nom}' ?"):
            # On demande au modèle de se réinitialiser
            self.model.clear_current_month_expenses()
            self._refresh_view()
            self.view.update_status("Dépenses réinitialisées.")

    def handle_show_graph(self):
        """
        Orchestre l'affichage de la fenêtre des graphiques.
        """
        # 1. Vérification des prérequis (rôle du contrôleur)
        if not self.model.mois_actuel:
            self.view.show_message("Attention", "Veuillez d'abord charger ou créer un mois.", "warning")
            return

        # Vérification pour éviter d'ouvrir une fenêtre vide
        if not self.model.depenses:
            self.view.show_message("Information", "Il n'y a aucune dépense à afficher dans le graphique.")
            return

        # 2. Délégation à la Vue (rôle de la vue)
        # Le contrôleur demande à la vue d'afficher la fenêtre et lui fournit
        # le moyen d'obtenir les données (le callback vers le modèle).
        self.view.show_graph_window(self.model.get_graph_data)


    def handle_import_excel(self):
        """
        Orchestre l'import depuis un fichier Excel en respectant l'architecture MVC.
        """
        # 1. Demander à la vue le chemin du fichier
        file_path = self.view.ask_open_file_dialog(
            title="Sélectionner un fichier Excel",
            filetypes=[("Fichiers Excel", "*.xls *.xlsx")]
        )
        if not file_path:
            self.view.update_status("Import annulé.")
            return

        # 2. Demander à la vue la plage de dates
        start_date_str, end_date_str = self.view.ask_date_range_for_import()
        if not start_date_str or not end_date_str:
            self.view.update_status("Import annulé.")
            return

        self.view.update_status("Import en cours, veuillez patienter...")
        
        # 3. Demander au modèle de faire tout le travail
        # Le modèle gère la lecture du fichier, la validation, la création du mois et l'ajout des dépenses.
        success, message = self.model.import_from_excel(file_path, start_date_str, end_date_str)

        # 4. Mettre à jour la vue avec le résultat
        self.view.update_status(message)
        if success:
            # Rafraîchir l'écran pour afficher le nouveau mois importé
            self._refresh_view()
            self.update_mois_label()
            self.view.show_message("Succès", message)
        else:
            # Afficher un message d'erreur si l'import a échoué
            self.view.show_message("Erreur d'import", message, "error")