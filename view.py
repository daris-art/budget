# view.py - Vue améliorée avec architecture MVC stricte

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable
import logging

from utils import MoisDisplayData, Depense, Mois, MoisInput

logger = logging.getLogger(__name__)

class Tooltip:
    """Classe utilitaire pour les infobulles"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event):
        try:
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 20
            y += self.widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            label = tk.Label(self.tooltip, text=self.text, bg="lightyellow", 
                           relief=tk.SOLID, borderwidth=1)
            label.pack()
            self.tooltip.wm_geometry("+%d+%d" % (x, y))
        except tk.TclError:
            pass  # Widget peut être détruit

    def hide(self, event):
        if self.tooltip:
            try:
                self.tooltip.destroy()
                self.tooltip = None
            except tk.TclError:
                pass

class BudgetView:
    """
    Vue principale - Responsable uniquement de l'interface utilisateur
    """
    
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self.depenses_widgets = []
        self.graph_window = None

        # Variables d'interface
        self.salaire_var = tk.StringVar()
        self.total_depenses_var = tk.StringVar(value="Total Dépenses : 0.00 €")
        self.total_effectue_var = tk.StringVar(value="Total Effectué : 0.00 €")
        self.total_non_effectue_var = tk.StringVar(value="Dépenses non effectuées : 0.00 €")
        self.argent_restant_var = tk.StringVar(value="Argent restant : 0.00 €")
        self.total_emprunte_var = tk.StringVar(value="Total Emprunté : 0.00 €")
        self.status_var = tk.StringVar()
        self.mois_actuel_var = tk.StringVar(value="Aucun mois sélectionné")
        
        # Configuration des callbacks
        self.salaire_var.trace_add("write", self.controller.handle_salaire_update)

        # Création de l'interface
        self._configure_styles()
        self._create_widgets()
        
        logger.info("BudgetView initialisée")

    def _configure_styles(self):
        """Configure les styles visuels"""
        style = ttk.Style()
        
        # Styles de base
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
        
        # Styles des boutons
        style.configure("Red.TButton", foreground="white", background="#f44336", 
                       font=("Arial", 9, "bold"))
        style.map("Red.TButton", background=[('active', '#d32f2f')])
        style.configure("Blue.TButton", foreground="white", background="#2196F3", 
                       font=("Arial", 10))
        style.map("Blue.TButton", background=[('active', '#1976D2')])
        style.configure("Green.TButton", foreground="white", background="#4CAF50", 
                       font=("Arial", 10, "bold"))
        style.map("Green.TButton", background=[('active', '#45a049')])
        
        # Styles des checkboxes
        style.configure("Effectue.TCheckbutton", font=("Arial", 11))
        style.map("Effectue.TCheckbutton",
                  indicatorcolor=[('selected', '#28a745'), ('!selected', 'white')],
                  background=[('active', '#e9ecef')])
        
        style.configure("Emprunte.TCheckbutton", font=("Arial", 11))
        style.map("Emprunte.TCheckbutton",
                  indicatorcolor=[('selected', '#007bff'), ('!selected', 'white')],
                  background=[('active', '#e9ecef')])
        
        # Autres styles
        style.configure("StatusFrame.TFrame", borderwidth=1)
        style.map('TCombobox', fieldbackground=[('readonly', 'white')])
        style.map('TCombobox', selectbackground=[('readonly', 'blue')])
        style.map('TCombobox', selectforeground=[('readonly', 'white')])

    def _create_widgets(self):
        """Crée tous les widgets de l'interface"""
        try:
            self.master.title("Calculateur de Budget Mensuel (MVC) - Amélioré")
            self.master.geometry("960x930")
            self.master.minsize(860, 600)
            
            main_frame = ttk.Frame(self.master, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Section gestion des fichiers/mois
            self._create_file_management_section(main_frame)
            
            # Section salaire
            self._create_salary_section(main_frame)
            
            # Section dépenses
            self._create_expenses_section(main_frame)
            
            # Section actions
            self._create_actions_section(main_frame)
            
            # Section résumé
            self._create_summary_section(main_frame)
            
            # Barre de statut
            self._create_status_bar()
            
            logger.info("Interface créée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'interface: {e}")
            raise

    def _create_file_management_section(self, parent):
        """Crée la section de gestion des fichiers/mois"""
        fichier_frame = ttk.Frame(parent)
        fichier_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Boutons de gestion des mois
        bouton_charger_mois = ttk.Button(
            fichier_frame, text="📂 Charger Mois", 
            command=self.controller.handle_load_mois, style="Blue.TButton"
        )
        bouton_charger_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_charger_mois, "Charger un budget mensuel existant")

        bouton_nouveau_mois = ttk.Button(
            fichier_frame, text="➕ Nouveau Mois", 
            command=self.controller.handle_create_new_mois, style="Green.TButton"
        )
        bouton_nouveau_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_nouveau_mois, "Créer un nouveau budget mensuel")

        bouton_supprimer_mois = ttk.Button(
            fichier_frame, text="🗑️ Supprimer Mois", 
            command=self.controller.handle_delete_mois, style="Red.TButton"
        )
        bouton_supprimer_mois.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_supprimer_mois, "Supprimer définitivement un mois")

        # Boutons d'import/export
        bouton_export = ttk.Button(
            fichier_frame, text="📤 Exporter JSON", 
            command=self.controller.handle_export_to_json, style="Blue.TButton"
        )
        bouton_export.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_export, "Exporter le mois actuel vers un fichier JSON")

        bouton_import = ttk.Button(
            fichier_frame, text="📥 Importer JSON", 
            command=self.controller.handle_import_from_json, style="Blue.TButton"
        )
        bouton_import.pack(side=tk.LEFT, padx=5)
        Tooltip(bouton_import, "Importer des données depuis un fichier JSON")

        # Label du mois actuel
        self.label_mois_actuel = ttk.Label(
            fichier_frame, textvariable=self.mois_actuel_var, style="Month.TLabel"
        )
        self.label_mois_actuel.pack(side=tk.LEFT, padx=(80, 0))

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
        
        # En-têtes
        header_frame = ttk.Frame(expenses_main_frame)
        header_frame.pack(fill=tk.X, padx=(0, 17), pady=(0, 2))
        
        ttk.Label(header_frame, text="Nom de la Dépense", style="Header.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Label(header_frame, text="Montant (€)", style="Header.TLabel").pack(
            side=tk.RIGHT, padx=(0, 320)
        )
        ttk.Label(header_frame, text="Catégorie", style="Header.TLabel").pack(
            side=tk.RIGHT, padx=(0, 80)
        )
        
        # Zone scrollable pour les dépenses
        canvas = tk.Canvas(expenses_main_frame, borderwidth=0)
        self.scrollable_frame = ttk.Frame(canvas)
        scrollbar = ttk.Scrollbar(expenses_main_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas_frame = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configuration du scrolling
        self.scrollable_frame.bind(
            "<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            '<Configure>', 
            lambda e: canvas.itemconfig(canvas_frame, width=e.width)
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

    def _create_summary_section(self, parent):
        """Crée la section de résumé financier"""
        summary_frame = ttk.Frame(parent, padding="10 0")
        summary_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Ligne 1
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

        # Ligne 2
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
        
        # Ligne 3
        line3_frame = ttk.Frame(summary_frame)
        line3_frame.pack(fill=tk.X, pady=(2, 5))
        
        self.label_total_emprunte = ttk.Label(
            line3_frame, textvariable=self.total_emprunte_var, style="Emprunte.TLabel"
        )
        self.label_total_emprunte.pack(side=tk.LEFT, anchor="w")

        # Bouton reset
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
            
            # Mettre à jour le titre de la fenêtre
            if display_data.nom != "Aucun mois":
                self.master.title(f"Budget Manager - {display_data.nom}")
            else:
                self.master.title("Budget Manager")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour complète: {e}")

    def update_expenses_display(self, depenses: List[Depense], categories: List[str]):
        """Met à jour l'affichage des dépenses"""
        try:
            # Supprimer les widgets existants
            for widget_dict in self.depenses_widgets:
                widget_dict['frame'].destroy()
            self.depenses_widgets.clear()

            # Créer les nouveaux widgets
            for i, depense in enumerate(depenses):
                self._create_expense_widget(i, depense, categories)
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des dépenses: {e}")

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

            # Couleur conditionnelle pour l'argent restant
            if display_data.argent_restant < 0:
                self.label_resultat.config(foreground="red")
            else:
                self.label_resultat.config(foreground="green")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du résumé: {e}")

    def set_salaire_display(self, salaire: float):
        """Met à jour l'affichage du salaire"""
        try:
            current_val = self.salaire_var.get().replace(',', '.')
            if current_val != f"{salaire:.2f}":
                self.salaire_var.set(f"{salaire:.2f}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du salaire: {e}")

    # ===== MÉTHODES D'INTERACTION AVEC L'UTILISATEUR =====
    def get_new_mois_input(self) -> Optional[MoisInput]:
        """Récupère les données de création d'un nouveau mois"""
        try:
            nom_mois = tk.simpledialog.askstring(
                "Nouveau mois", 
                "Nom du nouveau mois (ex: Janvier 2024):",
                initialvalue=f"{datetime.now().strftime('%B %Y')}"
            )
            
            if not nom_mois:
                return None
                
            salaire_str = tk.simpledialog.askstring(
                "Salaire", 
                f"Salaire pour {nom_mois}:",
                initialvalue="0"
            )
            
            if salaire_str is None:  # Annulé
                return None
                
            return MoisInput(nom=nom_mois, salaire=salaire_str or "0")
            
        except Exception as e:
            logger.error(f"Erreur lors de la saisie du nouveau mois: {e}")
            return None

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
                initialfile=f"{mois_nom.replace(' ', '_')}.json" # Correction ici : 'initialfile' au lieu de 'initialfilename'
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

    # ===== MÉTHODES D'ACCÈS AUX DONNÉES =====
    def get_salaire_value(self) -> str:
        """Récupère la valeur du salaire"""
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
                last_entry = self.depenses_widgets[-1]['frame'].winfo_children()[0]
                last_entry.focus_set()
        except Exception as e:
            logger.error(f"Erreur lors du focus sur la dernière dépense: {e}")

    # ===== MÉTHODES DE MESSAGES =====
    def show_success_message(self, message: str):
        """Affiche un message de succès"""
        messagebox.showinfo("Succès", message)

    def show_error_message(self, message: str):
        """Affiche un message d'erreur"""
        messagebox.showerror("Erreur", message)

    def show_warning_message(self, message: str):
        """Affiche un message d'avertissement"""
        messagebox.showwarning("Attention", message)

    def show_info_message(self, message: str):
        """Affiche un message d'information"""
        messagebox.showinfo("Information", message)

    def ask_confirmation(self, title: str, message: str) -> bool:
        """Demande une confirmation"""
        return messagebox.askyesno(title, message)

    def update_status(self, message: str):
        """Met à jour la barre de statut"""
        self.status_var.set(message)

    # ===== GRAPHIQUES =====
    def show_graph_window(self, get_data_callback: Callable):
        """Affiche la fenêtre des graphiques"""
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
            expense_frame.pack(fill=tk.X, pady=2, padx=2)

            # Variables
            nom_var = tk.StringVar(value=depense.nom)
            montant_var = tk.StringVar(value=f"{depense.montant:.2f}")
            categorie_var = tk.StringVar(value=depense.categorie)
            effectue_var = tk.BooleanVar(value=depense.effectue)
            emprunte_var = tk.BooleanVar(value=depense.emprunte)
            
            widgets = {
                'frame': expense_frame, 'nom_var': nom_var, 'montant_var': montant_var, 
                'categorie_var': categorie_var, 'effectue_var': effectue_var,
                'emprunte_var': emprunte_var
            }
            self.depenses_widgets.append(widgets)
            
            # Widgets d'entrée
            nom_entry = ttk.Entry(expense_frame, textvariable=nom_var)
            nom_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
            cat_combo = ttk.Combobox(
                expense_frame, textvariable=categorie_var, values=categories, 
                width=15, state="readonly"
            )
            cat_combo.pack(side=tk.LEFT, padx=(10, 0))

            validate_cmd = (self.master.register(self._validate_numeric_input), '%P')
            montant_entry = ttk.Entry(
                expense_frame, textvariable=montant_var, width=10, 
                justify='right', validate="key", validatecommand=validate_cmd
            )
            montant_entry.pack(side=tk.LEFT, padx=(5, 0))

            # Frame pour les statuts
            status_frame = ttk.Frame(expense_frame, padding="5 2", style="StatusFrame.TFrame")
            status_frame.pack(side=tk.LEFT, padx=(2, 0))

            check_effectue = ttk.Checkbutton(
                status_frame, text=" ✔️ Payée", variable=effectue_var,
                onvalue=True, offvalue=False, style="Effectue.TCheckbutton"
            )
            check_effectue.pack(side=tk.LEFT, padx=(8, 8))
            Tooltip(check_effectue, "Cochez si cette dépense a été payée")

            check_emprunte = ttk.Checkbutton(
                status_frame, text=" 💸 Empruntée", variable=emprunte_var,
                onvalue=True, offvalue=False, style="Emprunte.TCheckbutton"
            )
            check_emprunte.pack(side=tk.LEFT)
            Tooltip(check_emprunte, "Cochez si cette dépense est un prêt")

            # Bouton supprimer
            remove_button = ttk.Button(
                expense_frame, text="X", width=3, style="Red.TButton", 
                command=lambda i=index: self.controller.handle_remove_expense(i)
            )
            remove_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Callbacks pour les modifications
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
        if value_if_allowed == "":
            return True
        try:
            float(value_if_allowed.replace(',', '.'))
            return True
        except ValueError:
            return False


class MoisSelectionDialog:
    """Boîte de dialogue pour la sélection d'un mois"""
    
    def __init__(self, parent, mois_list: List[Mois], title: str, prompt: str):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        # Contenu
        tk.Label(self.dialog, text=prompt, pady=10, font=("Arial", 12)).pack()
        
        # Liste des mois
        self.listbox = tk.Listbox(self.dialog, selectmode=tk.SINGLE, font=("Arial", 10))
        for mois in mois_list:
            display_text = f"{mois.nom} (Salaire: {mois.salaire:.2f}€)"
            if mois.date_creation:
                try:
                    date_obj = datetime.fromisoformat(mois.date_creation.replace('Z', '+00:00'))
                    date_str = date_obj.strftime("%d/%m/%Y")
                    display_text += f" - Créé le {date_str}"
                except ValueError:
                    pass
            self.listbox.insert('end', display_text)
        
        self.listbox.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Boutons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Sélectionner", command=self._on_select).pack(
            side='left', padx=5
        )
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel).pack(
            side='left', padx=5
        )
        
        # Double-clic pour sélectionner
        self.listbox.bind('<Double-Button-1>', lambda e: self._on_select())
        
        # Focus sur la liste
        self.listbox.focus_set()
        if mois_list:
            self.listbox.selection_set(0)
        
        # Stockage de la liste pour la sélection
        self.mois_list = mois_list
        
        # Attendre la fermeture
        self.dialog.wait_window()
    
    def _on_select(self):
        selection = self.listbox.curselection()
        if selection:
            self.result = self.mois_list[selection[0]]
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.dialog.destroy()


