# view.py - Vue principale de l'application

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import logging

from utils import MoisDisplayData, Depense, Mois, MoisInput
from graph_view import GraphWindow
from dialogs import MoisSelectionDialog, Tooltip

logger = logging.getLogger(__name__)

class BudgetView:
    """
    Vue principale - Responsable uniquement de l'interface utilisateur
    """
    
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self.depenses_widgets = []
        self.graph_window = None

        self.salaire_var = tk.StringVar()
        self.total_depenses_var = tk.StringVar(value="Total Dépenses : 0.00 €")
        self.total_effectue_var = tk.StringVar(value="Total Effectué : 0.00 €")
        self.total_non_effectue_var = tk.StringVar(value="Dépenses non effectuées : 0.00 €")
        self.argent_restant_var = tk.StringVar(value="Argent restant : 0.00 €")
        self.total_emprunte_var = tk.StringVar(value="Total Emprunté : 0.00 €")
        self.status_var = tk.StringVar()
        self.mois_actuel_var = tk.StringVar(value="Aucun mois sélectionné")
        
        self.salaire_var.trace_add("write", self.controller.handle_salaire_update)

        self._configure_styles()
        self._create_widgets()
        
        logger.info("BudgetView initialisée")

    def _configure_styles(self):
        """Configure les styles visuels"""
        style = ttk.Style()
        
        style.configure("TLabel", font=("Arial", 10))
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Header.TLabel", font=("Arial", 10, "underline"))
        style.configure("Result.TLabel", font=("Arial", 14, "bold"))
        style.configure("TotalDepenses.TLabel", font=("Arial", 13, "bold"), foreground="purple")
        style.configure("Effectue.TLabel", font=("Arial", 12, "bold"))
        style.configure("NonEffectue.TLabel", font=("Arial", 12, "bold"), foreground="#E74C3C")
        style.configure("Emprunte.TLabel", font=("Arial", 10, "bold"), foreground="#007bff")
        style.configure("Status.TLabel", font=("Arial", 9), foreground="grey")
        style.configure("Month.TLabel", foreground="#3A3A3A", 
                       font=("Segoe UI", 19, "underline bold"), padding=5)
        
        style.configure("Red.TButton", foreground="white", background="#f44336", 
                       font=("Arial", 9, "bold"))
        style.map("Red.TButton", background=[('active', '#d32f2f')])
        style.configure("Blue.TButton", foreground="white", background="#2196F3", 
                       font=("Arial", 10))
        style.map("Blue.TButton", background=[('active', '#1976D2')])
        style.configure("Green.TButton", foreground="white", background="#4CAF50", 
                       font=("Arial", 10, "bold"))
        style.map("Green.TButton", background=[('active', '#45a049')])
        
        style.configure("Orange.TButton", foreground="white", background="#ff9800",
                       font=("Arial", 10))
        style.map("Orange.TButton", background=[('active', '#f57c00')])

        style.configure("Gray.TButton", foreground="white", background="#6c757d",
                       font=("Arial", 10))
        style.map("Gray.TButton", background=[('active', '#5a6268')])
        
        style.configure("Effectue.TCheckbutton", font=("Arial", 11))
        style.map("Effectue.TCheckbutton",
                  indicatorcolor=[('selected', '#28a745'), ('!selected', 'white')],
                  background=[('active', '#e9ecef')])
        
        style.configure("Emprunte.TCheckbutton", font=("Arial", 11))
        style.map("Emprunte.TCheckbutton",
                  indicatorcolor=[('selected', '#007bff'), ('!selected', 'white')],
                  background=[('active', '#e9ecef')])
        
        style.configure("StatusFrame.TFrame", borderwidth=1)
        style.map('TCombobox', fieldbackground=[('readonly', 'white')])
        style.map('TCombobox', selectbackground=[('readonly', 'blue')])
        style.map('TCombobox', selectforeground=[('readonly', 'white')])

    def _create_widgets(self):
        """Crée tous les widgets de l'interface"""
        try:
            self.master.title("Calculateur de Budget Mensuel (MVC) - Amélioré")
            self.master.geometry("1024x930")
            self.master.minsize(960, 600)
            
            main_frame = ttk.Frame(self.master, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)

            self._create_file_management_section(main_frame)
            self._create_salary_section(main_frame)
            self._create_expenses_section(main_frame)
            self._create_actions_section(main_frame)
            self._create_summary_section(main_frame)
            self._create_status_bar()
            
            logger.info("Interface créée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'interface: {e}")
            raise

    def _create_file_management_section(self, parent):
        """Crée la section de gestion des fichiers/mois"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(5, 15))

        buttons_frame = ttk.Frame(top_frame)
        buttons_frame.pack()

        bouton_charger_mois = ttk.Button(
            buttons_frame, text="📂 Charger Mois", 
            command=self.controller.handle_load_mois, style="Blue.TButton"
        )
        bouton_charger_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_charger_mois, "Charger un budget mensuel existant")

        bouton_nouveau_mois = ttk.Button(
            buttons_frame, text="➕ Nouveau Mois", 
            command=self.controller.handle_create_new_mois, style="Green.TButton"
        )
        bouton_nouveau_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_nouveau_mois, "Créer un nouveau budget mensuel")

        bouton_importer_excel = ttk.Button(
            buttons_frame, text="📥 Importer Excel",
            command=self.controller.handle_import_from_excel, style="Green.TButton"
        )
        bouton_importer_excel.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_importer_excel, "Créer un nouveau mois à partir d'un relevé de compte Excel")


        bouton_renommer = ttk.Button(
            buttons_frame, text="✏️ Renommer Mois",
            command=self.controller.handle_rename_mois, style="Gray.TButton"
        )
        bouton_renommer.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_renommer, "Renommer le mois actuel")
        
        bouton_dupliquer = ttk.Button(
            buttons_frame, text="📋 Dupliquer Mois",
            command=self.controller.handle_duplicate_mois, style="Orange.TButton"
        )
        bouton_dupliquer.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_dupliquer, "Crée une copie du mois actuel avec toutes ses dépenses")

        bouton_supprimer_mois = ttk.Button(
            buttons_frame, text="🗑️ Supprimer Mois", 
            command=self.controller.handle_delete_mois, style="Red.TButton"
        )
        bouton_supprimer_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_supprimer_mois, "Supprimer définitivement un mois")

        self.label_mois_actuel = ttk.Label(
            top_frame, 
            textvariable=self.mois_actuel_var, 
            style="Month.TLabel",
            justify=tk.CENTER
        )
        self.label_mois_actuel.pack(pady=(10, 0))

    def _create_salary_section(self, parent):
        """Crée la section de saisie du salaire"""
        salary_frame = ttk.Frame(parent)
        salary_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(salary_frame, text="Votre Salaire (€) :", style="Title.TLabel").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        
        validate_cmd = (self.master.register(self._validate_numeric_input), '%P')
        self.entree_salaire = ttk.Entry(
            salary_frame, textvariable=self.salaire_var, 
            validate="key", validatecommand=validate_cmd
        )
        self.entree_salaire.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _create_expenses_section(self, parent):
        """Crée la section des dépenses"""
        expenses_main_frame = ttk.LabelFrame(
            parent, text="Vos Dépenses Mensuelles (€)", 
            style="Title.TLabel", padding="10"
        )
        expenses_main_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        header_frame = ttk.Frame(expenses_main_frame)
        header_frame.pack(fill=tk.X, padx=(40, 17), pady=(0, 2))
        
        ttk.Label(header_frame, text="Nom de la Dépense", style="Header.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(15, 0)
        )
        ttk.Label(header_frame, text="Catégorie", style="Header.TLabel").pack(
            side=tk.RIGHT, padx=(0, 320)
        )
        ttk.Label(header_frame, text="Montant (€)", style="Header.TLabel").pack(
            side=tk.RIGHT, padx=(0, 80)
        )
        
        self.canvas = tk.Canvas(expenses_main_frame, borderwidth=0)
        self.scrollable_frame = ttk.Frame(self.canvas)
        scrollbar = ttk.Scrollbar(expenses_main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.scrollable_frame.bind(
            "<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            '<Configure>', 
            lambda e: self.canvas.itemconfig(canvas_frame, width=e.width)
        )

    def _create_actions_section(self, parent):
        """Crée la section des boutons d'action"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=5)
        
        bouton_ajouter = ttk.Button(
            action_frame, text="➕ Ajouter une dépense", 
            command=self.controller.handle_add_expense, style="Green.TButton"
        )
        bouton_ajouter.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(bouton_ajouter, "Ajouter une dépense mensuelle à la liste")

        bouton_trier = ttk.Button(
            action_frame, text="🔽 Trier par Montant", 
            command=self.controller.handle_sort, style="Blue.TButton"
        )
        bouton_trier.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_trier, "Trier les dépenses par montant décroissant")

        bouton_graph = ttk.Button(
            action_frame, text="📈 Voir Graphique", 
            command=self.controller.handle_show_graph, style="Blue.TButton"
        )
        bouton_graph.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_graph, "Afficher une représentation graphique des dépenses")
        
        # --- Boutons déplacés ici ---
        bouton_export = ttk.Button(
            action_frame, text="📤 Exporter JSON", 
            command=self.controller.handle_export_to_json, style="Blue.TButton"
        )
        bouton_export.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_export, "Exporter le mois actuel vers un fichier JSON")

        bouton_import = ttk.Button(
            action_frame, text="📥 Importer JSON", 
            command=self.controller.handle_import_from_json, style="Blue.TButton"
        )
        bouton_import.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_import, "Importer des données depuis un fichier JSON")

    def _create_summary_section(self, parent):
        """Crée la section de résumé financier"""
        summary_frame = ttk.Frame(parent, padding="10 0")
        summary_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        line1_frame = ttk.Frame(summary_frame)
        line1_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.label_total_depenses = ttk.Label(
            line1_frame, textvariable=self.total_depenses_var, style="TotalDepenses.TLabel"
        )
        self.label_total_depenses.pack(side=tk.LEFT, anchor="w")
        
        self.label_total_effectue = ttk.Label(
            line1_frame, textvariable=self.total_effectue_var, style="Effectue.TLabel"
        )
        self.label_total_effectue.pack(side=tk.RIGHT, anchor="e")

        line2_frame = ttk.Frame(summary_frame)
        line2_frame.pack(fill=tk.X, pady=(2, 10))
        
        self.label_resultat = ttk.Label(
            line2_frame, textvariable=self.argent_restant_var, style="Result.TLabel"
        )
        self.label_resultat.pack(side=tk.LEFT, anchor="w")
        
        self.label_total_non_effectue = ttk.Label(
            line2_frame, textvariable=self.total_non_effectue_var, style="NonEffectue.TLabel"
        )
        self.label_total_non_effectue.pack(side=tk.RIGHT, anchor="e")
        
        line3_frame = ttk.Frame(summary_frame)
        line3_frame.pack(fill=tk.X, pady=(2, 5))
        
        self.label_total_emprunte = ttk.Label(
            line3_frame, textvariable=self.total_emprunte_var, style="Emprunte.TLabel"
        )
        self.label_total_emprunte.pack(side=tk.LEFT, anchor="w")

        bouton_reset = ttk.Button(
            summary_frame, text="🔄 Réinitialiser Tout", 
            command=self.controller.handle_reset, style="Red.TButton"
        )
        bouton_reset.pack(fill=tk.X, pady=(5, 0))
        Tooltip(bouton_reset, "Réinitialiser toutes les données saisies")

    def _create_status_bar(self):
        """Crée la barre de statut"""
        status_bar = ttk.Frame(self.master, relief=tk.SUNKEN, padding="2 5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            status_bar, textvariable=self.status_var, style="Status.TLabel"
        )
        self.status_label.pack(side=tk.LEFT)

    # ===== MÉTHODES D'INTERFACE PUBLIQUES =====
    def update_complete_display(self, display_data: MoisDisplayData, categories: List[str]):
        """Met à jour complètement l'affichage"""
        try:
            self.mois_actuel_var.set(display_data.nom)
            self.set_salaire_display(display_data.salaire)
            self.update_expenses_display(display_data.depenses, categories)
            self.update_summary_display(display_data)
            
            if display_data.nom != "Aucun mois":
                self.master.title(f"Budget Manager - {display_data.nom}")
            else:
                self.master.title("Budget Manager")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour complète: {e}")

    def update_expenses_display(self, depenses: List[Depense], categories: List[str]):
        """Met à jour l'affichage des dépenses (redessin complet)"""
        try:
            for widget_dict in self.depenses_widgets:
                widget_dict['frame'].destroy()
            self.depenses_widgets.clear()

            for i, depense in enumerate(depenses):
                self._create_expense_widget(i, depense, categories)
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des dépenses: {e}")

    def add_expense_widget(self, depense: Depense, categories: List[str]):
        """Ajoute un seul widget de dépense à la fin de la liste."""
        try:
            index = len(self.depenses_widgets)
            self._create_expense_widget(index, depense, categories)
            self.master.update_idletasks()
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du widget de dépense: {e}")

    def remove_expense_widget(self, index: int):
        """Supprime un seul widget de dépense de la liste."""
        try:
            if 0 <= index < len(self.depenses_widgets):
                widget_dict = self.depenses_widgets.pop(index)
                widget_dict['frame'].destroy()
                self._reindex_widgets(start_index=index)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du widget de dépense: {e}")
    
    def _reindex_widgets(self, start_index: int):
        """Met à jour les callbacks des widgets après une suppression pour refléter les nouveaux indices."""
        for i in range(start_index, len(self.depenses_widgets)):
            widget_dict = self.depenses_widgets[i]
            
            new_callback = lambda *args, idx=i: self.controller.handle_expense_update(idx)
            
            widget_dict['remove_button'].configure(command=lambda idx=i: self.controller.handle_remove_expense(idx))
            
            for var_name in ['montant_var', 'categorie_var', 'effectue_var', 'emprunte_var', 'nom_var']:
                var = widget_dict[var_name]
                if var.trace_info():
                    trace_name = var.trace_info()[0][1]
                    var.trace_remove('write', trace_name)
                var.trace_add('write', new_callback)

    def clear_for_loading(self, status_message: str):
        """Prépare l'interface pour un chargement en effaçant les données actuelles."""
        try:
            for widget_dict in self.depenses_widgets:
                widget_dict['frame'].destroy()
            self.depenses_widgets.clear()
            
            self.mois_actuel_var.set("")
            if self.salaire_var.trace_info():
                trace_name = self.salaire_var.trace_info()[0][1]
                self.salaire_var.trace_remove('write', trace_name)
            self.salaire_var.set("0.00")
            self.salaire_var.trace_add('write', self.controller.handle_salaire_update)
            
            empty_data = MoisDisplayData(nom="", salaire=0, depenses=[], total_depenses=0,
                                         argent_restant=0, total_effectue=0, total_non_effectue=0,
                                         total_emprunte=0)
            self.update_summary_display(empty_data)
            
            self.update_status(status_message)
            self.master.update_idletasks()
        except Exception as e:
            logger.error(f"Erreur lors de la préparation au chargement: {e}")

    def update_summary_display(self, display_data: MoisDisplayData):
        """Met à jour le résumé financier"""
        try:
            self.total_depenses_var.set(
                f"Total Dépenses : {display_data.total_depenses:,.2f} €".replace(',', ' ')
            )
            self.argent_restant_var.set(
                f"Argent restant : {display_data.argent_restant:,.2f} €".replace(',', ' ')
            )
            self.total_effectue_var.set(
                f"Total Effectué : {display_data.total_effectue:,.2f} €".replace(',', ' ')
            )
            self.total_non_effectue_var.set(
                f"Non effectué : {display_data.total_non_effectue:,.2f} €".replace(',', ' ')
            )
            self.total_emprunte_var.set(
                f"Total Emprunté : {display_data.total_emprunte:,.2f} €".replace(',', ' ')
            )

            if display_data.argent_restant < 0:
                self.label_resultat.config(foreground="red")
            else:
                self.label_resultat.config(foreground="green")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du résumé: {e}")

    def set_salaire_display(self, salaire: float):
        """Met à jour l'affichage du salaire"""
        try:
            if self.salaire_var.trace_info():
                trace_name = self.salaire_var.trace_info()[0][1]
                self.salaire_var.trace_remove('write', trace_name)
            
            current_val = self.salaire_var.get().replace(',', '.')
            if current_val != f"{salaire:.2f}":
                self.salaire_var.set(f"{salaire:.2f}")
                
            self.salaire_var.trace_add('write', self.controller.handle_salaire_update)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du salaire: {e}")

    def update_mois_title(self, new_name: str):
        """Met à jour uniquement le titre du mois et le titre de la fenêtre."""
        try:
            self.mois_actuel_var.set(new_name)
            self.master.title(f"Budget Manager - {new_name}")
            self.update_status(f"Mois renommé en '{new_name}'.")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du titre du mois: {e}")

    # ===== MÉTHODES D'INTERACTION AVEC L'UTILISATEUR =====
    def get_new_mois_input(self) -> Optional[MoisInput]:
        """Récupère les données de création d'un nouveau mois"""
        try:
            nom_mois = self.ask_for_string(
                "Nouveau mois", 
                "Nom du nouveau mois (ex: Janvier 2024):",
                f"{datetime.now().strftime('%B %Y')}"
            )
            if not nom_mois: return None
                
            salaire_str = self.ask_for_string("Salaire", f"Salaire pour {nom_mois}:", "0")
            if salaire_str is None: return None
                
            return MoisInput(nom=nom_mois, salaire=salaire_str or "0")
            
        except Exception as e:
            logger.error(f"Erreur lors de la saisie du nouveau mois: {e}")
            return None

    def ask_for_string(self, title: str, prompt: str, initial_value: str = "") -> Optional[str]:
        """Affiche une boîte de dialogue pour demander une chaîne de caractères."""
        return simpledialog.askstring(title, prompt, initialvalue=initial_value, parent=self.master)

    def show_mois_selection_dialog(self, mois_list: List[Mois], 
                                  title: str = "Charger un mois",
                                  prompt: str = "Sélectionnez un mois:") -> Optional[Mois]:
        """Affiche une boîte de dialogue de sélection de mois"""
        try:
            dialog = MoisSelectionDialog(self.master, mois_list, title, prompt)
            return dialog.result
        except Exception as e:
            logger.error(f"Erreur lors de la sélection de mois: {e}")
            return None

    def get_export_filepath(self, mois_nom: str) -> Optional[Path]:
        """Récupère le chemin d'export"""
        try:
            filepath = filedialog.asksaveasfilename(
                title=f"Exporter {mois_nom}",
                defaultextension=".json",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
                initialfile=f"{mois_nom.replace(' ', '_')}.json"
            )
            return Path(filepath) if filepath else None
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du fichier d'export: {e}")
            return None

    def get_import_filepath(self) -> Optional[Path]:
        """Récupère le chemin d'import"""
        try:
            filepath = filedialog.askopenfilename(
                title="Importer depuis JSON",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
            )
            return Path(filepath) if filepath else None
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du fichier d'import: {e}")
            return None

    def get_salaire_value(self) -> str:
        return self.salaire_var.get()

    def get_expense_value(self, index: int) -> Optional[Tuple[str, str, str, bool, bool]]:
        """Récupère les valeurs d'une dépense"""
        try:
            if 0 <= index < len(self.depenses_widgets):
                widgets = self.depenses_widgets[index]
                nom = widgets['nom_var'].get()
                montant = widgets['montant_var'].get().replace(',', '.')
                categorie = widgets['categorie_var'].get()
                effectue = widgets['effectue_var'].get()
                emprunte = widgets['emprunte_var'].get()
                return nom, montant, categorie, effectue, emprunte
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la dépense {index}: {e}")
            return None

    def focus_last_expense(self):
        """Donne le focus à la dernière dépense"""
        try:
            if self.depenses_widgets:
                last_entry = self.depenses_widgets[-1]['frame'].winfo_children()[1]
                last_entry.focus_set()
        except Exception as e:
            logger.error(f"Erreur lors du focus sur la dernière dépense: {e}")

    def scroll_to_bottom(self):
        """Fait défiler la liste des dépenses jusqu'en bas."""
        try:
            self.master.after(100, lambda: self.canvas.yview_moveto(1.0))
        except Exception as e:
            logger.warning(f"Impossible de faire défiler vers le bas: {e}")

    # ===== MÉTHODES DE MESSAGES =====
    def show_error_message(self, message: str):
        messagebox.showerror("Erreur", message, parent=self.master)

    def show_warning_message(self, message: str):
        messagebox.showwarning("Attention", message, parent=self.master)

    def show_info_message(self, message: str):
        messagebox.showinfo("Information", message, parent=self.master)

    def ask_confirmation(self, title: str, message: str) -> bool:
        return messagebox.askyesno(title, message, parent=self.master)

    def update_status(self, message: str):
        self.status_var.set(message)

    # ===== GRAPHIQUES =====
    def show_graph_window(self, get_data_callback: Callable):
        try:
            if self.graph_window and self.graph_window.winfo_exists():
                self.graph_window.lift()
                return
            self.graph_window = GraphWindow(self.master, get_data_callback)
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture de la fenêtre graphique: {e}")

    # ===== MÉTHODES PRIVÉES =====
    def _create_expense_widget(self, index: int, depense: Depense, categories: List[str]):
        """Crée un widget pour une dépense"""
        try:
            expense_frame = ttk.Frame(self.scrollable_frame)
            expense_frame.pack(fill=tk.X, pady=1, padx=0)

            nom_var = tk.StringVar(value=depense.nom)
            montant_var = tk.StringVar(value=f"{depense.montant:.2f}")
            categorie_var = tk.StringVar(value=depense.categorie)
            effectue_var = tk.BooleanVar(value=depense.effectue)
            emprunte_var = tk.BooleanVar(value=depense.emprunte)
            
            remove_button = ttk.Button(
                expense_frame, text="X", width=3, style="Red.TButton", 
                command=lambda i=index: self.controller.handle_remove_expense(i)
            )
            remove_button.pack(side=tk.LEFT, padx=(0, 10))

            nom_entry = ttk.Entry(expense_frame, textvariable=nom_var)
            nom_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
            validate_cmd = (self.master.register(self._validate_numeric_input), '%P')
            montant_entry = ttk.Entry(
                expense_frame, textvariable=montant_var, width=10, 
                justify='right', validate="key", validatecommand=validate_cmd
            )
            montant_entry.pack(side=tk.LEFT, padx=(15, 10))
            
            cat_combo = ttk.Combobox(
                expense_frame, textvariable=categorie_var, values=categories, 
                width=15, state="readonly"
            )
            cat_combo.pack(side=tk.LEFT, padx=(10, 0))

            status_frame = ttk.Frame(expense_frame, padding="5 2", style="StatusFrame.TFrame")
            status_frame.pack(side=tk.LEFT, padx=(2, 0))

            check_effectue = ttk.Checkbutton(
                status_frame, text=" ✔️Payée", variable=effectue_var,
                onvalue=True, offvalue=False, style="Effectue.TCheckbutton"
            )
            check_effectue.pack(side=tk.LEFT, padx=(8, 14))
            Tooltip(check_effectue, "Cochez si cette dépense a été payée")

            check_emprunte = ttk.Checkbutton(
                status_frame, text=" 💸Empruntée", variable=emprunte_var,
                onvalue=True, offvalue=False, style="Emprunte.TCheckbutton"
            )
            check_emprunte.pack(side=tk.LEFT, padx=(0, 15))
            Tooltip(check_emprunte, "Cochez si cette dépense est un prêt")
            
            widgets = {
                'frame': expense_frame, 'nom_var': nom_var, 'montant_var': montant_var, 
                'categorie_var': categorie_var, 'effectue_var': effectue_var,
                'emprunte_var': emprunte_var,
                'remove_button': remove_button, 'nom_entry': nom_entry,
                'montant_entry': montant_entry
            }
            self.depenses_widgets.append(widgets)
            
            callback = lambda *args, idx=index: self.controller.handle_expense_update(idx)

            nom_var.trace_add("write", callback)
            montant_var.trace_add("write", callback)
            categorie_var.trace_add("write", callback)
            effectue_var.trace_add("write", callback)
            emprunte_var.trace_add("write", callback)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du widget dépense {index}: {e}")

    def _validate_numeric_input(self, value_if_allowed: str) -> bool:
        """Valide une entrée numérique"""
        if value_if_allowed == "": return True
        try:
            float(value_if_allowed.replace(',', '.'))
            return True
        except ValueError:
            return False
        
    def get_excel_import_filepath(self) -> Optional[Path]:
        """Récupère le chemin d'import pour un fichier Excel"""
        try:
            filepath = filedialog.askopenfilename(
                title="Importer depuis Excel",
                filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")]
            )
            return Path(filepath) if filepath else None
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du fichier d'import Excel: {e}")
            return None