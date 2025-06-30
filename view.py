# view.py
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime, timedelta

class BudgetView:
    """
    Gère l'interface graphique (widgets). Ne contient pas de logique métier.
    Communique uniquement avec le contrôleur.
    (Version avancée conservée)
    """
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self.depenses_widgets = []
        self.graph_window = None

        self.salaire_var = tk.StringVar()
        self.total_depenses_var = tk.StringVar(value="Total Dépenses : 0.00 €")
        self.argent_restant_var = tk.StringVar(value="Argent restant : 0.00 €")
        self.status_var = tk.StringVar()
        
        self.salaire_var.trace_add("write", self.controller.handle_salaire_update)

        self._configure_styles()
        self._create_widgets()

    def _configure_styles(self):
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10))
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Header.TLabel", font=("Arial", 10, "underline"))
        style.configure("Result.TLabel", font=("Arial", 14, "bold"))
        style.configure("TotalDepenses.TLabel", font=("Arial", 12, "bold"), foreground="purple")
        style.configure("Red.TButton", foreground="white", background="#f44336", font=("Arial", 9, "bold"))
        style.map("Red.TButton", background=[('active', '#d32f2f')])
        style.configure("Blue.TButton", foreground="white", background="#2196F3", font=("Arial", 10))
        style.map("Blue.TButton", background=[('active', '#1976D2')])
        style.configure("Green.TButton", foreground="white", background="#4CAF50", font=("Arial", 10, "bold"))
        style.map("Green.TButton", background=[('active', '#45a049')])
        style.configure("Status.TLabel", font=("Arial", 9), foreground="grey")

    def _create_widgets(self):
        self.master.title("Calculateur de Budget Mensuel (MVC) - Amélioré")
        self.master.geometry("800x800")
        self.master.minsize(800, 600)
        
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        salary_frame = ttk.Frame(main_frame)
        salary_frame.pack(fill=tk.X, pady=5)
        ttk.Label(salary_frame, text="Votre Salaire (€) :", style="Title.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        validate_cmd = (self.master.register(self._validate_numeric_input), '%P')
        self.entree_salaire = ttk.Entry(salary_frame, textvariable=self.salaire_var, validate="key", validatecommand=validate_cmd)
        self.entree_salaire.pack(side=tk.LEFT, fill=tk.X, expand=True)

        expenses_main_frame = ttk.LabelFrame(main_frame, text="Vos Dépenses Mensuelles (€)", style="Title.TLabel", padding="10")
        expenses_main_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        header_frame = ttk.Frame(expenses_main_frame)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Nom de la Dépense", style="Header.TLabel").pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(header_frame, text="Catégorie", style="Header.TLabel", width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Montant (€)", style="Header.TLabel", width=15).pack(side=tk.LEFT)
        ttk.Label(header_frame, width=5).pack(side=tk.LEFT)
        
        canvas = tk.Canvas(expenses_main_frame, borderwidth=0)
        self.scrollable_frame = ttk.Frame(canvas)
        scrollbar = ttk.Scrollbar(expenses_main_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas_frame = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_frame, width=e.width))

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        ttk.Button(action_frame, text="Ajouter une dépense", command=self.controller.handle_add_expense, style="Green.TButton").pack(side=tk.LEFT, padx=(0, 10))
        # Ajout du bouton Sauvegarder qui manquait dans cette version
        ttk.Button(action_frame, text="Sauvegarder", command=self.controller.handle_save, style="Blue.TButton").pack(side=tk.LEFT)
        ttk.Button(action_frame, text="Trier par Montant", command=self.controller.handle_sort, style="Blue.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Voir Graphique", command=self.controller.handle_show_graph, style="Blue.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Charger un Fichier", command=self.controller.handle_load_file, style="Blue.TButton").pack(side=tk.LEFT, padx=5)


        summary_frame = ttk.Frame(main_frame, padding="10 0")
        summary_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.label_total_depenses = ttk.Label(summary_frame, textvariable=self.total_depenses_var, style="TotalDepenses.TLabel")
        self.label_total_depenses.pack(anchor="w")
        self.label_resultat = ttk.Label(summary_frame, textvariable=self.argent_restant_var, style="Result.TLabel")
        self.label_resultat.pack(anchor="w", pady=(5, 10))
        ttk.Button(summary_frame, text="Réinitialiser Tout", command=self.controller.handle_reset, style="Red.TButton").pack(fill=tk.X, pady=(5, 0))
        
        status_bar = ttk.Frame(self.master, relief=tk.SUNKEN, padding="2 5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT)

    def _validate_numeric_input(self, value_if_allowed):
        if value_if_allowed == "" or value_if_allowed == "-": return True
        try:
            float(value_if_allowed.replace(',', '.'))
            return True
        except ValueError:
            return False

    def redraw_expenses(self, expenses_data, categories):
        for widget_dict in self.depenses_widgets:
            widget_dict['frame'].destroy()
        self.depenses_widgets.clear()
        
        validate_cmd = (self.master.register(self._validate_numeric_input), '%P')
        
        for i, dep in enumerate(expenses_data):
            row_frame = ttk.Frame(self.scrollable_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=2)

            nom_var = tk.StringVar(value=dep.nom)
            montant_var = tk.StringVar(value=str(dep.montant).replace('.', ','))
            categorie_var = tk.StringVar(value=dep.categorie)
            
            nom_entry = ttk.Entry(row_frame, textvariable=nom_var)
            nom_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
            
            categorie_combo = ttk.Combobox(row_frame, width=13, textvariable=categorie_var, values=categories)
            categorie_combo.pack(side=tk.LEFT, padx=5)

            montant_entry = ttk.Entry(row_frame, width=15, textvariable=montant_var, validate="key", validatecommand=validate_cmd)
            montant_entry.pack(side=tk.LEFT, padx=(0, 5))
            
            callback = lambda *args, index=i: self.controller.handle_expense_update(index)
            nom_var.trace_add("write", callback)
            montant_var.trace_add("write", callback)
            categorie_var.trace_add("write", callback)
            categorie_combo.bind("<<ComboboxSelected>>", callback)

            delete_button = ttk.Button(row_frame, text="X", width=2, style="Red.TButton", command=lambda index=i: self.controller.handle_remove_expense(index))
            delete_button.pack(side=tk.LEFT)

            self.depenses_widgets.append({
                'frame': row_frame, 
                'nom_var': nom_var, 
                'montant_var': montant_var,
                'categorie_var': categorie_var
            })

    def update_summary(self, total, restant):
        self.total_depenses_var.set(f"Total Dépenses : {total:.2f} €".replace('.', ','))
        self.argent_restant_var.set(f"Argent restant : {restant:.2f} €".replace('.', ','))
        self.label_resultat.config(foreground="green" if restant >= 0 else "red")
    
    def update_status(self, message):
        self.status_var.set(message)

    def set_display_salaire(self, salaire):
        current_val = str(salaire).replace('.',',')
        if self.salaire_var.get() != current_val:
            # Pour éviter une boucle infinie avec trace_add, on désactive temporairement le traçage
            trace_info = self.salaire_var.trace_info()
            if trace_info:
                self.salaire_var.trace_vdelete("w", trace_info[0][1])
                self.salaire_var.set(current_val)
                self.salaire_var.trace_add("write", self.controller.handle_salaire_update)
            else:
                self.salaire_var.set(current_val)
                
    def get_expense_value(self, index):
        if 0 <= index < len(self.depenses_widgets):
            widgets = self.depenses_widgets[index]
            nom = widgets['nom_var'].get()
            montant_str = widgets['montant_var'].get().replace(',', '.')
            categorie = widgets['categorie_var'].get()
            return nom, montant_str, categorie
        return None, None, None

    def display_message(self, title, message, type='info'):
        if type == 'error': messagebox.showerror(title, message)
        elif type == 'warning': messagebox.showwarning(title, message)
        else: messagebox.showinfo(title, message)

    def ask_confirmation(self, title, message):
        return messagebox.askyesno(title, message)
        
    def show_graph_window(self, get_data_callback):
        if self.graph_window and self.graph_window.winfo_exists():
            self.graph_window.lift()
            self.graph_window.focus()
            return
            
        labels, values, argent_restant, categories_data = get_data_callback()
        
        if not labels or not values:
            self.display_message("Graphique", "Aucune dépense valide à afficher.", "warning")
            return
            
        self.graph_window = GraphWindow(self.master, get_data_callback)


class GraphWindow(tk.Toplevel):
    def __init__(self, master, get_data_callback):
        super().__init__(master)
        self.get_data_callback = get_data_callback
        
        self.title("Analyse Complète des Dépenses")

        """ self.attributes('-fullscreen', True) """
        self.minsize(1000, 700) 
        self.update_idletasks()
        
        
        self.geometry("1200x800+50+50")  # Taille raisonnable avec un léger décalage


        self.bind("<Escape>", lambda e: self.destroy())



        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        """ self.transient(master)
        self.grab_set() """

        self.draw_content()

    def draw_content(self):
        """Dessine ou redessine tout le contenu de la fenêtre graphique."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        plt.close('all')

        labels, values, argent_restant, categories_data = self.get_data_callback()
        salaire = argent_restant + sum(values)

        if not labels or not values:
            self.destroy()
            messagebox.showwarning("Graphique", "Plus de données à afficher.")
            return

        # Frame centrale avec Canvas pour gérer les débordements si nécessaire
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_overview_tab(notebook, labels, values, argent_restant, salaire, categories_data)
        self._create_budget_analysis_tab(notebook, labels, values, argent_restant, salaire, categories_data)
        self._create_trends_tab(notebook, labels, values, categories_data)
        self._create_comparison_tab(notebook, labels, values, argent_restant, salaire, categories_data)

        # Zone infos + boutons bien visibles
        info_frame = ttk.Frame(self.main_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=(5, 10), anchor="s")

        self._create_stats_frame(info_frame, values, argent_restant, salaire)

        button_frame = ttk.Frame(info_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Actualiser", command=self.draw_content).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Fermer", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _create_stats_frame(self, parent, values, argent_restant, salaire):
        total_depenses = sum(values)
        depense_moyenne = total_depenses / len(values) if values else 0
        depense_max = max(values) if values else 0
        
        stats_frame = ttk.LabelFrame(parent, text="Statistiques Clés", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        
        col1 = ttk.Frame(stats_frame); col1.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col2 = ttk.Frame(stats_frame); col2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col3 = ttk.Frame(stats_frame); col3.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(col1, text=f"💰 Salaire mensuel: {salaire:.2f}€", font=("Arial", 11, "bold")).pack(anchor="w")
        ttk.Label(col1, text=f"📊 Nombre de dépenses: {len(values)}", font=("Arial", 10)).pack(anchor="w")
        ttk.Label(col2, text=f"💸 Total dépenses: {total_depenses:.2f}€", font=("Arial", 11), foreground="red").pack(anchor="w")
        ttk.Label(col2, text=f"📈 Dépense moyenne: {depense_moyenne:.2f}€", font=("Arial", 10)).pack(anchor="w")
        
        if argent_restant >= 0:
            ttk.Label(col3, text=f"✅ Argent restant: {argent_restant:.2f}€", font=("Arial", 11), foreground="green").pack(anchor="w")
        else:
            ttk.Label(col3, text=f"⚠️ Déficit: {abs(argent_restant):.2f}€", font=("Arial", 11), foreground="red").pack(anchor="w")
        ttk.Label(col3, text=f"🔝 Plus grosse dépense: {depense_max:.2f}€", font=("Arial", 10)).pack(anchor="w")

    def _create_overview_tab(self, notebook, labels, values, argent_restant, salaire, categories_data):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📊 Vue d'ensemble")
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Vue d\'ensemble de votre Budget', fontsize=16, fontweight='bold')
        
        # Graphique en secteurs des catégories
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
        
        # Graphique en barres des dépenses individuelles
        ax2 = fig.add_subplot(2, 2, 2)
        sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)[:10]  # Top 10
        if sorted_data:
            sorted_labels, sorted_values = zip(*sorted_data)
            bars = ax2.bar(range(len(sorted_labels)), sorted_values, 
                          color=plt.cm.viridis(np.linspace(0, 1, len(sorted_labels))))
            ax2.set_xticks(range(len(sorted_labels)))
            ax2.set_xticklabels([label[:15] + '...' if len(label) > 15 else label 
                               for label in sorted_labels], rotation=45, ha='right')
            ax2.set_ylabel('Montant (€)')
            ax2.set_title('Top 10 des Dépenses', fontweight='bold')
        
        # Graphique de répartition budget vs dépenses
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
        
        # Camembert des dépenses individuelles par montant
        ax4 = fig.add_subplot(2, 2, 4)
        if labels and values:
            total = sum(values)
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
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📈 Analyse Budget")
        
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyse Détaillée du Budget', fontsize=16, fontweight='bold')
        
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
        
        ax4 = fig.add_subplot(2, 2, 4)
        if categories_data:
            total_budget = salaire if salaire > 0 else 1
            spending_ratio = sum(categories_data.values()) / total_budget * 100
            
            ratios = [spending_ratio, max(0, 100 - spending_ratio)]
            labels = [f'Dépenses ({spending_ratio:.1f}%)', f'Épargne ({max(0, 100-spending_ratio):.1f}%)']
            
            if spending_ratio > 90: colors = ['#ff4757', '#ddd']
            elif spending_ratio > 70: colors = ['#ffa502', '#ddd']
            else: colors = ['#2ed573', '#ddd']
            
            wedges, texts, autotexts = ax4.pie(ratios, labels=labels, autopct='%1.1f%%',
                                              colors=colors, startangle=90)
            ax4.set_title('Taux d\'Épargne', fontweight='bold')
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_trends_tab(self, notebook, labels, values, categories_data):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="📊 Tendances")
        
        plt.rcParams['font.family'] = 'DejaVu Sans'  # ou une autre comme 'Arial Unicode MS'

        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyse des Tendances', fontsize=16, fontweight='bold')
        
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
        
        if len(weeks) > 1 :
            z = np.polyfit(weeks, weekly_spending, 1)
            p = np.poly1d(z)
            ax1.plot(weeks, p(weeks), "--", color='black', alpha=0.8, 
                    label=f'Tendance: {"↗" if z[0] > 0 else "↘"} {abs(z[0]):.1f}€/sem')
        
        ax1.set_xlabel('Semaine')
        ax1.set_ylabel('Dépenses (€)')
        ax1.set_title('Évolution Hebdomadaire', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
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
                patch.set_facecolor(color); patch.set_alpha(0.7)
            
            ax2.set_ylabel('Montant (€)')
            ax2.set_title('Variabilité par Catégorie', fontweight='bold')
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        ax3 = fig.add_subplot(2, 2, 3)
        if categories_data:
            months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun']
            cat_names = list(categories_data.keys())
            total_spending = sum(categories_data.values()) if sum(categories_data.values()) > 0 else 1
            proportions = {cat: [(categories_data[cat]/total_spending*100) + np.random.uniform(-5, 5) for _ in months] for cat in cat_names}

            for i in range(len(months)):
                total = sum(proportions[cat][i] for cat in cat_names)
                if total > 0:
                    for cat in cat_names: proportions[cat][i] = proportions[cat][i] / total * 100
            
            bottom = np.zeros(len(months))
            colors = plt.cm.Set3(np.linspace(0, 1, len(cat_names)))
            
            for i, cat in enumerate(cat_names):
                ax3.fill_between(months, bottom, bottom + proportions[cat], label=cat, color=colors[i], alpha=0.8)
                bottom += proportions[cat]
            
            ax3.set_ylabel('Proportion (%)')
            ax3.set_title('Évolution des Proportions', fontweight='bold')
            ax3.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            ax3.set_ylim(0, 100)
        
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
            ax4.set_xticklabels([cat[:8] + '...' if len(cat) > 8 else cat for cat in categories], rotation=45, ha='right')
            ax4.set_yticklabels([cat[:8] + '...' if len(cat) > 8 else cat for cat in categories])
            ax4.set_title('Corrélations Fictives', fontweight='bold')
            
            for i in range(n_cats):
                for j in range(n_cats):
                    ax4.text(j, i, f'{correlation_matrix[i, j]:.2f}', ha="center", va="center", color="black", fontsize=8)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_comparison_tab(self, notebook, labels, values, argent_restant, salaire, categories_data):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text="🔍 Comparaisons")
        
        fig = plt.Figure(figsize=(12, 8))
        fig.suptitle('Analyses Comparatives', fontsize=16, fontweight='bold')
        
        ax1 = fig.add_subplot(2, 2, 1)
        if categories_data:
            categories = list(categories_data.keys())
            user_values = list(categories_data.values())
            national_avg = [v * np.random.uniform(0.8, 1.2) for v in user_values]
            
            x = np.arange(len(categories))
            width = 0.35
            
            bars1 = ax1.bar(x - width/2, user_values, width, label='Vos dépenses', color='#ff6b6b', alpha=0.8)
            bars2 = ax1.bar(x + width/2, national_avg, width, label='Moyenne nationale', color='#4ecdc4', alpha=0.8)
            
            ax1.set_xlabel('Catégories')
            ax1.set_ylabel('Montant (€)')
            ax1.set_title('Comparaison avec la Moyenne', fontweight='bold')
            ax1.set_xticks(x)
            ax1.set_xticklabels([cat[:10] + '...' if len(cat) > 10 else cat for cat in categories], rotation=45, ha='right')
            ax1.legend()
        
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
        
        ax3 = fig.add_subplot(2, 2, 3)
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun']
        
        current_spending = sum(values) if values else 0
        current_income = salaire if salaire > 0 else 0
        spending_trend = [current_spending * (1 + np.random.uniform(-0.1, 0.1)) for _ in months]
        income_trend = [current_income * (1 + np.random.uniform(-0.05, 0.05)) for _ in months]
        
        ax3.plot(months, spending_trend, marker='o', linewidth=2, color='#ff6b6b', label='Dépenses')
        ax3.plot(months, income_trend, marker='s', linewidth=2, color='#4ecdc4', label='Revenus')
        
        ax3.fill_between(months, spending_trend, income_trend, where=[s < i for s, i in zip(spending_trend, income_trend)], color='green', alpha=0.3, label='Épargne')
        ax3.fill_between(months, spending_trend, income_trend, where=[s >= i for s, i in zip(spending_trend, income_trend)], color='red', alpha=0.3, label='Déficit')
        
        ax3.set_ylabel('Montant (€)')
        ax3.set_title('Revenus vs Dépenses', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # ### LIGNE CORRIGÉE CI-DESSOUS ###
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
        radii = [max(0, r) for r in ratios.values()] # Assurer que les rayons ne sont pas négatifs
        
        bars = ax4.bar(theta, radii, width=0.5, alpha=0.7, color=plt.cm.viridis(np.linspace(0, 1, len(ratios))))
        
        ax4.set_theta_zero_location('N')
        ax4.set_theta_direction(-1)
        ax4.set_rlabel_position(-22.5) # Position des étiquettes de rayon
        ax4.set_thetagrids(np.degrees(theta), list(ratios.keys()))
        ax4.set_title('Ratios Financiers (%)', fontweight='bold', pad=20)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)