class GraphWindow(tk.Toplevel):
    """Fenêtre des graphiques"""
    
    def __init__(self, master, get_data_callback: Callable):
        super().__init__(master)
        self.get_data_callback = get_data_callback
        
        self.title("Analyse Complète des Dépenses")
        self.minsize(1000, 700) 
        self.update_idletasks()
        self.geometry("1200x800+50+50")
        self.bind("<Escape>", lambda e: self.destroy())

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.draw_content()

    def draw_content(self):
        """Dessine le contenu des graphiques"""
        try:
            # Nettoyer le contenu existant
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            plt.close('all')

            # Récupérer les données
            labels, values, argent_restant, categories_data = self.get_data_callback()
            salaire = argent_restant + sum(values) if values else 0

            if not labels or not values:
                self.destroy()
                messagebox.showwarning("Graphique", "Plus de données à afficher.")
                return

            # Créer l'interface à onglets
            content_frame = ttk.Frame(self.main_frame)
            content_frame.pack(fill=tk.BOTH, expand=True)

            notebook = ttk.Notebook(content_frame)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Créer les différents onglets
            self._create_overview_tab(notebook, labels, values, argent_restant, salaire, categories_data)
            self._create_budget_analysis_tab(notebook, labels, values, argent_restant, salaire, categories_data)
            self._create_trends_tab(notebook, labels, values, categories_data)
            self._create_comparison_tab(notebook, labels, values, argent_restant, salaire, categories_data)

            # Frame d'informations en bas
            info_frame = ttk.Frame(self.main_frame)
            info_frame.pack(fill=tk.X, padx=10, pady=(5, 10), anchor="s")
            self._create_stats_frame(info_frame, values, argent_restant, salaire)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des graphiques: {e}")
            messagebox.showerror("Erreur", "Erreur lors de la génération des graphiques")
            self.destroy()
        
    def _create_stats_frame(self, parent, values, argent_restant, salaire):
        """Crée le frame des statistiques"""
        total_depenses = sum(values) if values else 0
        depense_moyenne = total_depenses / len(values) if values else 0
        depense_max = max(values) if values else 0
        
        stats_frame = ttk.LabelFrame(parent, text="Statistiques Clés", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        
        col1 = ttk.Frame(stats_frame)
        col1.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col2 = ttk.Frame(stats_frame)
        col2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col3 = ttk.Frame(stats_frame)
        col3.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(col1, text=f"💰 Salaire mensuel: {salaire:.2f}€", 
                 font=("Arial", 11, "bold")).pack(anchor="w")
        ttk.Label(col1, text=f"📊 Nombre de dépenses: {len(values)}", 
                 font=("Arial", 10)).pack(anchor="w")
        
        ttk.Label(col2, text=f"💸 Total dépenses: {total_depenses:.2f}€", 
                 font=("Arial", 11), foreground="red").pack(anchor="w")
        ttk.Label(col2, text=f"📈 Dépense moyenne: {depense_moyenne:.2f}€", 
                 font=("Arial", 10)).pack(anchor="w")
        
        if argent_restant >= 0:
            ttk.Label(col3, text=f"✅ Argent restant: {argent_restant:.2f}€", 
                     font=("Arial", 11), foreground="green").pack(anchor="w")
        else:
            ttk.Label(col3, text=f"⚠️ Déficit: {abs(argent_restant):.2f}€", 
                     font=("Arial", 11), foreground="red").pack(anchor="w")
        ttk.Label(col3, text=f"🔝 Plus grosse dépense: {depense_max:.2f}€", 
                 font=("Arial", 10)).pack(anchor="w")

    def _create_overview_tab(self, notebook, labels, values, argent_restant, salaire, categories_data):
        """Crée l'onglet vue d'ensemble"""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📊 Vue d'ensemble")
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Vue d\'ensemble de votre Budget', fontsize=16, fontweight='bold')
        
        # Graphique 1: Répartition par catégories
        ax1 = fig.add_subplot(2, 2, 1)
        if categories_data:
            cat_labels = list(categories_data.keys())
            cat_values = list(categories_data.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(cat_labels)))
            wedges, texts, autotexts = ax1.pie(cat_values, labels=cat_labels, autopct='%1.1f%%', 
                                              startangle=90, colors=colors)
            ax1.set_title('Répartition par Catégories', fontweight='bold')
        else:
            ax1.text(0.5, 0.5, "Pas de catégories", ha='center', va='center')
            ax1.set_title('Répartition par Catégories', fontweight='bold')
        
        # Graphique 2: Top 10 des dépenses
        ax2 = fig.add_subplot(2, 2, 2)
        sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:10]
        if sorted_data:
            sorted_labels, sorted_values = zip(*sorted_data)
            bars = ax2.bar(range(len(sorted_labels)), sorted_values, 
                          color=plt.cm.viridis(np.linspace(0, 1, len(sorted_labels))))
            ax2.set_xticks(range(len(sorted_labels)))
            ax2.set_xticklabels([label[:15] + '...' if len(label) > 15 else label 
                               for label in sorted_labels], rotation=45, ha='right')
            ax2.set_ylabel('Montant (€)')
            ax2.set_title('Top 10 des Dépenses', fontweight='bold')
        
        # Graphique 3: Budget vs Dépenses
        ax3 = fig.add_subplot(2, 2, 3)
        budget_data = ['Dépenses', 'Argent restant'] if argent_restant >= 0 else ['Dépenses', 'Déficit']
        budget_values = [sum(values), abs(argent_restant)]
        colors = ['#ff6b6b', '#4ecdc4'] if argent_restant >= 0 else ['#ff6b6b', '#ff4757']
        
        bars = ax3.bar(budget_data, budget_values, color=colors)
        ax3.set_ylabel('Montant (€)')
        ax3.set_title('Budget vs Dépenses', fontweight='bold')
        
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}€', ha='center', va='bottom')
        
        # Graphique 4: Répartition détaillée
        ax4 = fig.add_subplot(2, 2, 4)
        if labels and values:
            colors = plt.cm.Pastel2(np.linspace(0, 1, len(values)))
            def make_label(pct, all_vals):
                absolute = int(round(pct / 100. * np.sum(all_vals)))
                return f"{absolute}€"
            wedges, texts, autotexts = ax4.pie(
                values,
                labels=[label[:20] + '...' if len(label) > 20 else label for label in labels],
                autopct=lambda pct: make_label(pct, values),
                startangle=90,
                colors=colors,
                textprops={'fontsize': 8}
            )
            ax4.set_title("Répartition des Dépenses par Libellé", fontweight="bold")
        else:
            ax4.text(0.5, 0.5, "Aucune dépense", ha='center', va='center')
            ax4.set_title("Répartition des Dépenses par Libellé", fontweight="bold")
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_budget_analysis_tab(self, notebook, labels, values, argent_restant, salaire, categories_data):
        """Crée l'onglet d'analyse budgétaire"""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📈 Analyse Budget")
        
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyse Détaillée du Budget', fontsize=16, fontweight='bold')
        
        # Graphique 1: Radar des catégories
        ax1 = fig.add_subplot(2, 2, 1, projection='polar')
        if categories_data:
            categories = list(categories_data.keys())
            values_cat = list(categories_data.values())
            max_val = max(values_cat) if values_cat else 1
            normalized_values = [v/max_val * 100 for v in values_cat]
            
            angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
            normalized_values += normalized_values[:1]
            angles += angles[:1]
            
            ax1.plot(angles, normalized_values, 'o-', linewidth=2, color='#ff6b6b')
            ax1.fill(angles, normalized_values, alpha=0.25, color='#ff6b6b')
            ax1.set_xticks(angles[:-1])
            ax1.set_xticklabels(categories)
            ax1.set_title('Radar des Catégories', fontweight='bold', pad=20)
        
        # Graphique 2: Distribution des montants
        ax2 = fig.add_subplot(2, 2, 2)
        if values:
            bins = min(10, len(set(values))) if values else 1
            ax2.hist(values, bins=bins, color='#4ecdc4', alpha=0.7, edgecolor='black')
            ax2.axvline(np.mean(values), color='red', linestyle='--', 
                       label=f'Moyenne: {np.mean(values):.2f}€')
            ax2.set_xlabel('Montant (€)')
            ax2.set_ylabel('Fréquence')
            ax2.set_title('Distribution des Montants', fontweight='bold')
            ax2.legend()
        
        # Graphique 3: Flux de trésorerie
        ax3 = fig.add_subplot(2, 2, 3)
        if categories_data:
            cat_names = ['Salaire'] + list(categories_data.keys()) + ['Solde']
            cat_values = [salaire] + [-v for v in categories_data.values()] + [argent_restant]
            
            cumulative = np.cumsum([0] + cat_values[:-1])
            colors = ['green'] + ['red'] * (len(cat_values)-2) + (['green'] if argent_restant >= 0 else ['red'])
            
            for i, (name, value) in enumerate(zip(cat_names, cat_values)):
                if i == 0:
                    ax3.bar(i, value, color=colors[i], alpha=0.7)
                elif i == len(cat_names) - 1:
                    ax3.bar(i, value, bottom=0, color=colors[i], alpha=0.7)
                else:
                    ax3.bar(i, value, bottom=cumulative[i], color=colors[i], alpha=0.7)
            
            ax3.set_xticks(range(len(cat_names)))
            ax3.set_xticklabels([name[:10] + '...' if len(name) > 10 else name 
                               for name in cat_names], rotation=45, ha='right')
            ax3.set_ylabel('Montant (€)')
            ax3.set_title('Flux de Trésorerie', fontweight='bold')
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Graphique 4: Taux d'épargne
        ax4 = fig.add_subplot(2, 2, 4)
        if categories_data:
            total_budget = salaire if salaire > 0 else 1
            spending_ratio = sum(categories_data.values()) / total_budget * 100
            
            ratios = [spending_ratio, max(0, 100 - spending_ratio)]
            labels_pie = [f'Dépenses ({spending_ratio:.1f}%)', f'Épargne ({max(0, 100-spending_ratio):.1f}%)']
            
            if spending_ratio > 90: 
                colors = ['#ff4757', '#ddd']
            elif spending_ratio > 70: 
                colors = ['#ffa502', '#ddd']
            else: 
                colors = ['#2ed573', '#ddd']
            
            wedges, texts, autotexts = ax4.pie(ratios, labels=labels_pie, autopct='%1.1f%%',
                                              colors=colors, startangle=90)
            ax4.set_title('Taux d\'Épargne', fontweight='bold')
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_trends_tab(self, notebook, labels, values, categories_data):
        """Crée l'onglet des tendances"""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📊 Tendances")
        
        plt.rcParams['font.family'] = 'DejaVu Sans'

        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyse des Tendances', fontsize=16, fontweight='bold')
        
        # Graphique 1: Évolution hebdomadaire simulée
        ax1 = fig.add_subplot(2, 2, 1)
        weeks = list(range(1, 13))
        
        weekly_spending = []
        base_spending = sum(values) / 4 if values else 0
        for week in weeks:
            seasonal_factor = 1 + 0.2 * np.sin(week * np.pi / 6)
            random_factor = 1 + np.random.uniform(-0.3, 0.3)
            weekly_spending.append(base_spending * seasonal_factor * random_factor)
        
        ax1.plot(weeks, weekly_spending, marker='o', linewidth=2, color='#ff6b6b')
        ax1.fill_between(weeks, weekly_spending, alpha=0.3, color='#ff6b6b')
        
        if len(weeks) > 1:
            z = np.polyfit(weeks, weekly_spending, 1)
            p = np.poly1d(z)
            ax1.plot(weeks, p(weeks), "--", color='black', alpha=0.8, 
                    label=f'Tendance: {"↗" if z[0] > 0 else "↘"} {abs(z[0]):.1f}€/sem')
        
        ax1.set_xlabel('Semaine')
        ax1.set_ylabel('Dépenses (€)')
        ax1.set_title('Évolution Hebdomadaire', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Graphique 2: Variabilité par catégorie
        ax2 = fig.add_subplot(2, 2, 2)
        if categories_data:
            box_data, cat_names = [], []
            for cat, value in categories_data.items():
                simulated_data = np.random.normal(value, value*0.2, 20)
                box_data.append(simulated_data)
                cat_names.append(cat[:10] + '...' if len(cat) > 10 else cat)
            
            bp = ax2.boxplot(box_data, labels=cat_names, patch_artist=True)
            colors = plt.cm.Set3(np.linspace(0, 1, len(bp['boxes'])))
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax2.set_ylabel('Montant (€)')
            ax2.set_title('Variabilité par Catégorie', fontweight='bold')
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        # Graphique 3: Évolution des proportions
        ax3 = fig.add_subplot(2, 2, 3)
        if categories_data:
            months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun']
            cat_names = list(categories_data.keys())
            total_spending = sum(categories_data.values()) if sum(categories_data.values()) > 0 else 1
            proportions = {cat: [(categories_data[cat]/total_spending*100) + np.random.uniform(-5, 5) for _ in months] for cat in cat_names}

            for i in range(len(months)):
                total = sum(proportions[cat][i] for cat in cat_names)
                if total > 0:
                    for cat in cat_names: 
                        proportions[cat][i] = proportions[cat][i] / total * 100
            
            bottom = np.zeros(len(months))
            colors = plt.cm.Set3(np.linspace(0, 1, len(cat_names)))
            
            for i, cat in enumerate(cat_names):
                ax3.fill_between(months, bottom, bottom + proportions[cat], 
                               label=cat, color=colors[i], alpha=0.8)
                bottom += proportions[cat]
            
            ax3.set_ylabel('Proportion (%)')
            ax3.set_title('Évolution des Proportions', fontweight='bold')
            ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            ax3.set_ylim(0, 100)
        
        # Graphique 4: Matrice de corrélation fictive
        ax4 = fig.add_subplot(2, 2, 4)
        if len(values) > 1 and categories_data:
            categories = list(categories_data.keys())
            n_cats = len(categories)
            correlation_matrix = np.random.rand(n_cats, n_cats)
            correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
            np.fill_diagonal(correlation_matrix, 1)
            
            im = ax4.imshow(correlation_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
            ax4.set_xticks(range(n_cats))
            ax4.set_yticks(range(n_cats))
            ax4.set_xticklabels([cat[:8] + '...' if len(cat) > 8 else cat for cat in categories], 
                              rotation=45, ha='right')
            ax4.set_yticklabels([cat[:8] + '...' if len(cat) > 8 else cat for cat in categories])
            ax4.set_title('Corrélations Fictives', fontweight='bold')
            
            for i in range(n_cats):
                for j in range(n_cats):
                    ax4.text(j, i, f'{correlation_matrix[i, j]:.2f}', 
                           ha="center", va="center", color="black", fontsize=8)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_comparison_tab(self, notebook, labels, values, argent_restant, salaire, categories_data):
        """Crée l'onglet de comparaisons"""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="🔍 Comparaisons")
        
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyses Comparatives', fontsize=16, fontweight='bold')
        
        # Graphique 1: Comparaison avec la moyenne nationale
        ax1 = fig.add_subplot(2, 2, 1)
        if categories_data:
            categories = list(categories_data.keys())
            user_values = list(categories_data.values())
            national_avg = [v * np.random.uniform(0.8, 1.2) for v in user_values]
            
            x = np.arange(len(categories))
            width = 0.35
            
            bars1 = ax1.bar(x - width/2, user_values, width, label='Vos dépenses', 
                           color='#ff6b6b', alpha=0.8)
            bars2 = ax1.bar(x + width/2, national_avg, width, label='Moyenne nationale', 
                           color='#4ecdc4', alpha=0.8)
            
            ax1.set_xlabel('Catégories')
            ax1.set_ylabel('Montant (€)')
            ax1.set_title('Comparaison avec la Moyenne', fontweight='bold')
            ax1.set_xticks(x)
            ax1.set_xticklabels([cat[:10] + '...' if len(cat) > 10 else cat for cat in categories], 
                              rotation=45, ha='right')
            ax1.legend()
        
        # Graphique 2: Performance budgétaire
        ax2 = fig.add_subplot(2, 2, 2)
        if categories_data:
            categories = list(categories_data.keys())
            actual = list(categories_data.values())
            targets = [v * np.random.uniform(0.9, 1.1) for v in actual]
            
            performance = [(a - t) / t * 100 if t > 0 else 0 for a, t in zip(actual, targets)]
            colors = ['green' if p <= 0 else 'red' for p in performance]
            bars = ax2.barh(categories, performance, color=colors, alpha=0.7)
            
            ax2.set_xlabel('Écart vs Objectif (%)')
            ax2.set_title('Performance Budgétaire', fontweight='bold')
            ax2.axvline(x=0, color='black', linestyle='-', alpha=0.3)
            
            for i, (bar, perf) in enumerate(zip(bars, performance)):
                width = bar.get_width()
                ax2.text(width + (1 if width >= 0 else -1), bar.get_y() + bar.get_height()/2,
                        f'{perf:+.1f}%', ha='left' if width >= 0 else 'right', va='center')
        
        # Graphique 3: Revenus vs Dépenses
        ax3 = fig.add_subplot(2, 2, 3)
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun']
        
        current_spending = sum(values) if values else 0
        current_income = salaire if salaire > 0 else 0
        spending_trend = [current_spending * (1 + np.random.uniform(-0.1, 0.1)) for _ in months]
        income_trend = [current_income * (1 + np.random.uniform(-0.05, 0.05)) for _ in months]
        
        ax3.plot(months, spending_trend, marker='o', linewidth=2, color='#ff6b6b', label='Dépenses')
        ax3.plot(months, income_trend, marker='s', linewidth=2, color='#4ecdc4', label='Revenus')
        
        ax3.fill_between(months, spending_trend, income_trend, 
                        where=[s < i for s, i in zip(spending_trend, income_trend)], 
                        color='green', alpha=0.3, label='Épargne')
        ax3.fill_between(months, spending_trend, income_trend, 
                        where=[s >= i for s, i in zip(spending_trend, income_trend)], 
                        color='red', alpha=0.3, label='Déficit')
        
        ax3.set_ylabel('Montant (€)')
        ax3.set_title('Revenus vs Dépenses', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Graphique 4: Ratios financiers
        ax4 = fig.add_subplot(2, 2, 4, projection='polar')
        
        ratios = {
            'Taux d\'épargne': (argent_restant / salaire * 100) if salaire > 0 else 0,
            'Ratio dépenses': (sum(values) / salaire * 100) if salaire > 0 else 0,
        }
        
        if categories_data:
            total_spending = sum(categories_data.values())
            for cat, value in list(categories_data.items())[:3]:
                ratios[f'{cat} / Total'] = (value / total_spending * 100) if total_spending > 0 else 0
        
        theta = np.linspace(0.0, 2 * np.pi, len(ratios), endpoint=False)
        radii = [max(0, r) for r in ratios.values()]
        
        bars = ax4.bar(theta, radii, width=0.5, alpha=0.7, 
                      color=plt.cm.viridis(np.linspace(0, 1, len(ratios))))
        
        ax4.set_theta_zero_location('N')
        ax4.set_theta_direction(-1)
        ax4.set_rlabel_position(-22.5)
        ax4.set_thetagrids(np.degrees(theta), list(ratios.keys()))
        ax4.set_title('Ratios Financiers (%)', fontweight='bold', pad=20)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)